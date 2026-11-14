"""Redis-backed real-time game state engine for Codenames Multiplayer."""

import copy
import json
import os
import random
import time
import uuid
from typing import Any, Optional

import redis

from gamerooms.language_support import get_game_language_support, normalize_language_code
from impostor.word_pairs import normalize_text
from website.version import VERSION_COUNTER

from .words import (
    WORD_PACKS,
    deal_codenames_board,
    is_clue_forbidden_on_board,
    suggest_spymaster_clues,
)

_redis = None
_fallback_store: dict[str, str] = {}
_sys_rng = random.SystemRandom()

TEAMS = ("red", "blue")
ROLES = ("spymaster", "operative")

DEFAULT_SETTINGS: dict[str, Any] = {
    "word_pack": "classic",
    "spymaster_timer": 0,  # 0 = untimed casual default
    "operative_timer": 0,  # 0 = untimed casual default
    "allow_custom_deck": True,
    "rotate_spymasters": True,
}


def _get_redis():
    global _redis
    if _redis is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis = redis.Redis.from_url(redis_url, decode_responses=True)
    return _redis


def _key(code: str) -> str:
    return f"codenames:{code.upper()}"


def create_initial_state(
    code: str,
    title: str = "Codenames Room",
    password: str = "",
    language: str = "en",
) -> dict[str, Any]:
    """Create a fresh Codenames room state."""
    return {
        "code": code.upper(),
        "title": title,
        "password": password,
        "language": normalize_language_code(language),
        "status": "open",
        "phase": "lobby",  # lobby | playing | gameover
        "started": False,
        "creator": None,
        "creator_id": None,
        "admin_token": uuid.uuid4().hex[:12],
        "round_num": 0,
        "red_wins": 0,
        "blue_wins": 0,
        "starting_team": None,
        "turn_team": None,  # red | blue
        "turn_phase": None,  # spymaster_clue | operative_guess | finished
        "guesses_remaining": 0,
        "current_clue": None,
        "current_turn": None,
        "winner": None,
        "win_reason": None,
        "board": [],
        "used_words": [],
        "custom_deck": [],
        "turns_log": [],
        "rounds_history": [],
        "last_spymasters": {"red": None, "blue": None},
        "players": {},
        "chat_log": [],
        "next_chat_id": 1,
        "next_player_seq": 1,
        "timer_ends_at": None,
        "timer_duration": 0,
        "timer_paused_remaining": None,
        "settings": copy.deepcopy(DEFAULT_SETTINGS),
    }


def _ensure_state_schema(code: str, state: dict[str, Any]) -> dict[str, Any]:
    defaults = create_initial_state(code=code)
    for k, v in defaults.items():
        if k not in state:
            state[k] = v
    if "settings" not in state or not isinstance(state["settings"], dict):
        state["settings"] = copy.deepcopy(DEFAULT_SETTINGS)
    else:
        for sk, sv in DEFAULT_SETTINGS.items():
            state["settings"].setdefault(sk, sv)
    return state


def get_game(code: str) -> dict[str, Any]:
    r = _get_redis()
    try:
        data = r.get(_key(code))
    except Exception:
        data = _fallback_store.get(_key(code))
    if not data:
        return create_initial_state(code=code)
    return _ensure_state_schema(code, json.loads(data))


def save_game(code: str, state: dict[str, Any]) -> None:
    payload = json.dumps(state)
    _fallback_store[_key(code)] = payload
    r = _get_redis()
    try:
        r.set(_key(code), payload, ex=60 * 60 * 12)
    except Exception:
        pass


def delete_game(code: str) -> None:
    _fallback_store.pop(_key(code), None)
    r = _get_redis()
    try:
        r.delete(_key(code))
    except Exception:
        pass


def sync_room_db_status(code: str, status: str) -> None:
    """Persist open/running/finished status back to gamerooms.Room."""
    try:
        from gamerooms.models import Room

        Room.objects.filter(code=code.upper()).update(status=status)
    except Exception:
        pass


def append_event(
    state: dict[str, Any],
    sender_name: str,
    text: str,
    kind: str = "system",
    sender_id: Optional[str] = None,
) -> dict[str, Any]:
    entry = {
        "id": state.get("next_chat_id", 1),
        "ts": time.time(),
        "sender_id": sender_id,
        "sender": sender_name,
        "text": text,
        "kind": kind,
    }
    state["next_chat_id"] = entry["id"] + 1
    log = state.setdefault("chat_log", [])
    log.append(entry)
    if len(log) > 160:
        state["chat_log"] = log[-160:]
    return entry


def set_phase_timer(state: dict[str, Any], seconds: int) -> None:
    sec = max(0, int(seconds or 0))
    state["timer_duration"] = sec
    state["timer_paused_remaining"] = None
    state["timer_ends_at"] = (time.time() + sec) if sec > 0 else None


def find_player_by_token(state: dict[str, Any], token: Optional[str]) -> Optional[dict[str, Any]]:
    if not token:
        return None
    for p in state.get("players", {}).values():
        if p.get("token") == token:
            return p
    return None


def find_player_by_name(state: dict[str, Any], name: Optional[str]) -> Optional[dict[str, Any]]:
    if not name:
        return None
    lowered = name.strip().lower()
    for p in state.get("players", {}).values():
        if p.get("name", "").strip().lower() == lowered:
            return p
    return None


def _unique_name(state: dict[str, Any], raw_name: str, exclude_pid: Optional[str] = None) -> str:
    base = (raw_name or "Agent").strip()[:28] or "Agent"
    existing = {p["name"].lower() for pid, p in state.get("players", {}).items() if pid != exclude_pid}
    if base.lower() not in existing:
        return base
    i = 2
    while f"{base} {i}".lower() in existing:
        i += 1
    return f"{base} {i}"


def is_player_admin(state: dict[str, Any], player: Optional[dict[str, Any]]) -> bool:
    if not player:
        return False
    return bool(player.get("is_admin") or player.get("id") == state.get("creator_id"))


def add_player(
    state: dict[str, Any],
    name: str,
    token: Optional[str] = None,
    is_admin: bool = False,
    channel_name: str = "",
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Add or reconnect a player cleanly; first joiner becomes admin if creator unset."""
    existing = find_player_by_token(state, token)
    if existing:
        existing["connected"] = True
        if channel_name:
            existing["channel_name"] = channel_name
        if is_admin:
            existing["is_admin"] = True
        save_game(state["code"], state)
        return state, existing, False

    existing_name = find_player_by_name(state, name)
    if existing_name and not existing_name.get("connected"):
        existing_name["connected"] = True
        if channel_name:
            existing_name["channel_name"] = channel_name
        if is_admin:
            existing_name["is_admin"] = True
        save_game(state["code"], state)
        return state, existing_name, False

    pid = f"p{state.get('next_player_seq', 1)}"
    state["next_player_seq"] = state.get("next_player_seq", 1) + 1
    clean_name = _unique_name(state, name)

    is_first = len(state.get("players", {})) == 0
    make_admin = bool(is_admin or is_first)

    player = {
        "id": pid,
        "name": clean_name,
        "token": token or uuid.uuid4().hex[:16],
        "is_admin": make_admin,
        "is_spectator": False,
        "is_table_player": False,
        "team": None,
        "role": "operative",
        "connected": True,
        "channel_name": channel_name,
    }
    state["players"][pid] = player
    if not state.get("creator") and make_admin:
        state["creator"] = clean_name
        state["creator_id"] = pid
    append_event(state, "System", f"🕵️ {clean_name} joined the mission.", kind="join")
    save_game(state["code"], state)
    return state, player, True


def add_table_player(state: dict[str, Any], name: str) -> tuple[bool, str]:
    """Allow the Host/Moderator to add an oral / couch player without a phone."""
    raw = " ".join(str(name or "").strip().split())[:28]
    if not raw:
        return False, "Enter a player name to add."

    pid = f"p{state.get('next_player_seq', 1)}"
    state["next_player_seq"] = state.get("next_player_seq", 1) + 1
    clean_name = _unique_name(state, raw)

    player = {
        "id": pid,
        "name": clean_name,
        "token": uuid.uuid4().hex[:16],
        "is_admin": False,
        "is_spectator": False,
        "is_table_player": True,
        "team": None,
        "role": "operative",
        "connected": True,
        "channel_name": "",
    }
    state["players"][pid] = player
    append_event(state, "System", f"🪑 {clean_name} was added as an oral/table player.", kind="join")
    save_game(state["code"], state)
    return True, f"Added table player {clean_name}."


def kick_player(state: dict[str, Any], target_id: str, by_name: str = "Host") -> Optional[str]:
    target = state.get("players", {}).pop(target_id, None)
    if not target:
        return None
    append_event(state, "System", f"👢 {target['name']} was removed by {by_name}.")
    save_game(state["code"], state)
    return target["name"]


def toggle_spectator(state: dict[str, Any], target_id: str) -> Optional[bool]:
    target = state.get("players", {}).get(target_id)
    if not target:
        return None
    target["is_spectator"] = not bool(target.get("is_spectator"))
    if target["is_spectator"]:
        target["team"] = None
    save_game(state["code"], state)
    return target["is_spectator"]


def join_team(
    state: dict[str, Any],
    player_id: str,
    team: str,
    role: str = "operative",
    target_player_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Assign self (or another player if called by Host/Moderator) to a team and role."""
    caller = state.get("players", {}).get(player_id)
    if not caller:
        return False, "Player not found."

    if target_player_id and target_player_id != player_id:
        if not is_player_admin(state, caller):
            return False, "Only the Host can assign other players' teams."
        subject = state.get("players", {}).get(target_player_id)
    else:
        subject = caller

    if not subject:
        return False, "Target player not found."

    if team not in TEAMS or role not in ROLES:
        return False, "Invalid team or role."

    subject["is_spectator"] = False
    subject["team"] = team
    subject["role"] = role
    save_game(state["code"], state)
    return True, f"{subject['name']} joined {team.title()} ({role.title()})."


def auto_balance_teams(state: dict[str, Any]) -> tuple[bool, str]:
    """Distribute active players evenly onto Red & Blue teams with one Spymaster each."""
    active = [p for p in state.get("players", {}).values() if not p.get("is_spectator")]
    if len(active) < 2:
        return False, "Need at least 2 active players to balance teams."

    shuffled = list(active)
    _sys_rng.shuffle(shuffled)
    for idx, p in enumerate(shuffled):
        team = "red" if idx % 2 == 0 else "blue"
        p["team"] = team
        p["role"] = "operative"

    for team in TEAMS:
        members = [p for p in state["players"].values() if p.get("team") == team and not p.get("is_spectator")]
        if members:
            members[0]["role"] = "spymaster"

    append_event(state, "System", "⚖️ Teams auto-balanced (Red vs Blue).", kind="system")
    save_game(state["code"], state)
    return True, "Teams balanced."


def _ensure_teams_ready(state: dict[str, Any]) -> None:
    """Assign any unassigned active players and ensure both teams have a Spymaster."""
    active = [p for p in state.get("players", {}).values() if not p.get("is_spectator")]
    unassigned = [p for p in active if p.get("team") not in TEAMS]
    red_count = sum(1 for p in active if p.get("team") == "red")
    blue_count = sum(1 for p in active if p.get("team") == "blue")

    for p in unassigned:
        if red_count <= blue_count:
            p["team"] = "red"
            red_count += 1
        else:
            p["team"] = "blue"
            blue_count += 1

    # Handle case where everyone stacked onto one team
    if red_count == 0 or blue_count == 0:
        auto_balance_teams(state)
        return

    for team in TEAMS:
        members = [p for p in active if p.get("team") == team]
        if members and not any(m.get("role") == "spymaster" for m in members):
            members[0]["role"] = "spymaster"


def rotate_spymasters(state: dict[str, Any]) -> None:
    """Rotate Spymasters on each team to the next teammate for replay variety."""
    last = state.get("last_spymasters") or {}
    for team in TEAMS:
        members = [p for p in state.get("players", {}).values() if p.get("team") == team and not p.get("is_spectator")]
        if len(members) < 2:
            if members:
                members[0]["role"] = "spymaster"
            continue
        prev_id = last.get(team) or next((m["id"] for m in members if m.get("role") == "spymaster"), None)
        ids = [m["id"] for m in members]
        if prev_id in ids:
            next_id = ids[(ids.index(prev_id) + 1) % len(ids)]
        else:
            next_id = ids[0]
        for m in members:
            m["role"] = "spymaster" if m["id"] == next_id else "operative"


def update_settings(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    s = state.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))
    if "word_pack" in patch and patch["word_pack"] in WORD_PACKS:
        s["word_pack"] = patch["word_pack"]
    if "spymaster_timer" in patch:
        raw_st = patch["spymaster_timer"]
        s["spymaster_timer"] = max(0, min(600, int(raw_st) if raw_st not in (None, "") else 0))
    if "operative_timer" in patch:
        raw_ot = patch["operative_timer"]
        s["operative_timer"] = max(0, min(600, int(raw_ot) if raw_ot not in (None, "") else 0))
    if "allow_custom_deck" in patch:
        s["allow_custom_deck"] = bool(patch["allow_custom_deck"])
    if "rotate_spymasters" in patch:
        s["rotate_spymasters"] = bool(patch["rotate_spymasters"])
    save_game(state["code"], state)
    return s


def add_custom_word(state: dict[str, Any], author: dict[str, Any], word: str) -> tuple[bool, str]:
    clean_word = " ".join(str(word or "").strip().split())[:28]
    if not clean_word:
        return False, "Enter a codename word to add."
    norm = normalize_text(clean_word)
    deck = state.setdefault("custom_deck", [])
    if any(normalize_text(item.get("word")) == norm for item in deck):
        return False, f"'{clean_word}' is already in the custom word queue."
    deck.append({"word": clean_word.title(), "author_name": author["name"]})
    append_event(state, "System", f"🃏 {author['name']} added custom codename '{clean_word.title()}'.")
    save_game(state["code"], state)
    return True, f"Added '{clean_word.title()}' to the custom deck."


def _apply_turn_timer(state: dict[str, Any]) -> None:
    s = state.get("settings", DEFAULT_SETTINGS)
    sec = s.get("spymaster_timer", 0) if state.get("turn_phase") == "spymaster_clue" else s.get("operative_timer", 0)
    set_phase_timer(state, int(sec or 0))


def start_round(state: dict[str, Any], is_redraw: bool = False) -> tuple[bool, str]:
    """Deal a fresh 25-word Codenames board and begin play."""
    active = [p for p in state.get("players", {}).values() if not p.get("is_spectator")]
    if len(active) < 2:
        return False, "Need at least 2 active players to start Codenames."

    _ensure_teams_ready(state)
    if not is_redraw and state.get("round_num", 0) >= 1 and state["settings"].get("rotate_spymasters", True):
        rotate_spymasters(state)

    for team in TEAMS:
        spy = next(
            (p for p in state["players"].values() if p.get("team") == team and p.get("role") == "spymaster"),
            None,
        )
        state.setdefault("last_spymasters", {})[team] = spy["id"] if spy else None

    lang_code = state.get("language", "en")
    word_pack = state["settings"].get("word_pack", "classic")
    used_words = state.setdefault("used_words", [])
    custom_deck = state.setdefault("custom_deck", [])

    starting_team, board = deal_codenames_board(
        lang_code=lang_code,
        word_pack=word_pack,
        used_words=used_words,
        custom_deck=custom_deck,
        rng=_sys_rng,
    )
    for card in board:
        if card["word_en"].lower() not in used_words:
            used_words.append(card["word_en"].lower())
    if len(used_words) >= len(board) * 14:
        # Keep room history from starving when playing >14 boards consecutively
        state["used_words"] = used_words[-25:]

    if not is_redraw:
        state["round_num"] = state.get("round_num", 0) + 1

    state["started"] = True
    state["phase"] = "playing"
    state["status"] = "running"
    state["starting_team"] = starting_team
    state["turn_team"] = starting_team
    state["turn_phase"] = "spymaster_clue"
    state["guesses_remaining"] = 0
    state["current_clue"] = None
    state["current_turn"] = None
    state["winner"] = None
    state["win_reason"] = None
    state["board"] = board
    state["turns_log"] = []

    _apply_turn_timer(state)
    team_label = "🔴 Red" if starting_team == "red" else "🔵 Blue"
    verb = "Board redrawn!" if is_redraw else f"Game #{state['round_num']} started!"
    append_event(state, "System", f"🕵️ {verb} {team_label} starts with 9 agents to find.", kind="system")
    save_game(state["code"], state)
    sync_room_db_status(state["code"], "running")
    return True, "Board dealt."


def submit_clue(
    state: dict[str, Any],
    player_id: str,
    clue_word: str,
    clue_count: Any = 1,
    by_mod: bool = False,
) -> tuple[bool, str]:
    """Validate and publish a Spymaster's 1-word clue + count."""
    if state.get("phase") != "playing" or state.get("turn_phase") != "spymaster_clue":
        return False, "Not waiting for a Spymaster clue right now."

    caller = state.get("players", {}).get(player_id)
    if not caller:
        return False, "Player not found."

    turn_team = state.get("turn_team")
    caller_is_admin = is_player_admin(state, caller)
    is_team_spymaster = (
        caller.get("team") == turn_team and caller.get("role") == "spymaster" and not caller.get("is_spectator")
    )

    if not (is_team_spymaster or (by_mod and caller_is_admin)):
        return False, f"Only the {turn_team.title()} Spymaster can submit the clue."

    cleaned = " ".join(str(clue_word or "").strip().split())[:40]
    if not cleaned:
        return False, "Enter a one-word clue."
    if len(cleaned.split()) > 1:
        return False, "Codenames clues must be a single word (no spaces)."

    forbidden = is_clue_forbidden_on_board(cleaned, state.get("board", []))
    if forbidden:
        return False, f"🚫 Illegal clue: '{cleaned}' matches visible board card '{forbidden}'!"

    try:
        count_int = int(clue_count)
    except (TypeError, ValueError):
        return False, "Invalid clue number."
    if count_int not in range(0, 10) and count_int != 99:
        return False, "Clue number must be 0-9 or 99 (∞)."

    guesses_allowed = 99 if count_int in (0, 99) else min(25, count_int + 1)
    display_count = "∞" if count_int == 99 else str(count_int)

    spymaster_name = caller["name"]
    if by_mod and caller_is_admin and not is_team_spymaster:
        team_spy = next(
            (
                p
                for p in state.get("players", {}).values()
                if p.get("team") == turn_team and p.get("role") == "spymaster"
            ),
            None,
        )
        spymaster_name = team_spy["name"] if team_spy else f"{caller['name']} (Mod)"

    clue_obj = {
        "team": turn_team,
        "word": cleaned.upper(),
        "count": count_int,
        "display_count": display_count,
        "spymaster_id": caller["id"],
        "spymaster_name": spymaster_name,
        "by_mod": bool(by_mod and caller_is_admin and not is_team_spymaster),
        "ts": time.time(),
    }
    state["current_clue"] = clue_obj
    state["current_turn"] = {
        "turn_num": len(state.get("turns_log", [])) + 1,
        "team": turn_team,
        "clue_word": clue_obj["word"],
        "clue_count": count_int,
        "display_count": display_count,
        "spymaster_name": spymaster_name,
        "guesses": [],
        "ts": clue_obj["ts"],
    }
    state["turn_phase"] = "operative_guess"
    state["guesses_remaining"] = guesses_allowed
    _apply_turn_timer(state)

    team_emoji = "🔴" if turn_team == "red" else "🔵"
    mod_note = " (logged by Mod)" if clue_obj["by_mod"] else ""
    append_event(
        state,
        spymaster_name,
        f"{team_emoji} Clue: {clue_obj['word']} ({display_count}){mod_note}",
        kind="clue",
        sender_id=player_id,
    )
    save_game(state["code"], state)
    return True, "Clue published."


def _archive_current_turn(state: dict[str, Any]) -> None:
    cur = state.get("current_turn")
    if cur:
        state.setdefault("turns_log", []).append(cur)
        state["current_turn"] = None


def _finish_board(state: dict[str, Any], winner: str, reason: str) -> None:
    _archive_current_turn(state)
    state["phase"] = "gameover"
    state["turn_phase"] = "finished"
    state["status"] = "finished"
    state["winner"] = winner
    state["win_reason"] = reason
    state["guesses_remaining"] = 0
    set_phase_timer(state, 0)

    if winner == "red":
        state["red_wins"] = state.get("red_wins", 0) + 1
    elif winner == "blue":
        state["blue_wins"] = state.get("blue_wins", 0) + 1

    board = state.get("board", [])
    red_left = sum(1 for c in board if c.get("affiliation") == "red" and not c.get("revealed"))
    blue_left = sum(1 for c in board if c.get("affiliation") == "blue" and not c.get("revealed"))

    state.setdefault("rounds_history", []).append(
        {
            "round": state.get("round_num", 1),
            "starting_team": state.get("starting_team"),
            "winner": winner,
            "win_reason": reason,
            "red_remaining": red_left,
            "blue_remaining": blue_left,
            "turns": copy.deepcopy(state.get("turns_log", [])),
            "board": [
                {
                    "index": c["index"],
                    "word_en": c["word_en"],
                    "word_display": c["word_display"],
                    "affiliation": c["affiliation"],
                    "revealed": c["revealed"],
                    "revealed_by": c.get("revealed_by"),
                    "definition": c.get("definition", ""),
                }
                for c in board
            ],
            "ts": time.time(),
        }
    )
    append_event(state, "System", reason, kind="gameover")
    save_game(state["code"], state)
    sync_room_db_status(state["code"], "finished")


def _switch_to_other_team(state: dict[str, Any]) -> None:
    _archive_current_turn(state)
    other = "blue" if state.get("turn_team") == "red" else "red"
    state["turn_team"] = other
    state["turn_phase"] = "spymaster_clue"
    state["guesses_remaining"] = 0
    _apply_turn_timer(state)


def guess_card(
    state: dict[str, Any],
    player_id: str,
    card_index: int,
    by_mod: bool = False,
) -> tuple[bool, str]:
    """Tap a codename card on the 5x5 grid as an Operative (or Host on an oral player's behalf)."""
    if state.get("phase") != "playing" or state.get("turn_phase") != "operative_guess":
        return False, "Not in operative guessing phase right now."

    caller = state.get("players", {}).get(player_id)
    if not caller:
        return False, "Player not found."

    turn_team = state.get("turn_team")
    caller_is_admin = is_player_admin(state, caller)
    is_active_operative = (
        caller.get("team") == turn_team and caller.get("role") == "operative" and not caller.get("is_spectator")
    )
    if not (is_active_operative or (by_mod and caller_is_admin)):
        return False, f"Only {turn_team.title()} Operatives (or Host for oral players) can tap cards."

    board = state.get("board", [])
    try:
        idx = int(card_index)
    except (TypeError, ValueError):
        return False, "Invalid card index."
    if idx < 0 or idx >= len(board):
        return False, "Card index out of range."

    card = board[idx]
    if card.get("revealed"):
        return False, "That card is already revealed."

    card["revealed"] = True
    card["revealed_by"] = caller["name"]
    card["revealed_by_team"] = turn_team

    aff = card.get("affiliation")
    other_team = "blue" if turn_team == "red" else "red"
    guess_record = {
        "index": idx,
        "word": card["word_display"],
        "word_en": card["word_en"],
        "affiliation": aff,
        "player_name": caller["name"],
        "by_mod": bool(by_mod and caller_is_admin and not is_active_operative),
        "ts": time.time(),
    }
    if state.get("current_turn"):
        state["current_turn"].setdefault("guesses", []).append(guess_record)

    aff_emoji = {"red": "🔴", "blue": "🔵", "civilian": "⬜", "assassin": "💀"}.get(aff, "⬜")
    append_event(
        state,
        caller["name"],
        f"{aff_emoji} Tapped '{card['word_display']}' → {aff.upper()}",
        kind="guess",
        sender_id=player_id,
    )

    red_left = sum(1 for c in board if c.get("affiliation") == "red" and not c.get("revealed"))
    blue_left = sum(1 for c in board if c.get("affiliation") == "blue" and not c.get("revealed"))

    if aff == "assassin":
        _finish_board(
            state,
            winner=other_team,
            reason=f"💀 {caller['name']} hit the ASSASSIN ({card['word_display']})! {other_team.title()} Team wins!",
        )
        return True, "Assassin uncovered!"

    if red_left == 0:
        _finish_board(state, winner="red", reason="🎉 Red Team uncovered all 9/8 agents!")
        return True, "Red Team wins!"

    if blue_left == 0:
        _finish_board(state, winner="blue", reason="🎉 Blue Team uncovered all agents!")
        return True, "Blue Team wins!"

    if aff != turn_team:
        _switch_to_other_team(state)
        next_label = "🔴 Red" if state["turn_team"] == "red" else "🔵 Blue"
        append_event(state, "System", f"↩️ Turn ended — {next_label} Spymaster is up next.")
        save_game(state["code"], state)
        return True, f"Turn ended ({aff})."

    # Correct friendly agent!
    rem = max(0, int(state.get("guesses_remaining", 1)) - 1)
    state["guesses_remaining"] = rem
    if rem <= 0:
        _switch_to_other_team(state)
        next_label = "🔴 Red" if state["turn_team"] == "red" else "🔵 Blue"
        append_event(state, "System", f"✅ Max guesses used — {next_label} Spymaster is up next.")

    save_game(state["code"], state)
    return True, "Agent found!"


def end_turn(state: dict[str, Any], player_id: str, by_mod: bool = False) -> tuple[bool, str]:
    """Voluntarily end the Operative guessing phase and pass turn to the opposing Spymaster."""
    if state.get("phase") != "playing" or state.get("turn_phase") != "operative_guess":
        return False, "Can only end turn during Operative guessing."

    caller = state.get("players", {}).get(player_id)
    if not caller:
        return False, "Player not found."

    turn_team = state.get("turn_team")
    caller_is_admin = is_player_admin(state, caller)
    is_active_operative = (
        caller.get("team") == turn_team and caller.get("role") == "operative" and not caller.get("is_spectator")
    )
    if not (is_active_operative or (by_mod and caller_is_admin)):
        return False, "Only active team Operatives or Host can pass the turn."

    _switch_to_other_team(state)
    next_label = "🔴 Red" if state["turn_team"] == "red" else "🔵 Blue"
    append_event(state, "System", f"⏭️ {caller['name']} passed turn — {next_label} Spymaster is up!")
    save_game(state["code"], state)
    return True, "Turn passed."


def end_match_early(state: dict[str, Any], by_name: str = "Host") -> None:
    """Abort an active board and reveal all affiliations."""
    if state.get("phase") == "playing":
        _finish_board(state, winner="none", reason=f"🛑 Board ended early by {by_name}.")
    else:
        state["phase"] = "gameover"
        state["status"] = "finished"
        append_event(state, "System", f"🏁 Match ended by {by_name}.", kind="gameover")
        save_game(state["code"], state)
        sync_room_db_status(state["code"], "finished")


def reset_to_lobby(state: dict[str, Any]) -> None:
    """Return to Lobby while preserving teams and room score counters."""
    state["phase"] = "lobby"
    state["status"] = "open"
    state["started"] = False
    state["turn_phase"] = None
    state["turn_team"] = None
    state["current_clue"] = None
    state["current_turn"] = None
    state["winner"] = None
    state["win_reason"] = None
    state["board"] = []
    state["turns_log"] = []
    set_phase_timer(state, 0)
    append_event(state, "System", "🔄 Room returned to Lobby for next setup!")
    save_game(state["code"], state)
    sync_room_db_status(state["code"], "open")


def player_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    players = []
    for p in state.get("players", {}).values():
        players.append(
            {
                "id": p["id"],
                "name": p["name"],
                "team": p.get("team"),
                "role": p.get("role", "operative"),
                "is_admin": is_player_admin(state, p),
                "is_spectator": bool(p.get("is_spectator")),
                "is_table_player": bool(p.get("is_table_player")),
                "connected": bool(p.get("connected", True)),
            }
        )
    return sorted(
        players,
        key=lambda x: (
            0 if x["team"] == "red" else (1 if x["team"] == "blue" else 2),
            0 if x["role"] == "spymaster" else 1,
            x["name"].lower(),
        ),
    )


def get_sanitized_player_view(state: dict[str, Any], viewer_id: Optional[str]) -> dict[str, Any]:
    """Return zero-spoiler player state: never leak unrevealed keycard colors to Operatives."""
    phase = state.get("phase", "lobby")
    viewer = state.get("players", {}).get(viewer_id) if viewer_id else None
    is_admin = is_player_admin(state, viewer)
    is_spectator = bool(viewer.get("is_spectator")) if viewer else False
    viewer_team = viewer.get("team") if viewer else None
    viewer_role = viewer.get("role", "operative") if viewer else "operative"

    # Zero-spoiler guarantee: only active Spymasters (or finished board) see unrevealed affiliations
    can_see_keycard = bool(
        phase == "gameover" or (phase == "playing" and viewer_role == "spymaster" and not is_spectator)
    )

    board = state.get("board", [])
    red_left = sum(1 for c in board if c.get("affiliation") == "red" and not c.get("revealed"))
    blue_left = sum(1 for c in board if c.get("affiliation") == "blue" and not c.get("revealed"))

    sanitized_board = []
    for c in board:
        show_aff = bool(c.get("revealed") or can_see_keycard)
        sanitized_board.append(
            {
                "index": c["index"],
                "word": c["word_display"],
                "word_en": c["word_en"],
                "definition": c.get("definition", ""),
                "pos": c.get("pos", "noun"),
                "revealed": bool(c.get("revealed")),
                "revealed_by": c.get("revealed_by"),
                "affiliation": c.get("affiliation") if show_aff else None,
                "author_name": c.get("author_name"),
                "related": c.get("related", []) if can_see_keycard else [],
            }
        )

    turn_team = state.get("turn_team")
    turn_phase = state.get("turn_phase")
    is_active_spy = bool(
        phase == "playing"
        and turn_phase == "spymaster_clue"
        and viewer_role == "spymaster"
        and viewer_team == turn_team
        and not is_spectator
    )
    can_give_clue = bool(phase == "playing" and turn_phase == "spymaster_clue" and (is_active_spy or is_admin))
    can_guess = bool(
        phase == "playing"
        and turn_phase == "operative_guess"
        and ((viewer_team == turn_team and viewer_role == "operative" and not is_spectator) or is_admin)
    )

    suggestions: list[dict[str, Any]] = []
    if is_active_spy and board:
        suggestions = suggest_spymaster_clues(board, turn_team, max_suggestions=6)

    now = time.time()
    remaining_timer = 0
    if state.get("timer_paused_remaining") is not None:
        remaining_timer = max(0, int(state["timer_paused_remaining"]))
    elif state.get("timer_ends_at"):
        remaining_timer = max(0, int(round(state["timer_ends_at"] - now)))

    return {
        "type": "state",
        "version_counter": VERSION_COUNTER,
        "code": state.get("code"),
        "title": state.get("title"),
        "language": state.get("language", "en"),
        "language_support": get_game_language_support("codenames", state.get("language", "en")),
        "status": state.get("status", "open"),
        "phase": phase,
        "started": bool(state.get("started")),
        "round_num": state.get("round_num", 0),
        "red_wins": state.get("red_wins", 0),
        "blue_wins": state.get("blue_wins", 0),
        "starting_team": state.get("starting_team"),
        "turn_team": turn_team,
        "turn_phase": turn_phase,
        "guesses_remaining": state.get("guesses_remaining", 0),
        "red_remaining": red_left,
        "blue_remaining": blue_left,
        "current_clue": state.get("current_clue"),
        "winner": state.get("winner"),
        "win_reason": state.get("win_reason"),
        "board": sanitized_board,
        "can_see_keycard": can_see_keycard,
        "can_give_clue": can_give_clue,
        "can_guess": can_guess,
        "spymaster_suggestions": suggestions,
        "custom_deck_count": len(state.get("custom_deck", [])),
        "turns_log": state.get("turns_log", []),
        "rounds_history": state.get("rounds_history", []),
        "me": {
            "id": viewer_id,
            "name": viewer.get("name") if viewer else None,
            "team": viewer_team,
            "role": viewer_role,
            "is_admin": is_admin,
            "is_spectator": is_spectator,
            "is_spymaster": viewer_role == "spymaster" and not is_spectator,
            "token": viewer.get("token") if viewer else None,
        },
        "players": player_list(state),
        "settings": state.get("settings", DEFAULT_SETTINGS),
        "chat_log": list(state.get("chat_log", []))[-100:],
        "timer": {
            "duration": state.get("timer_duration", 0),
            "remaining": remaining_timer,
            "paused": state.get("timer_paused_remaining") is not None,
        },
    }


def export_game_replay(state: dict[str, Any]) -> dict[str, Any]:
    """Export a complete, self-contained JSON replay of the Codenames match."""
    return {
        "game": "codenames",
        "code": state.get("code"),
        "title": state.get("title"),
        "language": state.get("language", "en"),
        "round_num": state.get("round_num", 0),
        "red_wins": state.get("red_wins", 0),
        "blue_wins": state.get("blue_wins", 0),
        "players": player_list(state),
        "rounds_history": state.get("rounds_history", []),
        "active_turns": state.get("turns_log", []),
        "chat_log": state.get("chat_log", []),
    }

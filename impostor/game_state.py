"""Redis-backed game state engine for Advanced Word Impostor."""

import copy
import json
import os
import random
import time
import uuid
from typing import Any, Optional

import redis

from gamerooms.language_support import get_game_language_support, normalize_language_code

from .word_pairs import (
    CATEGORIES,
    normalize_text,
    pick_impostor_pair,
    text_matches_term,
)

_redis = None
_fallback_store: dict[str, str] = {}

POISON_MODES = (
    "undercover_blind",
    "undercover_informed",
    "poisoned_citizen",
    "classic_blank",
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "max_rounds": 5,
    "poison_mode": "undercover_blind",
    "enable_lethal_word": True,
    "enable_steal": True,
    "clue_loops": 2,
    "turn_timer": 0,
    "vote_timer": 0,
    "steal_timer": 0,
    "category": "all",
    "allow_custom_deck": True,
}


def _get_redis():
    global _redis
    if _redis is None:
        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        _redis = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
    return _redis


def _key(code: str) -> str:
    return f"impostor_room:{code.upper()}"


def create_initial_state(
    code: str,
    title: str = "Word Impostor Night",
    password: str = "",
    creator_name: str = "",
    language: str = "en",
    settings: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a fresh Word Impostor game state dictionary."""
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    if settings:
        merged.update(settings)

    return {
        "code": code.upper(),
        "title": title,
        "password": password,
        "language": normalize_language_code(language),
        "admin_token": uuid.uuid4().hex[:16],
        "status": "open",
        "phase": "lobby",  # lobby, clue, voting, last_chance, reveal, gameover
        "started": False,
        "round_num": 0,
        "players": {},  # pid -> {id, name, token, score, is_admin, is_spectator, connected, channel_name}
        "next_player_seq": 1,
        "creator": creator_name or None,
        "creator_id": None,
        "settings": merged,
        # Round-scoped secret & turn state
        "current_pair": None,
        "used_pairs": [],
        "custom_deck": [],  # [{citizen_word, poison_word, lethal_word, category, author_id, author_name}]
        "round_director_id": None,
        "round_participants": [],
        "impostor_id": None,
        "poisoned_citizen_id": None,
        "poisoned_ids": [],  # players eliminated mid-round by Lethal Taboo word
        "turn_order": [],  # ordered list of pids across clue_loops
        "turn_index": 0,
        "clues": [],  # [{player_id, player_name, text, spoken, loop, is_lethal, ts}]
        "votes": {},  # voter_pid -> target_pid
        "ejected_id": None,
        "steal_guess": None,
        "steal_success": False,
        "round_outcome": None,  # citizens_win, impostor_win, impostor_survived, impostor_steal, impostor_poisoned
        "round_summary": "",
        "score_deltas": {},
        "rounds_history": [],
        "chat_log": [],
        "next_chat_id": 1,
        "timer_duration": 0,
        "timer_ends_at": None,
        "timer_paused_remaining": None,
        "created_at": time.time(),
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
    base = (raw_name or "Player").strip()[:28] or "Player"
    existing = {p["name"].lower() for pid, p in state.get("players", {}).items() if pid != exclude_pid}
    if base.lower() not in existing:
        return base
    i = 2
    while f"{base} {i}".lower() in existing:
        i += 1
    return f"{base} {i}"


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
        "score": 0,
        "is_admin": make_admin,
        "is_spectator": False,
        "connected": True,
        "channel_name": channel_name,
    }
    state["players"][pid] = player
    if not state.get("creator") and make_admin:
        state["creator"] = clean_name
        state["creator_id"] = pid
    append_event(state, "System", f"🕵️ {clean_name} joined the room.", kind="join")
    save_game(state["code"], state)
    return state, player, True


def add_table_player(state: dict[str, Any], name: str) -> tuple[bool, str]:
    """Allow the Host/Moderator to add a local oral/couch player in the lobby."""
    if state.get("phase") != "lobby":
        return False, "Oral/table players can only be added while in the lobby."
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
        "score": 0,
        "is_admin": False,
        "is_spectator": False,
        "is_table_player": True,
        "connected": True,
        "channel_name": "",
    }
    state["players"][pid] = player
    append_event(state, "System", f"🪑 {clean_name} was added as an oral/table player.", kind="join")
    save_game(state["code"], state)
    return True, f"Added oral player {clean_name}."


def is_player_admin(state: dict[str, Any], player: Optional[dict[str, Any]]) -> bool:
    if not player:
        return False
    return bool(player.get("is_admin") or player.get("id") == state.get("creator_id"))


def kick_player(state: dict[str, Any], target_id: str, by_name: str = "Host") -> Optional[str]:
    target = state.get("players", {}).pop(target_id, None)
    if not target:
        return None
    if target_id in state.get("round_participants", []):
        state["round_participants"].remove(target_id)
    state["turn_order"] = [pid for pid in state.get("turn_order", []) if pid != target_id]
    state.get("votes", {}).pop(target_id, None)
    append_event(state, "System", f"👢 {target['name']} was removed by {by_name}.")
    save_game(state["code"], state)
    return target["name"]


def toggle_spectator(state: dict[str, Any], target_id: str) -> Optional[bool]:
    target = state.get("players", {}).get(target_id)
    if not target:
        return None
    target["is_spectator"] = not bool(target.get("is_spectator"))
    save_game(state["code"], state)
    return target["is_spectator"]


def update_settings(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    s = state.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))
    if "poison_mode" in patch and patch["poison_mode"] in POISON_MODES:
        s["poison_mode"] = patch["poison_mode"]
    if "enable_lethal_word" in patch:
        s["enable_lethal_word"] = bool(patch["enable_lethal_word"])
    if "enable_steal" in patch:
        s["enable_steal"] = bool(patch["enable_steal"])
    if "clue_loops" in patch or "rounds" in patch:
        raw_cycles = patch.get("clue_loops", patch.get("rounds", 2))
        s["clue_loops"] = max(1, min(10, int(raw_cycles or 2)))
    if "turn_timer" in patch:
        val = patch["turn_timer"]
        s["turn_timer"] = max(0, min(300, int(0 if val is None or val == "" else val)))
    if "vote_timer" in patch:
        val = patch["vote_timer"]
        s["vote_timer"] = max(0, min(180, int(0 if val is None or val == "" else val)))
    if "steal_timer" in patch:
        val = patch["steal_timer"]
        s["steal_timer"] = max(0, min(60, int(0 if val is None or val == "" else val)))
    if "max_rounds" in patch:
        s["max_rounds"] = max(1, min(20, int(patch["max_rounds"] or 5)))
    if "category" in patch and str(patch["category"]).lower() in CATEGORIES:
        s["category"] = str(patch["category"]).lower()
    if "allow_custom_deck" in patch:
        s["allow_custom_deck"] = bool(patch["allow_custom_deck"])
    save_game(state["code"], state)
    return s


def add_custom_pair(
    state: dict[str, Any],
    author: dict[str, Any],
    citizen_word: str,
    poison_word: str,
    lethal_word: str = "",
    category: str = "custom",
) -> tuple[bool, str]:
    citizen = (citizen_word or "").strip()[:60]
    poison = (poison_word or "").strip()[:60]
    lethal = (lethal_word or "").strip()[:60]
    if not citizen or not poison:
        return False, "Both Citizen Word and Poison Word are required."
    if normalize_text(citizen) == normalize_text(poison):
        return False, "Citizen Word and Poison Word must be different."
    if len(state.get("custom_deck", [])) >= 20:
        return False, "Custom deck is full (max 20 cards)."

    card = {
        "citizen_word": citizen,
        "poison_word": poison,
        "lethal_word": lethal,
        "category": (category or "custom").strip()[:24] or "custom",
        "author_id": author["id"],
        "author_name": author["name"],
    }
    state.setdefault("custom_deck", []).append(card)
    append_event(state, "System", f"🃏 {author['name']} added a secret Custom Pair card to the deck!")
    save_game(state["code"], state)
    return True, "Custom pair added."


def active_eligible_players(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in state.get("players", {}).values() if not p.get("is_spectator")]


def start_round(state: dict[str, Any], is_redraw: bool = False) -> tuple[bool, str]:
    """Deal a word pair and assign roles for a new round (or blind redraw)."""
    eligible = active_eligible_players(state)
    if len(eligible) < 2:
        return False, "At least 2 non-spectator players are required to start Word Impostor."

    s = state["settings"]
    lang = state.get("language", "en")

    # Peek at custom_deck to handle author director rule cleanly when > 3 players
    custom_deck = state.get("custom_deck", [])
    if is_redraw and state.get("current_pair"):
        prev_key = state["current_pair"].get("pair_key")
        if prev_key and prev_key not in state.setdefault("used_pairs", []):
            state["used_pairs"].append(prev_key)

    pair = pick_impostor_pair(
        category=s.get("category", "all"),
        lang_code=lang,
        used_pairs=state.get("used_pairs", []),
        custom_deck=custom_deck if not is_redraw else None,
    )
    if pair["pair_key"] not in state.setdefault("used_pairs", []):
        state["used_pairs"].append(pair["pair_key"])

    director_id = pair.get("author_id") if pair.get("author_id") in state["players"] else None
    participants = [p["id"] for p in eligible if p["id"] != director_id]
    # Guarantee at least 3 active participants in round; if author puts us below 3, include them normally
    if len(participants) < 3:
        director_id = None
        participants = [p["id"] for p in eligible]

    random.shuffle(participants)
    impostor_id = random.choice(participants)
    non_impostors = [pid for pid in participants if pid != impostor_id]

    poison_mode = s.get("poison_mode", "undercover_blind")
    poisoned_citizen_id = None
    if poison_mode == "poisoned_citizen" and non_impostors:
        poisoned_citizen_id = random.choice(non_impostors)

    if not is_redraw:
        state["round_num"] = state.get("round_num", 0) + 1

    state["started"] = True
    state["status"] = "running"
    state["phase"] = "clue"
    state["current_pair"] = pair
    state["round_director_id"] = director_id
    state["round_participants"] = participants
    state["impostor_id"] = impostor_id
    state["poisoned_citizen_id"] = poisoned_citizen_id
    state["poisoned_ids"] = []

    clue_loops = int(s.get("clue_loops", 1))
    turn_order = []
    for _loop in range(clue_loops):
        turn_order.extend(participants)
    state["turn_order"] = turn_order
    state["turn_index"] = 0
    state["clues"] = []
    state["votes"] = {}
    state["ejected_id"] = None
    state["steal_guess"] = None
    state["steal_success"] = False
    state["round_outcome"] = None
    state["round_summary"] = ""
    state["score_deltas"] = {}

    set_phase_timer(state, int(s.get("turn_timer", 45)))

    if is_redraw:
        append_event(state, "System", f"🎲 Blind Redraw! New secret words dealt for Round {state['round_num']}.")
    else:
        director_note = (
            f" (🎬 Round Director: {state['players'][director_id]['name']})"
            if director_id and director_id in state["players"]
            else ""
        )
        append_event(
            state,
            "System",
            f"🎬 Round {state['round_num']}/{s['max_rounds']} started — Category: {pair['category'].title()}{director_note}.",
        )
        sync_room_db_status(state["code"], "running")

    save_game(state["code"], state)
    return True, "Round started."


def current_turn_player_id(state: dict[str, Any]) -> Optional[str]:
    if state.get("phase") != "clue":
        return None
    order = state.get("turn_order", [])
    idx = state.get("turn_index", 0)
    if 0 <= idx < len(order):
        return order[idx]
    return None


def _advance_turn_or_vote(state: dict[str, Any]) -> None:
    """Advance turn_index past any poisoned/kicked players, or move into voting."""
    order = state.get("turn_order", [])
    poisoned = set(state.get("poisoned_ids", []))
    players = state.get("players", {})
    idx = state.get("turn_index", 0) + 1

    while idx < len(order):
        pid = order[idx]
        if pid in players and pid not in poisoned:
            state["turn_index"] = idx
            set_phase_timer(state, int(state["settings"].get("turn_timer", 45)))
            save_game(state["code"], state)
            return
        idx += 1

    # All turns complete -> begin voting phase
    start_voting_phase(state)


def submit_clue(
    state: dict[str, Any],
    player_id: str,
    clue_text: str = "",
    spoken: bool = False,
    target_player_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Record a clue turn (typed or spoken, directly or by the Moderator for an oral speaker)."""
    if state.get("phase") != "clue":
        return False, "Not currently in the clue phase."

    players = state.get("players", {})
    caller = players.get(player_id)
    if not caller:
        return False, "Player not found."

    caller_is_admin = is_player_admin(state, caller)
    active_pid = current_turn_player_id(state)
    participants = set(state.get("round_participants", []))
    poisoned = set(state.get("poisoned_ids", []))

    if caller_is_admin:
        if target_player_id:
            if target_player_id not in participants:
                return False, "Selected speaker is not participating in this round."
            speaker_id = target_player_id
        else:
            speaker_id = active_pid
    else:
        if player_id not in participants:
            return False, "Only active round participants can submit clues."
        speaker_id = player_id

    if not speaker_id or speaker_id not in players or speaker_id not in participants:
        return False, "Player not found in active round."
    if speaker_id in poisoned:
        return False, "Eliminated players cannot submit clues this round."

    player = players[speaker_id]
    by_mod = bool(caller_is_admin and speaker_id != player_id)

    pair = state.get("current_pair") or {}
    s = state["settings"]
    n_participants = max(1, len(participants))
    loop_num = (state.get("turn_index", 0) // n_participants) + 1

    if spoken:
        entry = {
            "player_id": speaker_id,
            "player_name": player["name"],
            "text": "🎙️ Spoke clue out loud",
            "spoken": True,
            "loop": loop_num,
            "is_lethal": False,
            "by_mod": by_mod,
            "ts": time.time(),
        }
        state.setdefault("clues", []).append(entry)
        mod_note = " (logged by Mod)" if by_mod else ""
        append_event(state, player["name"], f"🎙️ Gave clue out loud.{mod_note}", kind="clue", sender_id=speaker_id)
        if speaker_id == active_pid:
            _advance_turn_or_vote(state)
        else:
            save_game(state["code"], state)
        return True, "Spoken clue recorded."

    cleaned = " ".join(str(clue_text or "").strip().split())[:80]
    if not cleaned:
        return False, "Enter a clue word/phrase or press 'Spoke Out Loud'."

    # Block saying the exact citizen or poison word verbatim (anti-spoiler)
    if text_matches_term(cleaned, pair.get("citizen_matches", [])):
        return False, "🚫 That clue contains the secret Citizen word! Try an indirect clue."
    if state.get("settings", {}).get("poison_mode") in ("undercover_blind", "undercover_informed", "poisoned_citizen"):
        if text_matches_term(cleaned, pair.get("poison_matches", [])) and speaker_id == state.get("impostor_id"):
            return False, "🚫 Careful — you cannot say your secret word verbatim!"

    # Check Lethal Taboo Poison Word trap!
    hit_lethal = bool(
        s.get("enable_lethal_word", True)
        and pair.get("lethal_matches")
        and text_matches_term(cleaned, pair["lethal_matches"])
    )

    entry = {
        "player_id": speaker_id,
        "player_name": player["name"],
        "text": cleaned,
        "spoken": False,
        "loop": loop_num,
        "is_lethal": hit_lethal,
        "by_mod": by_mod,
        "ts": time.time(),
    }
    state.setdefault("clues", []).append(entry)

    if hit_lethal:
        state.setdefault("poisoned_ids", []).append(speaker_id)
        lethal_disp = pair.get("lethal_display") or pair.get("lethal_word")
        append_event(
            state,
            "System",
            f"☠️ POISONED! {player['name']} said Lethal Taboo word '{lethal_disp}' and is eliminated for this round!",
            kind="poison",
        )
        # Check immediate round-end conditions
        if speaker_id == state.get("impostor_id"):
            _finalize_reveal(
                state,
                outcome="impostor_poisoned",
                summary=f"☠️ Impostor {player['name']} stepped on the Lethal Poison Word '{lethal_disp}'! Citizens win the round!",
            )
            return True, "Lethal poison word triggered — Impostor eliminated!"
        remaining_citizens = [
            pid
            for pid in state.get("round_participants", [])
            if pid != state.get("impostor_id") and pid not in state.get("poisoned_ids", [])
        ]
        min_citizens = 2 if len(participants) >= 3 else 1
        if len(remaining_citizens) < min_citizens:
            _finalize_reveal(
                state,
                outcome="impostor_win",
                summary=f"☠️ Too many Citizens poisoned out! The Impostor dominates Round {state['round_num']}.",
            )
            return True, "Lethal poison word triggered!"
    else:
        mod_note = " (logged by Mod)" if by_mod else ""
        append_event(state, player["name"], f'💬 Clue: "{cleaned}"{mod_note}', kind="clue", sender_id=speaker_id)

    if speaker_id == active_pid:
        _advance_turn_or_vote(state)
    else:
        save_game(state["code"], state)
    return True, "Clue submitted."


def skip_current_turn(state: dict[str, Any], by_name: str = "Host") -> bool:
    if state.get("phase") != "clue":
        return False
    pid = current_turn_player_id(state)
    pname = state.get("players", {}).get(pid, {}).get("name", "Player") if pid else "Player"
    append_event(state, "System", f"⏭️ {pname}'s clue turn was skipped by {by_name}.")
    _advance_turn_or_vote(state)
    return True


def start_voting_phase(state: dict[str, Any]) -> None:
    if state.get("phase") in ("reveal", "gameover"):
        return
    state["phase"] = "voting"
    state["votes"] = {}
    set_phase_timer(state, int(state["settings"].get("vote_timer", 30)))
    append_event(state, "System", "🗳️ Clue phase complete — Discussion & Voting is now open! Vote for the Impostor.")
    save_game(state["code"], state)


def eligible_voters(state: dict[str, Any]) -> list[str]:
    poisoned = set(state.get("poisoned_ids", []))
    players = state.get("players", {})
    return [pid for pid in state.get("round_participants", []) if pid in players and pid not in poisoned]


def cast_vote(
    state: dict[str, Any],
    voter_id: str,
    target_id: str,
    on_behalf_of: Optional[str] = None,
    auto_tally: bool = True,
) -> tuple[bool, str]:
    """Record a vote directly from a player or assigned on someone's behalf by the Moderator."""
    if state.get("phase") != "voting":
        return False, "Voting is not open right now."

    players = state.get("players", {})
    caller = players.get(voter_id)
    caller_is_admin = is_player_admin(state, caller)
    effective_voter = str(on_behalf_of) if (caller_is_admin and on_behalf_of) else voter_id

    voters = eligible_voters(state)
    if effective_voter not in voters:
        if caller_is_admin and on_behalf_of:
            return False, "Selected voter is not eligible to vote this round."
        return False, "You are not eligible to vote this round."
    if target_id not in voters:
        return False, "Invalid vote target."
    if target_id == effective_voter:
        return False, "You cannot vote for yourself."

    state.setdefault("votes", {})[effective_voter] = target_id
    voter_name = players[effective_voter]["name"]
    target_name = players[target_id]["name"]
    mod_note = " (set by Mod)" if (caller_is_admin and effective_voter != voter_id) else ""
    append_event(state, "System", f"🗳️ {voter_name} pointed at {target_name}.{mod_note}", kind="vote")
    save_game(state["code"], state)

    if auto_tally and len(state["votes"]) >= len(voters):
        resolve_voting(state)
    return True, "Vote recorded."


def resolve_voting(state: dict[str, Any]) -> None:
    """Tally suspicion votes and either launch Last-Chance Impostor Steal or finalize Reveal."""
    if state.get("phase") != "voting":
        return

    votes = state.get("votes", {})
    counts: dict[str, int] = {}
    for target_id in votes.values():
        counts[target_id] = counts.get(target_id, 0) + 1

    if not counts:
        state["ejected_id"] = None
        _finalize_reveal(
            state,
            outcome="impostor_survived",
            summary="🕵️ No votes were cast — the Impostor slips away!",
        )
        return

    top_votes = max(counts.values())
    top_targets = [pid for pid, c in counts.items() if c == top_votes]

    if len(top_targets) > 1:
        tied_names = ", ".join(state["players"].get(pid, {}).get("name", "?") for pid in top_targets)
        state["ejected_id"] = None
        _finalize_reveal(
            state,
            outcome="impostor_survived",
            summary=f"⚖️ Vote tied between {tied_names} — No ejection, Impostor escapes!",
        )
        return

    ejected_id = top_targets[0]
    state["ejected_id"] = ejected_id
    ejected_name = state["players"].get(ejected_id, {}).get("name", "?")

    if ejected_id == state.get("impostor_id"):
        steal_enabled = bool(state["settings"].get("enable_steal", True))
        steal_sec = int(state["settings"].get("steal_timer", 0))
        if steal_enabled:
            state["phase"] = "last_chance"
            set_phase_timer(state, steal_sec)
            timer_note = f"{steal_sec}s" if steal_sec > 0 else "untimed"
            append_event(
                state,
                "System",
                f"⚡ {ejected_name} IS the Impostor! Last-Chance Steal ({timer_note}): {ejected_name} gets one guess at the Citizen Word!",
            )
            save_game(state["code"], state)
            return

        _finalize_reveal(
            state,
            outcome="citizens_win",
            summary=f"🎉 {ejected_name} was the Impostor! Citizens win the round!",
        )
        return

    _finalize_reveal(
        state,
        outcome="impostor_win",
        summary=f"💥 {ejected_name} was an innocent Citizen! The Impostor fooled the table!",
    )


def submit_steal_guess(state: dict[str, Any], player_id: str, guess_text: str) -> tuple[bool, str]:
    """Handle the 15-second Last-Chance Impostor Steal attempt."""
    if state.get("phase") != "last_chance":
        return False, "Not in Last-Chance Steal phase."
    if player_id != state.get("impostor_id"):
        return False, "Only the caught Impostor can make the Last-Chance Steal guess."

    cleaned = " ".join(str(guess_text or "").strip().split())[:80]
    state["steal_guess"] = cleaned or "(passed)"
    pair = state.get("current_pair") or {}

    if cleaned and text_matches_term(cleaned, pair.get("citizen_matches", []), allow_substring_word=False):
        state["steal_success"] = True
        _finalize_reveal(
            state,
            outcome="impostor_steal",
            summary=f"🔥 HEIST! Caught Impostor guessed '{pair.get('citizen_display')}' and STOLE the round!",
        )
        return True, "Last-Chance Steal succeeded!"

    state["steal_success"] = False
    _finalize_reveal(
        state,
        outcome="citizens_win",
        summary=f"🛡️ Impostor guessed '{state['steal_guess']}' — WRONG! Citizens win the round!",
    )
    return True, "Last-Chance Steal failed."


def expire_last_chance(state: dict[str, Any]) -> None:
    if state.get("phase") != "last_chance":
        return
    state["steal_guess"] = "(timed out)"
    state["steal_success"] = False
    _finalize_reveal(
        state,
        outcome="citizens_win",
        summary="⌛ Impostor ran out of time on the Last-Chance Steal — Citizens win the round!",
    )


def _finalize_reveal(state: dict[str, Any], outcome: str, summary: str) -> None:
    """Award round scores, store round replay summary, and enter 'reveal' phase."""
    state["phase"] = "reveal"
    state["round_outcome"] = outcome
    state["round_summary"] = summary
    state["timer_duration"] = 0
    state["timer_ends_at"] = None
    state["timer_paused_remaining"] = None

    impostor_id = state.get("impostor_id")
    poisoned_citizen_id = state.get("poisoned_citizen_id")
    deltas: dict[str, int] = {pid: 0 for pid in state.get("round_participants", [])}

    if outcome in ("citizens_win", "impostor_poisoned"):
        for pid in state.get("round_participants", []):
            if pid != impostor_id and pid not in state.get("poisoned_ids", []):
                deltas[pid] = 2
        if poisoned_citizen_id and poisoned_citizen_id != state.get("ejected_id") and poisoned_citizen_id in deltas:
            deltas[poisoned_citizen_id] += 1  # Survived false suspicion despite holding Poison Word!
    else:
        if impostor_id in deltas:
            deltas[impostor_id] = 3

    for pid, pts in deltas.items():
        if pid in state.get("players", {}):
            state["players"][pid]["score"] = state["players"][pid].get("score", 0) + pts

    state["score_deltas"] = deltas
    pair = state.get("current_pair") or {}
    state.setdefault("rounds_history", []).append(
        {
            "round": state.get("round_num", 1),
            "pair_key": pair.get("pair_key"),
            "category": pair.get("category"),
            "citizen_word": pair.get("citizen_display") or pair.get("citizen_word"),
            "poison_word": pair.get("poison_display") or pair.get("poison_word"),
            "lethal_word": pair.get("lethal_display") or pair.get("lethal_word"),
            "impostor_name": state.get("players", {}).get(impostor_id, {}).get("name", "?"),
            "poisoned_citizen_name": (
                state.get("players", {}).get(poisoned_citizen_id, {}).get("name") if poisoned_citizen_id else None
            ),
            "outcome": outcome,
            "summary": summary,
            "clues": list(state.get("clues", [])),
        }
    )

    append_event(state, "System", summary, kind="reveal")
    save_game(state["code"], state)


def end_match(state: dict[str, Any], by_name: str = "Host") -> None:
    state["phase"] = "gameover"
    state["status"] = "finished"
    state["timer_duration"] = 0
    state["timer_ends_at"] = None
    state["timer_paused_remaining"] = None
    append_event(state, "System", f"🏆 Match finished by {by_name}!", kind="gameover")
    sync_room_db_status(state["code"], "finished")
    save_game(state["code"], state)


def player_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    active_pid = current_turn_player_id(state)
    poisoned = set(state.get("poisoned_ids", []))
    voted_pids = set(state.get("votes", {}).keys())
    director_id = state.get("round_director_id")
    out = []
    for pid, p in state.get("players", {}).items():
        out.append(
            {
                "id": pid,
                "name": p["name"],
                "score": p.get("score", 0),
                "is_admin": is_player_admin(state, p),
                "is_spectator": bool(p.get("is_spectator", False)),
                "is_table_player": bool(p.get("is_table_player", False)),
                "is_turn": pid == active_pid,
                "is_poisoned": pid in poisoned,
                "is_director": pid == director_id,
                "has_voted": pid in voted_pids,
                "connected": bool(p.get("connected", False)),
            }
        )
    return out


def _build_player_card(state: dict[str, Any], viewer_id: Optional[str]) -> Optional[dict[str, Any]]:
    """Build ONLY this single player's secret card without exposing other roles/words."""
    if not viewer_id or viewer_id not in state.get("players", {}):
        return None
    if state.get("phase") not in ("clue", "voting", "last_chance", "reveal"):
        return None

    pair = state.get("current_pair") or {}
    s = state.get("settings", DEFAULT_SETTINGS)
    poison_mode = s.get("poison_mode", "undercover_blind")
    impostor_id = state.get("impostor_id")
    poisoned_citizen_id = state.get("poisoned_citizen_id")

    if viewer_id == state.get("round_director_id"):
        return {
            "role_type": "director",
            "role_label": "🎬 Round Director (Your Custom Card)",
            "role_revealed": True,
            "word": f"Citizens: {pair.get('citizen_display')} | Poison: {pair.get('poison_display')}",
            "category": pair.get("category"),
            "lethal_word_preview": pair.get("lethal_display") if s.get("enable_lethal_word") else None,
            "lethal_active": bool(s.get("enable_lethal_word") and pair.get("lethal_display")),
        }

    if viewer_id not in state.get("round_participants", []):
        return {
            "role_type": "spectator",
            "role_label": "👀 Spectator",
            "role_revealed": True,
            "word": None,
            "category": pair.get("category"),
            "lethal_active": bool(s.get("enable_lethal_word") and pair.get("lethal_display")),
        }

    is_imp = viewer_id == impostor_id
    is_poisoned_cit = viewer_id == poisoned_citizen_id
    citizen_word = pair.get("citizen_display") or pair.get("citizen_word")
    poison_word = pair.get("poison_display") or pair.get("poison_word")
    lethal_active = bool(s.get("enable_lethal_word") and (pair.get("lethal_display") or pair.get("lethal_word")))

    if poison_mode == "undercover_blind":
        return {
            "role_type": "mystery",
            "role_label": "🔒 Secret Word (Blind Role)",
            "role_revealed": False,
            "word": poison_word if is_imp else citizen_word,
            "category": pair.get("category"),
            "lethal_active": lethal_active,
        }
    if poison_mode == "undercover_informed":
        return {
            "role_type": "impostor" if is_imp else "citizen",
            "role_label": "🕵️ Impostor (Poison Word)" if is_imp else "🟢 Citizen",
            "role_revealed": True,
            "word": poison_word if is_imp else citizen_word,
            "category": pair.get("category"),
            "lethal_active": lethal_active,
        }
    if poison_mode == "poisoned_citizen":
        if is_imp:
            return {
                "role_type": "impostor",
                "role_label": "🕵️ Impostor (No Word — Bluff from Category!)",
                "role_revealed": True,
                "word": None,
                "category": pair.get("category"),
                "lethal_active": lethal_active,
            }
        # Poisoned Citizen's card looks IDENTICAL to a regular Citizen card!
        return {
            "role_type": "citizen",
            "role_label": "🟢 Citizen",
            "role_revealed": False,
            "word": poison_word if is_poisoned_cit else citizen_word,
            "category": pair.get("category"),
            "lethal_active": lethal_active,
        }

    # classic_blank
    if is_imp:
        return {
            "role_type": "impostor",
            "role_label": "🕵️ Impostor (Blank Card)",
            "role_revealed": True,
            "word": None,
            "category": pair.get("category"),
            "lethal_active": lethal_active,
        }
    return {
        "role_type": "citizen",
        "role_label": "🟢 Citizen",
        "role_revealed": True,
        "word": citizen_word,
        "category": pair.get("category"),
        "lethal_active": lethal_active,
    }


def get_sanitized_player_view(state: dict[str, Any], viewer_id: Optional[str] = None) -> dict[str, Any]:
    """
    Build strict zero-spoiler state for a player (including a Participating Game Master).
    Neither citizen_word, poison_word, lethal_word, nor impostor_id are exposed until 'reveal'/'gameover'.
    """
    phase = state.get("phase", "lobby")
    viewer = state.get("players", {}).get(viewer_id) if viewer_id else None
    is_admin = is_player_admin(state, viewer)
    active_pid = current_turn_player_id(state)

    now = time.time()
    remaining_timer = 0
    if state.get("timer_paused_remaining") is not None:
        remaining_timer = max(0, int(state["timer_paused_remaining"]))
    elif state.get("timer_ends_at"):
        remaining_timer = max(0, int(round(state["timer_ends_at"] - now)))

    reveal_truth = None
    if phase in ("reveal", "gameover") and state.get("current_pair"):
        pair = state["current_pair"]
        players = state.get("players", {})
        imp_id = state.get("impostor_id")
        pc_id = state.get("poisoned_citizen_id")
        ej_id = state.get("ejected_id")
        vote_breakdown = [
            {
                "voter": players.get(v_pid, {}).get("name", "?"),
                "target": players.get(t_pid, {}).get("name", "?"),
            }
            for v_pid, t_pid in state.get("votes", {}).items()
        ]
        reveal_truth = {
            "citizen_word": pair.get("citizen_display") or pair.get("citizen_word"),
            "citizen_word_en": pair.get("citizen_word"),
            "poison_word": pair.get("poison_display") or pair.get("poison_word"),
            "poison_word_en": pair.get("poison_word"),
            "lethal_word": pair.get("lethal_display") or pair.get("lethal_word"),
            "category": pair.get("category"),
            "impostor_id": imp_id,
            "impostor_name": players.get(imp_id, {}).get("name", "?"),
            "poisoned_citizen_id": pc_id,
            "poisoned_citizen_name": players.get(pc_id, {}).get("name") if pc_id else None,
            "ejected_id": ej_id,
            "ejected_name": players.get(ej_id, {}).get("name") if ej_id else None,
            "steal_guess": state.get("steal_guess"),
            "steal_success": bool(state.get("steal_success")),
            "outcome": state.get("round_outcome"),
            "summary": state.get("round_summary"),
            "votes": vote_breakdown,
            "score_deltas": {
                players.get(pid, {}).get("name", pid): pts for pid, pts in state.get("score_deltas", {}).items() if pts
            },
        }

    voters = eligible_voters(state)
    n_part = max(1, len(state.get("round_participants", [])))
    total_cycles = int(state.get("settings", DEFAULT_SETTINGS).get("clue_loops", 2))
    current_cycle = min(total_cycles, (state.get("turn_index", 0) // n_part) + 1)
    can_steal = bool(phase == "last_chance" and viewer_id and viewer_id == state.get("impostor_id"))
    can_vote = bool(phase == "voting" and viewer_id and viewer_id in voters)
    poisoned_set = set(state.get("poisoned_ids", []))
    players_map = state.get("players", {})
    round_participant_list = [
        {
            "id": pid,
            "name": players_map[pid]["name"],
            "is_poisoned": pid in poisoned_set,
        }
        for pid in state.get("round_participants", [])
        if pid in players_map
    ]

    return {
        "type": "state",
        "code": state.get("code"),
        "title": state.get("title"),
        "language": state.get("language", "en"),
        "language_support": get_game_language_support("impostor", state.get("language", "en")),
        "status": state.get("status", "open"),
        "phase": phase,
        "started": bool(state.get("started")),
        "round_num": state.get("round_num", 0),
        "max_rounds": state.get("settings", DEFAULT_SETTINGS).get("max_rounds", 5),
        "current_cycle": current_cycle,
        "total_cycles": total_cycles,
        "current_category": (state.get("current_pair") or {}).get("category") if phase != "lobby" else None,
        "current_player": state.get("players", {}).get(active_pid, {}).get("name") if active_pid else None,
        "current_player_id": active_pid,
        "round_participant_list": round_participant_list,
        "clues_count": len(state.get("clues", [])),
        "clues": list(state.get("clues", [])),
        "custom_deck_count": len(state.get("custom_deck", [])),
        "can_blind_redraw": bool(phase == "clue" and len(state.get("clues", [])) == 0),
        "can_vote": can_vote,
        "votes": dict(state.get("votes", {})),
        "eligible_voter_ids": voters,
        "my_vote": state.get("votes", {}).get(viewer_id) if viewer_id else None,
        "can_steal": can_steal,
        "my_card": _build_player_card(state, viewer_id),
        "reveal": reveal_truth,
        "me": {
            "id": viewer_id,
            "name": viewer.get("name") if viewer else None,
            "score": viewer.get("score", 0) if viewer else 0,
            "is_admin": is_admin,
            "is_turn": bool(viewer_id and viewer_id == active_pid),
            "is_spectator": bool(viewer.get("is_spectator", False)) if viewer else False,
            "is_poisoned": bool(viewer_id and viewer_id in state.get("poisoned_ids", [])),
            "is_director": bool(viewer_id and viewer_id == state.get("round_director_id")),
            "token": viewer.get("token") if viewer else None,
        },
        "players": player_list(state),
        "settings": state.get("settings", DEFAULT_SETTINGS),
        "rounds_history": state.get("rounds_history", []),
        "chat_log": list(state.get("chat_log", []))[-100:],
        "timer": {
            "duration": state.get("timer_duration", 0),
            "remaining": remaining_timer,
            "paused": state.get("timer_paused_remaining") is not None,
        },
    }

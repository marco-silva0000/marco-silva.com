"""Redis-backed game state engine for Stop! (Categories & Letter Speed Race)."""

import copy
import json
import os
import time
import uuid
from typing import Any, Optional

import redis

from gamerooms.language_support import get_game_language_support, normalize_language_code
from gamerooms.player_colors import (
    assign_distinct_player_color,
    get_player_initials,
    is_valid_color_hex,
)
from gamerooms.prompt_engine.evaluator import cluster_answer_keys
from impostor.word_pairs import normalize_text
from website.version import VERSION_COUNTER

from .categories import (
    CATEGORY_PACKS,
    get_sample_db_words,
    is_word_in_db,
    normalize_answer,
    pick_category_and_letter,
    starts_with_letter,
)

_redis = None
_fallback_store: dict[str, str] = {}

STOP_MODES = (
    "countdown_on_first",
    "instant_stop",
    "wait_all_or_timer",
)

CLASH_RULES = (
    "shared",
    "first_steals",
    "zero_clash",
    "none",  # No collision penalty (all valid score full points)
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "max_rounds": 8,  # 0 = infinite (until host ends)
    "round_timer": 30,
    "category_pack": "mix",
    "stop_mode": "countdown_on_first",
    "stop_countdown": 10,
    "clash_rule": "shared",
    "fuzzy_clash": True,
    "easy_letters_only": True,
    "allow_custom_categories": True,
}


def _get_redis():
    global _redis
    if _redis is None:
        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        _redis = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
    return _redis


def _key(code: str) -> str:
    return f"stop_room:{code.upper()}"


def create_initial_state(
    code: str,
    title: str = "Stop! Party Room",
    password: str = "",
    creator_name: str = "",
    language: str = "en",
    settings: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a fresh Stop! room state dictionary."""
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
        "phase": "lobby",  # lobby, playing, reveal, gameover
        "started": False,
        "round_num": 0,
        "players": {},  # pid -> {id, name, token, score, is_admin, is_spectator, connected, channel_name}
        "next_player_seq": 1,
        "creator": creator_name or None,
        "creator_id": None,
        "settings": merged,
        # Category & Letter round state
        "current_category": None,  # {id, title, source, pack, author_name?}
        "current_letter": "",
        "used_categories": [],
        "custom_categories": [],  # [{id, title, source: 'custom', pack: 'custom', author_id, author_name}]
        "round_participants": [],
        "round_started_at": None,
        "stop_called_by": None,
        "stop_reason": "",
        # Submissions: pid -> {player_id, player_name, raw_text, norm_key, elapsed_ms, order_rank, valid_letter, in_db, vetoed_by, host_override}
        "submissions": {},
        "next_submission_seq": 1,
        # Scored results for current round (populated in reveal / gameover)
        "round_results": [],
        "score_deltas": {},
        "applied_round_deltas": {},
        "sample_db_words": [],
        "round_summary": "",
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

    by_name = find_player_by_name(state, name)
    # Reclaim existing player if offline, or if this is the Host reconnecting
    if by_name:
        is_host_reconnect = is_admin and (by_name.get("is_admin") or by_name.get("id") == state.get("creator_id"))
        if is_host_reconnect or not by_name.get("connected", False):
            by_name["connected"] = True
            if channel_name:
                by_name["channel_name"] = channel_name
            if is_admin:
                by_name["is_admin"] = True
            save_game(state["code"], state)
            return state, by_name, False

    seq = state.get("next_player_seq", 1)
    pid = f"p{seq}"
    state["next_player_seq"] = seq + 1

    clean_name = _unique_name(state, name)
    has_any_admin = any(p.get("is_admin") for p in state.get("players", {}).values())
    grant_admin = bool(is_admin or not has_any_admin)

    assigned_color = assign_distinct_player_color(state.get("players", {}))
    player = {
        "id": pid,
        "name": clean_name,
        "color": assigned_color,
        "initials": get_player_initials(clean_name),
        "token": token or uuid.uuid4().hex[:20],
        "score": 0,
        "is_admin": grant_admin,
        "is_spectator": False,
        "connected": True,
        "channel_name": channel_name or None,
    }
    state.setdefault("players", {})[pid] = player

    if grant_admin and not state.get("creator_id"):
        state["creator_id"] = pid
        state["creator"] = clean_name

    # If joining mid-round while playing, let them participate immediately
    if state.get("phase") == "playing" and pid not in state.get("round_participants", []):
        state.setdefault("round_participants", []).append(pid)

    append_event(state, "System", f"👋 {clean_name} joined the room.")
    save_game(state["code"], state)
    return state, player, True


def change_player_color(
    state: dict[str, Any],
    target_player_id: str,
    new_color: str,
    requested_by_admin: bool = False,
    requester_player_id: str = "",
) -> bool:
    """Allow player to pick their badge color, or host to reassign any player's color."""
    if not is_valid_color_hex(new_color):
        return False
    player = state.get("players", {}).get(target_player_id)
    if not player:
        return False
    if target_player_id != requester_player_id and not requested_by_admin:
        return False
    player["color"] = new_color.strip()
    save_game(state["code"], state)
    return True


def is_player_admin(state: dict[str, Any], player: Optional[dict[str, Any]]) -> bool:
    if not player:
        return False
    return bool(player.get("is_admin") or player.get("id") == state.get("creator_id"))


def active_players(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in state.get("players", {}).values() if not p.get("is_spectator")]


def toggle_spectator(state: dict[str, Any], player_id: str) -> bool:
    p = state.get("players", {}).get(player_id)
    if not p:
        return False
    p["is_spectator"] = not p.get("is_spectator", False)
    mode_str = "Spectator 👀" if p["is_spectator"] else "Active Player 🎮"
    append_event(state, "System", f"{p['name']} is now {mode_str}.")
    save_game(state["code"], state)
    return True


def kick_player(state: dict[str, Any], target_id: str, by_name: str = "Host") -> Optional[dict[str, Any]]:
    players = state.get("players", {})
    removed = players.pop(target_id, None)
    if not removed:
        return None
    if target_id in state.get("round_participants", []):
        state["round_participants"] = [pid for pid in state["round_participants"] if pid != target_id]
    state.get("submissions", {}).pop(target_id, None)
    append_event(state, "System", f"🥾 {removed['name']} was removed by {by_name}.")
    save_game(state["code"], state)
    return removed


def transfer_host(state: dict[str, Any], target_id: str) -> bool:
    """Transfer room creator / host role to another player."""
    target = state.get("players", {}).get(target_id)
    if not target:
        return False
    target["is_admin"] = True
    state["creator_id"] = target_id
    state["creator"] = target["name"]
    append_event(state, "System", f"👑 Room Host privileges transferred to {target['name']}.")
    save_game(state["code"], state)
    return True


def update_settings(state: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    s = state.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))
    if "max_rounds" in raw:
        try:
            s["max_rounds"] = max(0, min(50, int(raw["max_rounds"])))
        except (ValueError, TypeError):
            pass
    if "round_timer" in raw:
        try:
            s["round_timer"] = max(0, min(180, int(raw["round_timer"])))
        except (ValueError, TypeError):
            pass
    if "category_pack" in raw and raw["category_pack"] in CATEGORY_PACKS:
        s["category_pack"] = raw["category_pack"]
    if "stop_mode" in raw and raw["stop_mode"] in STOP_MODES:
        s["stop_mode"] = raw["stop_mode"]
    if "stop_countdown" in raw:
        try:
            s["stop_countdown"] = max(3, min(30, int(raw["stop_countdown"])))
        except (ValueError, TypeError):
            pass
    if "clash_rule" in raw and raw["clash_rule"] in CLASH_RULES:
        s["clash_rule"] = raw["clash_rule"]
    if "fuzzy_clash" in raw:
        s["fuzzy_clash"] = bool(raw["fuzzy_clash"])
    if "easy_letters_only" in raw:
        s["easy_letters_only"] = bool(raw["easy_letters_only"])
    if "allow_custom_categories" in raw:
        s["allow_custom_categories"] = bool(raw["allow_custom_categories"])

    save_game(state["code"], state)
    return s


def add_custom_category(
    state: dict[str, Any],
    author: dict[str, Any],
    title: str,
) -> tuple[bool, str]:
    """Add a player/host custom category prompt to the room deck."""
    clean = " ".join(str(title or "").strip().split())[:90]
    if len(clean) < 2:
        return False, "Category title must be at least 2 characters."

    norm_id = f"custom::{normalize_text(clean)}"
    custom_list = state.setdefault("custom_categories", [])
    if any(c.get("id") == norm_id for c in custom_list):
        return False, "That custom category is already in the room deck."

    entry = {
        "id": norm_id,
        "title": f"✨ {clean}" if not clean[0].isalnum() else f"✨ {clean}",
        "raw_title": clean,
        "source": "custom",
        "pack": "custom",
        "author_id": author.get("id"),
        "author_name": author.get("name", "Player"),
    }
    custom_list.append(entry)
    append_event(state, "System", f"✨ {author.get('name', 'Player')} added custom category: “{clean}”")
    save_game(state["code"], state)
    return True, "Custom category added!"


def remove_custom_category(state: dict[str, Any], cat_id: str) -> bool:
    before = len(state.get("custom_categories", []))
    state["custom_categories"] = [c for c in state.get("custom_categories", []) if c.get("id") != cat_id]
    changed = len(state["custom_categories"]) < before
    if changed:
        save_game(state["code"], state)
    return changed


def start_round(
    state: dict[str, Any],
    is_redraw: bool = False,
    forced_category: str = "",
    forced_letter: str = "",
    from_round: Optional[int] = None,
) -> tuple[bool, str]:
    """Start the next Stop! round (or redraw current category & letter) with debounce and countdown."""
    cur_round = int(state.get("round_num", 0))
    if from_round is not None and not is_redraw and int(from_round) != cur_round:
        return False, f"Round already started ({cur_round})."

    now = time.time()
    last_from = state.get("last_advanced_from_round")
    last_advance = state.get("last_round_advance_at", 0)
    if not is_redraw and last_from == cur_round and (now - last_advance < 2.0):
        return False, "Please wait, round is currently advancing."
    state["last_advanced_from_round"] = cur_round
    state["last_round_advance_at"] = now

    participants = [p["id"] for p in active_players(state)]
    if not participants:
        return False, "At least 1 active player is required to start a round."

    if not is_redraw or cur_round == 0:
        state["round_num"] = cur_round + 1

    s = state.get("settings", DEFAULT_SETTINGS)
    cat, letter = pick_category_and_letter(
        pack=s.get("category_pack", "mix"),
        lang_code=state.get("language", "en"),
        used_categories=state.get("used_categories", []),
        custom_categories=state.get("custom_categories", []),
        easy_letters_only=bool(s.get("easy_letters_only", True)),
        last_letter=state.get("current_letter", ""),
        forced_category_title=forced_category,
        forced_letter=forced_letter,
    )

    state["started"] = True
    state["status"] = "running"
    state["phase"] = "playing"
    state["current_category"] = cat
    state["current_letter"] = letter
    if cat.get("id") and cat["id"] not in state.get("used_categories", []):
        state.setdefault("used_categories", []).append(cat["id"])

    state["round_participants"] = participants
    countdown_sec = 4.0
    state["round_countdown_until"] = now + countdown_sec
    state["round_started_at"] = now + countdown_sec
    state["stop_called_by"] = None
    state["stop_reason"] = ""
    state["submissions"] = {}
    state["next_submission_seq"] = 1
    state["round_results"] = []
    state["score_deltas"] = {}
    state["applied_round_deltas"] = {}
    state["sample_db_words"] = []
    state["round_summary"] = ""

    timer_sec = int(s.get("round_timer", 30) or 0)
    if timer_sec > 0:
        state["timer_duration"] = timer_sec
        state["timer_ends_at"] = (now + countdown_sec) + timer_sec
        state["timer_paused_remaining"] = None
    else:
        state["timer_duration"] = 0
        state["timer_ends_at"] = None
        state["timer_paused_remaining"] = None
    sync_room_db_status(state["code"], "running")

    action_label = "🔄 Redrew" if is_redraw else f"🚦 Round {state['round_num']}"
    append_event(
        state,
        "System",
        f"{action_label}: Category “{cat['title']}” · Letter “{letter}” — Race for a unique answer!",
    )
    save_game(state["code"], state)
    return True, "Round started!"


def submit_answer(
    state: dict[str, Any],
    player_id: str,
    answer_text: str,
    call_stop_now: bool = False,
) -> tuple[bool, str]:
    """Record or update a player's answer during the `playing` phase."""
    if state.get("phase") != "playing":
        return False, "Round is not currently accepting answers."

    player = state.get("players", {}).get(player_id)
    if not player or player.get("is_spectator"):
        return False, "Only active players can submit answers."

    clean = " ".join(str(answer_text or "").strip().split())[:80]
    if not clean:
        return False, "Please enter an answer."

    letter = state.get("current_letter", "A")
    cat = state.get("current_category") or {}
    cat_id = cat.get("id", "")
    lang = state.get("language", "en")

    now = time.time()
    started_at = state.get("round_started_at") or now
    elapsed_ms = max(10, int(round((now - started_at) * 1000)))

    seq = int(state.get("next_submission_seq", 1))
    state["next_submission_seq"] = seq + 1

    valid_letter = starts_with_letter(clean, letter)
    in_db = is_word_in_db(clean, cat_id=cat_id, lang_code=lang) if valid_letter else False
    norm_key = normalize_answer(clean)

    subs = state.setdefault("submissions", {})
    is_first_submission = len(subs) == 0
    was_update = player_id in subs

    subs[player_id] = {
        "player_id": player_id,
        "player_name": player["name"],
        "raw_text": clean,
        "norm_key": norm_key,
        "elapsed_ms": elapsed_ms,
        "order_rank": seq,
        "valid_letter": valid_letter,
        "in_db": in_db,
        "vetoed_by": [],
        "host_override": None,  # None = auto, True = force valid, False = force invalid
    }

    if not was_update:
        sec_str = f"{elapsed_ms / 1000:.1f}s"
        append_event(state, "System", f"⚡ {player['name']} locked in an answer ({sec_str})!")

    participants = state.get("round_participants") or [p["id"] for p in active_players(state)]
    all_submitted = all(pid in subs for pid in participants)

    s = state.get("settings", DEFAULT_SETTINGS)
    stop_mode = s.get("stop_mode", "countdown_on_first")

    if all_submitted:
        finish_round(state, stopped_by=player["name"], reason="All players locked in their answers!")
        return True, "All players locked in! Revealing answers..."

    if call_stop_now and valid_letter and stop_mode == "instant_stop":
        finish_round(state, stopped_by=player["name"], reason=f"🛑 {player['name']} called STOP!")
        return True, "STOP called!"

    if valid_letter and stop_mode == "countdown_on_first" and (is_first_submission or call_stop_now):
        countdown_sec = max(3, int(s.get("stop_countdown", 10) or 10))
        ends_at = state.get("timer_ends_at")
        if ends_at is None or (ends_at - now) > countdown_sec:
            state["timer_ends_at"] = now + countdown_sec
            state["timer_duration"] = countdown_sec
            state["timer_paused_remaining"] = None
            append_event(
                state,
                "System",
                f"⏱️ Hurry! {player['name']} locked in — {countdown_sec}s countdown until STOP!",
            )

    save_game(state["code"], state)
    return True, "Answer locked in!"


def call_stop(state: dict[str, Any], player_id: str, reason: str = "") -> tuple[bool, str]:
    """Handle a player or Host pressing the big red STOP! button."""
    if state.get("phase") != "playing":
        return False, "Round is not currently in progress."

    player = state.get("players", {}).get(player_id)
    if not player:
        return False, "Player not found."

    is_admin = is_player_admin(state, player)
    sub = state.get("submissions", {}).get(player_id)

    if not is_admin:
        if not sub or not sub.get("valid_letter"):
            return (
                False,
                f"You must lock in a valid answer starting with “{state.get('current_letter', '')}” before calling STOP!",
            )

    s = state.get("settings", DEFAULT_SETTINGS)
    stop_mode = s.get("stop_mode", "countdown_on_first")

    if stop_mode == "wait_all_or_timer" and not is_admin:
        return False, "Manual STOP is disabled in 'Wait for All / Timer' mode."

    if stop_mode == "countdown_on_first" and not is_admin:
        now = time.time()
        countdown_sec = max(3, int(s.get("stop_countdown", 10) or 10))
        ends_at = state.get("timer_ends_at")
        if ends_at is None or (ends_at - now) > countdown_sec:
            state["timer_ends_at"] = now + countdown_sec
            state["timer_duration"] = countdown_sec
            state["timer_paused_remaining"] = None
            append_event(state, "System", f"🛑 {player['name']} hit STOP! {countdown_sec}s final countdown!")
            save_game(state["code"], state)
            return True, f"{countdown_sec}s countdown triggered!"

    finish_round(
        state,
        stopped_by=player["name"],
        reason=reason or f"🛑 STOP called by {player['name']}!",
    )
    return True, "Round stopped!"


def _is_submission_effective_valid(state: dict[str, Any], sub: dict[str, Any]) -> bool:
    """Determine if a submission is currently valid (respecting starting letter, host override, and player vetoes)."""
    override = sub.get("host_override")
    if override is True:
        return True
    if override is False:
        return False
    if not sub.get("valid_letter"):
        return False
    vetoes = sub.get("vetoed_by") or []
    active_count = max(1, len(active_players(state)))
    # Majority veto threshold (at least 2 vetoes if 3+ players, or 1 if 1-2 players)
    threshold = max(1, (active_count // 2) + 1) if active_count >= 3 else 1
    return len(vetoes) < threshold


def _compute_round_scores(state: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Calculate points for every participant based on Uniqueness + Submission Speed.
    - Unique valid answers sorted fastest-first:
      * 1st Fastest Unique: 15 pts (10 base + 5 speed bonus)
      * 2nd Fastest Unique: 13 pts (10 base + 3 speed bonus)
      * 3rd Fastest Unique: 11 pts (10 base + 1 speed bonus)
      * 4th+ Unique: 10 pts
    - Duplicate / Clash valid answers (2+ players wrote the same normalized word or fuzzy typo variant):
      * clash_rule == 'none': 10 pts each
      * clash_rule == 'shared': 5 pts each
      * clash_rule == 'first_steals': 10 pts for fastest submitter of that word, 0 pts for slower duplicates
      * clash_rule == 'zero_clash': 0 pts for all duplicates
    """
    subs = state.get("submissions", {})
    participants = state.get("round_participants") or [p["id"] for p in active_players(state)]
    s_settings = state.get("settings", DEFAULT_SETTINGS)
    clash_rule = s_settings.get("clash_rule", "shared")
    fuzzy_clash = bool(s_settings.get("fuzzy_clash", True))

    # Ensure every participant + anyone who submitted is represented
    all_pids: list[str] = []
    for pid in participants:
        if pid not in all_pids:
            all_pids.append(pid)
    for pid in subs:
        if pid not in all_pids:
            all_pids.append(pid)

    valid_subs: list[dict[str, Any]] = []
    for pid in all_pids:
        sub = subs.get(pid)
        if sub and _is_submission_effective_valid(state, sub):
            valid_subs.append(sub)

    # Cluster valid answers (exact matches and close typos merge into collision groups)
    # Respect host_clash_override == False (forced unique isolated from clustering)
    cluster_inputs = []
    forced_unique_pids: set[str] = set()
    for sub in valid_subs:
        if sub.get("host_clash_override") is False:
            forced_unique_pids.add(sub["player_id"])
        else:
            cluster_inputs.append((sub["norm_key"], sub))

    clustered = cluster_answer_keys(cluster_inputs, fuzzy=fuzzy_clash) if cluster_inputs else {}

    sub_to_group: dict[str, list[dict[str, Any]]] = {}
    for _canon_key, grp in clustered.items():
        for s in grp:
            sub_to_group[s["player_id"]] = grp

    for pid in forced_unique_pids:
        sub = subs[pid]
        sub_to_group[pid] = [sub]

    # A submission is considered unique if its cluster group size is 1 AND host_clash_override != True
    unique_subs: list[dict[str, Any]] = [
        s
        for s in valid_subs
        if not (len(sub_to_group.get(s["player_id"], [])) > 1 or s.get("host_clash_override") is True)
    ]
    unique_subs.sort(key=lambda x: (x.get("elapsed_ms", 999999), x.get("order_rank", 999)))

    unique_rank_map: dict[str, int] = {sub["player_id"]: idx + 1 for idx, sub in enumerate(unique_subs)}

    deltas: dict[str, int] = {pid: 0 for pid in all_pids}
    results: list[dict[str, Any]] = []

    # Sort all submissions by speed first, then non-submitters at the bottom
    ordered_pids = sorted(
        all_pids,
        key=lambda pid: (
            0 if pid in subs else 1,
            subs[pid].get("elapsed_ms", 999999) if pid in subs else 999999,
            subs[pid].get("order_rank", 999) if pid in subs else 999,
        ),
    )

    speed_rank_counter = 1
    for pid in ordered_pids:
        p = state.get("players", {}).get(pid, {"id": pid, "name": "Player"})
        sub = subs.get(pid)
        if not sub:
            results.append(
                {
                    "player_id": pid,
                    "player_name": p.get("name", "Player"),
                    "has_submitted": False,
                    "raw_text": "",
                    "elapsed_ms": None,
                    "speed_rank": None,
                    "valid_letter": False,
                    "effective_valid": False,
                    "in_db": False,
                    "status": "missing",
                    "badge": "⌛ No Answer (0 pts)",
                    "points": 0,
                    "vetoed_by": [],
                    "host_override": None,
                    "host_clash_override": None,
                }
            )
            continue

        speed_rank = speed_rank_counter
        speed_rank_counter += 1
        eff_valid = _is_submission_effective_valid(state, sub)
        pts = 0
        status = "invalid"
        badge = "❌ Invalid (0 pts)"

        if not eff_valid:
            if sub.get("host_override") is False or (sub.get("vetoed_by") and sub.get("valid_letter")):
                status = "vetoed"
                badge = "👎 Vetoed (0 pts)"
            else:
                status = "wrong_letter"
                badge = f"❌ Doesn't start with “{state.get('current_letter', '')}” (0 pts)"
        else:
            grp = sub_to_group.get(pid, [sub])
            is_unique = not (len(grp) > 1 or sub.get("host_clash_override") is True)
            if is_unique:
                u_rank = unique_rank_map.get(pid, 99)
                if u_rank == 1:
                    pts = 15
                    status = "unique_1st"
                    badge = "🏆 1st Unique! (+15 pts)"
                elif u_rank == 2:
                    pts = 13
                    status = "unique_2nd"
                    badge = "🥈 2nd Unique! (+13 pts)"
                elif u_rank == 3:
                    pts = 11
                    status = "unique_3rd"
                    badge = "🥉 3rd Unique! (+11 pts)"
                else:
                    pts = 10
                    status = "unique"
                    badge = "✨ Unique (+10 pts)"
            else:
                sorted_grp = sorted(grp, key=lambda x: (x.get("elapsed_ms", 999999), x.get("order_rank", 999)))
                is_fastest_in_clash = sorted_grp[0]["player_id"] == pid
                if clash_rule == "none":
                    pts = 10
                    status = "clash_none"
                    badge = "✨ Valid Answer (+10 pts)"
                elif clash_rule == "first_steals":
                    if is_fastest_in_clash:
                        pts = 10
                        status = "clash_stolen"
                        badge = "⚡ First on Duplicate! (+10 pts)"
                    else:
                        pts = 0
                        status = "clash_beaten"
                        badge = "💥 Duplicate — Too Slow (0 pts)"
                elif clash_rule == "zero_clash":
                    pts = 0
                    status = "clash_zero"
                    badge = "💥 Duplicate Clash (0 pts)"
                else:
                    pts = 5
                    status = "clash_shared"
                    badge = "💥 Duplicate Clash (+5 pts)"

        deltas[pid] = pts
        results.append(
            {
                "player_id": pid,
                "player_name": sub.get("player_name") or p.get("name", "Player"),
                "has_submitted": True,
                "raw_text": sub.get("raw_text", ""),
                "elapsed_ms": sub.get("elapsed_ms"),
                "speed_rank": speed_rank,
                "valid_letter": bool(sub.get("valid_letter")),
                "effective_valid": eff_valid,
                "in_db": bool(sub.get("in_db")),
                "status": status,
                "badge": badge,
                "points": pts,
                "vetoed_by": list(sub.get("vetoed_by") or []),
                "host_override": sub.get("host_override"),
                "host_clash_override": sub.get("host_clash_override"),
            }
        )

    return results, deltas


def _apply_score_deltas(state: dict[str, Any], new_deltas: dict[str, int]) -> None:
    """Idempotently apply or update current round score deltas onto player total scores."""
    prev_applied = state.get("applied_round_deltas") or {}
    players = state.get("players", {})

    all_pids = set(prev_applied.keys()) | set(new_deltas.keys())
    for pid in all_pids:
        diff = int(new_deltas.get(pid, 0)) - int(prev_applied.get(pid, 0))
        if pid in players:
            players[pid]["score"] = max(0, int(players[pid].get("score", 0)) + diff)

    state["applied_round_deltas"] = dict(new_deltas)
    state["score_deltas"] = dict(new_deltas)


def finish_round(
    state: dict[str, Any],
    stopped_by: Optional[str] = None,
    reason: str = "",
) -> dict[str, Any]:
    """Transition from `playing` to `reveal` (or `gameover` if final round), scoring all submissions."""
    if state.get("phase") != "playing":
        return state

    state["stop_called_by"] = stopped_by or "Timer"
    state["stop_reason"] = reason or f"🛑 Round stopped by {stopped_by or 'Timer'}!"
    set_phase_timer(state, 0)

    cat = state.get("current_category") or {}
    letter = state.get("current_letter", "A")
    lang = state.get("language", "en")

    results, deltas = _compute_round_scores(state)
    state["round_results"] = results
    _apply_score_deltas(state, deltas)

    if cat.get("source") == "database":
        state["sample_db_words"] = get_sample_db_words(cat.get("id", ""), letter, lang_code=lang, limit=8)
    else:
        state["sample_db_words"] = []

    winner_entries = [r for r in results if r["points"] > 0]
    if winner_entries:
        top = max(winner_entries, key=lambda r: (r["points"], -(r["elapsed_ms"] or 999999)))
        sec = f"{(top['elapsed_ms'] or 0) / 1000:.1f}s"
        summary = f"🏆 {top['player_name']} led the round with “{top['raw_text']}” ({sec} · +{top['points']} pts)!"
    else:
        summary = f"😅 Nobody scored a valid answer for “{cat.get('title', 'Category')}” ({letter})!"

    state["round_summary"] = summary
    state["phase"] = "reveal"

    history = state.setdefault("rounds_history", [])
    history.append(
        {
            "round_num": state.get("round_num", 1),
            "category": cat.get("title", ""),
            "letter": letter,
            "summary": summary,
            "results": copy.deepcopy(results),
        }
    )

    append_event(state, "System", f"🛑 STOP! {summary}")
    save_game(state["code"], state)
    return state


def toggle_answer_validity(
    state: dict[str, Any],
    actor_id: str,
    target_pid: str,
) -> tuple[bool, str]:
    """
    During `reveal`, allow the Host to directly toggle validity override OR a player to toggle a veto vote,
    then immediately recalculate uniqueness, speed bonuses, and total scores.
    """
    if state.get("phase") != "reveal":
        return False, "Answers can only be reviewed during the Reveal phase."

    actor = state.get("players", {}).get(actor_id)
    sub = state.get("submissions", {}).get(target_pid)
    if not actor or not sub:
        return False, "Submission not found."

    if is_player_admin(state, actor):
        curr_eff = _is_submission_effective_valid(state, sub)
        sub["host_override"] = not curr_eff
        verdict = "✅ Accepted" if sub["host_override"] else "❌ Rejected"
        append_event(
            state,
            "System",
            f"⚖️ Host {actor['name']} marked {sub['player_name']}'s answer “{sub['raw_text']}” as {verdict}.",
        )
    else:
        vetoes = sub.setdefault("vetoed_by", [])
        if actor_id in vetoes:
            vetoes.remove(actor_id)
        else:
            vetoes.append(actor_id)

    results, deltas = _compute_round_scores(state)
    state["round_results"] = results
    _apply_score_deltas(state, deltas)

    if state.get("rounds_history"):
        state["rounds_history"][-1]["results"] = copy.deepcopy(results)

    save_game(state["code"], state)
    return True, "Scores recalculated!"


def toggle_submission_clash(
    state: dict[str, Any],
    actor_id: str,
    target_pid: str,
) -> tuple[bool, str]:
    """During `reveal`, allow the Host to arbitrate whether an answer is forced into a clash or forced unique."""
    if state.get("phase") != "reveal":
        return False, "Collisions can only be arbitrated during the Reveal phase."

    actor = state.get("players", {}).get(actor_id)
    sub = state.get("submissions", {}).get(target_pid)
    if not actor or not sub:
        return False, "Submission not found."

    if not is_player_admin(state, actor):
        return False, "Only the Host can arbitrate collisions."

    # Determine current clash state from round_results
    curr_result = next((r for r in state.get("round_results", []) if r["player_id"] == target_pid), None)
    was_clash = bool(curr_result and "clash" in curr_result.get("status", ""))

    if sub.get("host_clash_override") is not None:
        sub["host_clash_override"] = not sub["host_clash_override"]
    else:
        sub["host_clash_override"] = not was_clash

    verdict = "💥 Clash" if sub["host_clash_override"] else "✨ Unique"
    append_event(
        state,
        "System",
        f"⚖️ Host {actor['name']} arbitrated {sub['player_name']}'s answer “{sub['raw_text']}” as {verdict}.",
    )

    results, deltas = _compute_round_scores(state)
    state["round_results"] = results
    _apply_score_deltas(state, deltas)

    if state.get("rounds_history"):
        state["rounds_history"][-1]["results"] = copy.deepcopy(results)

    save_game(state["code"], state)
    return True, f"Submission marked as {verdict}!"


def end_match(state: dict[str, Any], by_name: str = "Host") -> dict[str, Any]:
    if state.get("phase") == "playing":
        finish_round(state, stopped_by=by_name, reason=f"Match ended by {by_name}")
    state["phase"] = "gameover"
    state["status"] = "finished"
    set_phase_timer(state, 0)
    sync_room_db_status(state["code"], "finished")
    append_event(state, "System", f"🏁 Match ended by {by_name}!")
    save_game(state["code"], state)
    return state


def play_again(state: dict[str, Any]) -> dict[str, Any]:
    for p in state.get("players", {}).values():
        p["score"] = 0
    state["phase"] = "lobby"
    state["status"] = "open"
    state["started"] = False
    state["round_num"] = 0
    state["current_category"] = None
    state["current_letter"] = ""
    state["submissions"] = {}
    state["round_results"] = []
    state["score_deltas"] = {}
    state["applied_round_deltas"] = {}
    state["sample_db_words"] = []
    state["round_summary"] = ""
    state["rounds_history"] = []
    set_phase_timer(state, 0)
    sync_room_db_status(state["code"], "open")
    append_event(state, "System", "🔄 Match reset back to Lobby!")
    save_game(state["code"], state)
    return state


def get_sanitized_player_view(state: dict[str, Any], viewer_id: Optional[str]) -> dict[str, Any]:
    """
    Build a zero-spoiler personalized state payload for `viewer_id`.
    During `playing`, other players' answer text is strictly omitted so no one can inspect JSON to copy answers.
    """
    phase = state.get("phase", "lobby")
    viewer = state.get("players", {}).get(viewer_id) if viewer_id else None
    is_admin = is_player_admin(state, viewer)
    subs = state.get("submissions", {})

    players_list = []
    for pid, p in sorted(
        state.get("players", {}).items(),
        key=lambda item: (-int(item[1].get("score", 0)), item[1].get("name", "").lower()),
    ):
        sub = subs.get(pid)
        players_list.append(
            {
                "id": pid,
                "name": p.get("name", "Player"),
                "color": p.get("color") or "#3b82f6",
                "initials": p.get("initials") or get_player_initials(p.get("name")),
                "score": int(p.get("score", 0)),
                "is_admin": bool(p.get("is_admin") or pid == state.get("creator_id")),
                "is_spectator": bool(p.get("is_spectator")),
                "connected": bool(p.get("connected")),
                "has_submitted": bool(sub),
                "elapsed_ms": sub.get("elapsed_ms") if sub else None,
            }
        )

    # Build live race tracker (safe during `playing` — no raw_text leaked!)
    live_race = []
    ordered_subs = sorted(subs.values(), key=lambda s: (s.get("elapsed_ms", 999999), s.get("order_rank", 999)))
    for idx, s in enumerate(ordered_subs):
        live_race.append(
            {
                "player_id": s["player_id"],
                "player_name": s["player_name"],
                "speed_rank": idx + 1,
                "elapsed_ms": s.get("elapsed_ms"),
                "valid_letter": bool(s.get("valid_letter")),
            }
        )

    my_sub = subs.get(viewer_id) if viewer_id else None
    my_submission = (
        {
            "raw_text": my_sub.get("raw_text", ""),
            "elapsed_ms": my_sub.get("elapsed_ms"),
            "valid_letter": bool(my_sub.get("valid_letter")),
            "in_db": bool(my_sub.get("in_db")),
        }
        if my_sub
        else None
    )

    now = time.time()
    timer_ends_at = state.get("timer_ends_at")
    remaining = max(0, int(round(timer_ends_at - now))) if timer_ends_at else None

    return {
        "type": "state_sync",
        "version": VERSION_COUNTER,
        "code": state.get("code"),
        "title": state.get("title"),
        "language": state.get("language", "en"),
        "language_support": get_game_language_support("stop", state.get("language", "en")),
        "status": state.get("status", "open"),
        "phase": phase,
        "started": bool(state.get("started")),
        "round_num": int(state.get("round_num", 0)),
        "settings": state.get("settings", DEFAULT_SETTINGS),
        "me": {
            "id": viewer["id"] if viewer else None,
            "name": viewer["name"] if viewer else None,
            "is_admin": is_admin,
            "is_spectator": bool(viewer.get("is_spectator")) if viewer else False,
            "score": int(viewer.get("score", 0)) if viewer else 0,
        },
        "players": players_list,
        "current_category": state.get("current_category"),
        "current_letter": state.get("current_letter", ""),
        "custom_categories": state.get("custom_categories", []),
        "my_submission": my_submission,
        "live_race": live_race,
        "submitted_count": len(subs),
        "participant_count": len(state.get("round_participants") or [p for p in players_list if not p["is_spectator"]]),
        "stop_called_by": state.get("stop_called_by"),
        "stop_reason": state.get("stop_reason", ""),
        "round_results": state.get("round_results", []) if phase in ("reveal", "gameover") else [],
        "score_deltas": state.get("score_deltas", {}) if phase in ("reveal", "gameover") else {},
        "sample_db_words": state.get("sample_db_words", []) if phase in ("reveal", "gameover") else [],
        "round_summary": state.get("round_summary", ""),
        "rounds_history": state.get("rounds_history", []),
        "chat_log": state.get("chat_log", [])[-60:],
        "timer": {
            "duration": state.get("timer_duration", 0),
            "ends_at": timer_ends_at,
            "remaining": remaining,
            "paused_remaining": state.get("timer_paused_remaining"),
        },
        "server_time": now,
        "round_countdown_until": state.get("round_countdown_until"),
        "round_started_at": state.get("round_started_at"),
    }

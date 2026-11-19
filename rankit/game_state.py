"""Redis-backed game state engine for 'Rank It!' (ito cooperative party game).

Mechanics:
- Players are dealt secret numbered cards from 1 to 100 without duplicates.
- The team is presented with a theme/spectrum from 1 (lowest) to 100 (highest).
- Players communicate clues/hints without saying numerical values.
- Players play cards into the central Timeline when they believe their number is next.
- Ascending plays succeed; if a played number is lower than a previous one, it clashes and loses a life!
- The goal is to survive and clear all levels together!
"""

import copy
import json
import os
import random
import time
import uuid
from typing import Any, Optional

import redis

from gamerooms.language_support import normalize_language_code
from gamerooms.player_colors import (
    assign_distinct_player_color,
    get_player_initials,
    is_valid_color_hex,
)
from website.version import VERSION_COUNTER

from .prompts import get_random_prompt

_redis = None
_fallback_store: dict[str, str] = {}

DEFAULT_SETTINGS: dict[str, Any] = {
    "cards_per_player": "level_based",  # "level_based" (1 card at lvl 1, 2 at lvl 2, etc.) or "1", "2", "3"
    "starting_lives": 3,
    "target_levels": 3,  # 0 = endless / until defeat
    "pack": "mix",  # "mix", "classic", "everyday", "superpowers", "food", "scary", "deep", "nsfw"
    "allow_nsfw": False,  # Opt-in toggle for adult / spicy 18+ cards
    "round_timer": 0,  # 0 = untimed discussion, or 60, 90, 120s
}


def get_redis_client():
    global _redis
    if _redis is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            r = redis.from_url(redis_url, socket_connect_timeout=1.5, socket_timeout=1.5)
            r.ping()
            _redis = r
        except Exception:
            _redis = False
    return _redis if _redis is not False else None


def get_game(code: str) -> dict[str, Any]:
    code = code.upper()
    r = get_redis_client()
    raw = None
    if r:
        try:
            raw = r.get(f"rankit:{code}")
        except Exception:
            raw = None
    if raw is None:
        raw = _fallback_store.get(f"rankit:{code}")

    if raw:
        try:
            data = json.loads(raw if isinstance(raw, str) else raw.decode())
            data.setdefault("version_counter", VERSION_COUNTER)
            return data
        except Exception:
            pass
    return create_game(code)


def save_game(code: str, state: dict[str, Any]) -> None:
    code = code.upper()
    state["updated_at"] = time.time()
    state["version_counter"] = VERSION_COUNTER
    raw = json.dumps(state)
    r = get_redis_client()
    if r:
        try:
            r.set(f"rankit:{code}", raw, ex=86400 * 3)
        except Exception:
            pass
    _fallback_store[f"rankit:{code}"] = raw


def create_game(code: str, title: str = "", password: str = "", language: str = "en") -> dict[str, Any]:
    code = code.upper()
    norm_lang = normalize_language_code(language)
    state: dict[str, Any] = {
        "code": code,
        "title": title or f"Rank It! Room {code}",
        "password": password,
        "language": norm_lang,
        "creator": None,
        "creator_id": None,
        "phase": "lobby",  # "lobby", "staging", "playing", "level_success", "gameover"
        "level": 1,
        "lives": 3,
        "max_lives": 3,
        "highest_played_number": 0,
        "settings": copy.deepcopy(DEFAULT_SETTINGS),
        "players": {},
        "next_player_seq": 1,
        "current_prompt": None,
        "used_prompt_ids": [],
        "timeline": [],  # Chronological order of played cards
        "level_history": [],  # Archives of past levels
        "activity_log": [],
        "round_countdown_until": None,
        "round_started_at": None,
        "last_advanced_from_level": None,
        "last_advance_timestamp": 0.0,
        "version_counter": VERSION_COUNTER,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    save_game(code, state)
    return state


def append_event(state: dict[str, Any], author: str, text: str) -> None:
    events = state.setdefault("activity_log", [])
    events.append(
        {
            "id": uuid.uuid4().hex[:8],
            "author": author,
            "text": text,
            "timestamp": time.time(),
        }
    )
    if len(events) > 60:
        state["activity_log"] = events[-60:]


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
    """Add or reconnect a player; assigns distinct badge color and initials."""
    existing = find_player_by_token(state, token)
    if existing:
        existing["connected"] = True
        if channel_name:
            existing["channel_name"] = channel_name
        if is_admin:
            existing["is_admin"] = True
        # Ensure color and initials are set
        if not existing.get("color"):
            existing["color"] = assign_distinct_player_color(state.get("players", {}))
        if not existing.get("initials"):
            existing["initials"] = get_player_initials(existing.get("name"))
        save_game(state["code"], state)
        return state, existing, False

    by_name = find_player_by_name(state, name)
    if by_name:
        is_host_reconnect = is_admin and (by_name.get("is_admin") or by_name.get("id") == state.get("creator_id"))
        if is_host_reconnect or not by_name.get("connected", False) or state.get("phase") in ("lobby", "waiting", None):
            by_name["connected"] = True
            if channel_name:
                by_name["channel_name"] = channel_name
            if is_admin:
                by_name["is_admin"] = True
            if not by_name.get("color"):
                by_name["color"] = assign_distinct_player_color(state.get("players", {}))
            if not by_name.get("initials"):
                by_name["initials"] = get_player_initials(by_name.get("name"))
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
        "token": token or uuid.uuid4().hex[:20],
        "color": assigned_color,
        "initials": get_player_initials(clean_name),
        "is_admin": grant_admin,
        "is_spectator": False,
        "connected": True,
        "channel_name": channel_name or None,
        "hand": [],  # Cards dealt for current level
    }
    state.setdefault("players", {})[pid] = player

    if grant_admin and not state.get("creator_id"):
        state["creator_id"] = pid
        state["creator"] = clean_name

    append_event(state, "System", f"👋 {clean_name} joined the room.")
    save_game(state["code"], state)
    return state, player, True


def is_player_admin(state: dict[str, Any], player: Optional[dict[str, Any]]) -> bool:
    if not player:
        return False
    return bool(player.get("is_admin") or player.get("id") == state.get("creator_id"))


def update_settings(state: dict[str, Any], new_settings: dict[str, Any]) -> None:
    settings = state.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))
    for k in (
        "cards_per_player",
        "starting_lives",
        "target_levels",
        "pack",
        "allow_nsfw",
        "round_timer",
    ):
        if k in new_settings:
            settings[k] = new_settings[k]

    # If starting lives changed in lobby, sync state lives
    if state.get("phase") == "lobby":
        try:
            lives = int(settings.get("starting_lives", 3))
            state["lives"] = max(1, min(lives, 5))
            state["max_lives"] = state["lives"]
        except Exception:
            pass

    save_game(state["code"], state)


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

    # Check permission: self or admin
    if target_player_id != requester_player_id and not requested_by_admin:
        return False

    player["color"] = new_color.strip()
    save_game(state["code"], state)
    return True


def _compute_cards_for_player(state: dict[str, Any]) -> int:
    cfg = state.get("settings", {}).get("cards_per_player", "level_based")
    if cfg == "level_based":
        return max(1, min(state.get("level", 1), 5))
    try:
        return max(1, min(int(cfg), 4))
    except Exception:
        return 1


def start_level(state: dict[str, Any], from_level: Optional[int] = None) -> bool:
    """Deal drafted cards and schedule a synchronized 4-second round countdown."""
    now = time.time()
    cur_level = state.get("level", 1)

    # Idempotency check: drop stale clicks from previously advanced levels
    if from_level is not None and from_level < cur_level:
        return False

    # Debounce spam clicks within 2.0s for the exact same level
    if state.get("last_advanced_from_level") == cur_level and (now - state.get("last_advance_timestamp", 0.0)) < 2.0:
        return False

    state["last_advanced_from_level"] = cur_level
    state["last_advance_timestamp"] = now

    # Reset level runtime
    state["highest_played_number"] = 0
    state["timeline"] = []

    # Filter active, non-spectator players
    active_players = [
        p for p in state.get("players", {}).values() if p.get("connected", True) and not p.get("is_spectator", False)
    ]
    if not active_players:
        return False

    cards_per_player = _compute_cards_for_player(state)
    total_cards = len(active_players) * cards_per_player
    total_cards = min(total_cards, 100)

    # Draft unique random numbers without replacement from 1 to 100
    drafted_numbers = random.sample(range(1, 101), total_cards)
    random.shuffle(drafted_numbers)

    # Distribute cards to players
    for p in state.get("players", {}).values():
        p["hand"] = []

    for idx, p in enumerate(active_players):
        slice_start = idx * cards_per_player
        slice_end = slice_start + cards_per_player
        p_numbers = drafted_numbers[slice_start:slice_end]
        # Sort internally for smooth player readability
        p_numbers.sort()

        p["hand"] = [
            {
                "card_id": f"c_{uuid.uuid4().hex[:8]}",
                "number": num,
                "clue": "",
                "played": False,
            }
            for num in p_numbers
        ]

    # Pick prompt for this level
    settings = state.get("settings", {})
    pack = settings.get("pack", "mix")
    allow_nsfw = settings.get("allow_nsfw", False)
    used_ids = state.get("used_prompt_ids", [])
    prompt = get_random_prompt(
        pack=pack,
        allow_nsfw=allow_nsfw,
        used_ids=used_ids,
        language=state.get("language", "en"),
    )
    state["current_prompt"] = prompt
    state.setdefault("used_prompt_ids", []).append(prompt["id"])

    # Scheduled Synchronized Countdown: 4 seconds staging
    state["round_countdown_until"] = now + 4.0
    state["round_started_at"] = now + 4.0
    state["phase"] = "playing"

    append_event(
        state,
        "System",
        f"🚀 Level {cur_level} started! Theme: '{prompt['title']}'. (Each player has {cards_per_player} cards).",
    )
    save_game(state["code"], state)
    return True


def set_card_clue(state: dict[str, Any], player_id: str, card_id: str, clue_text: str) -> bool:
    """Player sets or updates an optional hint/clue for their secret card."""
    player = state.get("players", {}).get(player_id)
    if not player:
        return False

    clean_clue = " ".join((clue_text or "").split()).strip()[:100]
    for c in player.get("hand", []):
        if c.get("card_id") == card_id:
            c["clue"] = clean_clue
            save_game(state["code"], state)
            return True
    return False


def play_card(state: dict[str, Any], player_id: str, card_id: str) -> tuple[bool, str]:
    """Play a card to the central timeline and validate ascending order."""
    if state.get("phase") != "playing":
        return False, "Not currently in playing phase."

    player = state.get("players", {}).get(player_id)
    if not player:
        return False, "Player not found."

    target_card = None
    for c in player.get("hand", []):
        if c.get("card_id") == card_id and not c.get("played", False):
            target_card = c
            break

    if not target_card:
        return False, "Card not found or already played."

    # Mark as played in hand
    target_card["played"] = True
    number = target_card["number"]
    clue = target_card.get("clue", "")
    prev_highest = state.get("highest_played_number", 0)

    is_clash = number < prev_highest
    timeline_entry = {
        "card_id": card_id,
        "number": number,
        "player_id": player["id"],
        "player_name": player["name"],
        "player_color": player.get("color", "#3b82f6"),
        "player_initials": player.get("initials") or get_player_initials(player["name"]),
        "clue": clue,
        "is_clash": is_clash,
        "prev_highest": prev_highest,
        "played_at": time.time(),
    }
    state.setdefault("timeline", []).append(timeline_entry)

    if is_clash:
        state["lives"] = max(0, state.get("lives", 1) - 1)
        remaining_lives = state["lives"]
        append_event(
            state,
            "System",
            f"💥 CLASH! {player['name']} played #{number}, which is lower than #{prev_highest}! Lost 1 life (❤️ {remaining_lives} left).",
        )
        if remaining_lives <= 0:
            state["phase"] = "gameover"
            append_event(state, "System", "💀 Game Over! The group ran out of lives.")
            save_game(state["code"], state)
            return True, "Clash occurred! Game Over."
    else:
        state["highest_played_number"] = number
        append_event(
            state,
            "System",
            f"✅ {player['name']} played #{number} {f'("{clue}")' if clue else ''}. Order preserved!",
        )

    # Check if all cards for this level have been played
    all_cards_played = True
    for p in state.get("players", {}).values():
        if not p.get("is_spectator", False):
            for c in p.get("hand", []):
                if not c.get("played", False):
                    all_cards_played = False
                    break
        if not all_cards_played:
            break

    if all_cards_played and state.get("lives", 0) > 0:
        # Level cleared!
        cur_level = state.get("level", 1)
        target = state.get("settings", {}).get("target_levels", 3)
        state["level_history"].append(
            {
                "level": cur_level,
                "prompt": state.get("current_prompt"),
                "timeline": copy.deepcopy(state.get("timeline", [])),
                "lives_left": state["lives"],
            }
        )

        if target and cur_level >= target:
            state["phase"] = "victory"
            append_event(
                state,
                "System",
                f"🏆 GRAND VICTORY! The team cleared all {target} levels with {state['lives']} lives remaining!",
            )
        else:
            state["phase"] = "level_success"
            state["level"] = cur_level + 1
            append_event(
                state,
                "System",
                f"🎉 LEVEL {cur_level} CLEARED! Ready for Level {cur_level + 1}!",
            )

    save_game(state["code"], state)
    return True, "Card played successfully."


def play_again(state: dict[str, Any]) -> None:
    """Reset match back to Level 1 in the lobby."""
    state["phase"] = "lobby"
    state["level"] = 1
    starting_lives = state.get("settings", {}).get("starting_lives", 3)
    state["lives"] = starting_lives
    state["max_lives"] = starting_lives
    state["highest_played_number"] = 0
    state["timeline"] = []
    state["level_history"] = []
    state["current_prompt"] = None
    state["round_countdown_until"] = None
    state["round_started_at"] = None
    state["last_advanced_from_level"] = None
    for p in state.get("players", {}).values():
        p["hand"] = []
    append_event(state, "System", "🔄 Match reset. Host returned room to lobby.")
    save_game(state["code"], state)


def kick_player(state: dict[str, Any], player_id: str) -> None:
    if player_id in state.get("players", {}):
        pname = state["players"][player_id].get("name", "Player")
        del state["players"][player_id]
        append_event(state, "System", f"👢 {pname} was removed from the room.")
        save_game(state["code"], state)


def transfer_host(state: dict[str, Any], new_host_id: str) -> None:
    if new_host_id in state.get("players", {}):
        for pid, p in state["players"].items():
            p["is_admin"] = pid == new_host_id
        state["creator_id"] = new_host_id
        state["creator"] = state["players"][new_host_id]["name"]
        append_event(state, "System", f"👑 Room host transferred to {state['creator']}.")
        save_game(state["code"], state)


def get_sanitized_player_view(state: dict[str, Any], viewer_id: Optional[str] = None) -> dict[str, Any]:
    """Return player state, masking other players' unplayed cards for zero spoilers!"""
    view = copy.deepcopy(state)
    view["server_time"] = time.time()

    viewer = None
    sanitized_players = []

    # Phase determines spoiler rules: in 'gameover' or 'victory', all numbers reveal!
    reveal_all = view.get("phase") in ("gameover", "victory")

    for pid, p in view.get("players", {}).items():
        is_viewer = pid == viewer_id
        sanitized_hand = []

        for card in p.get("hand", []):
            card_copy = copy.deepcopy(card)
            # If not played, and not viewer's own hand, and not gameover reveal: hide number!
            if not card.get("played", False) and not is_viewer and not reveal_all:
                card_copy["number"] = None
            sanitized_hand.append(card_copy)

        p_copy = {
            "id": p["id"],
            "name": p["name"],
            "color": p.get("color", "#3b82f6"),
            "initials": p.get("initials") or get_player_initials(p["name"]),
            "is_admin": bool(p.get("is_admin")),
            "is_spectator": bool(p.get("is_spectator")),
            "connected": bool(p.get("connected", True)),
            "cards_count": len([c for c in p.get("hand", []) if not c.get("played", False)]),
            "hand": sanitized_hand,
        }

        if is_viewer:
            viewer = p_copy
        sanitized_players.append(p_copy)

    view["players"] = sanitized_players
    view["viewer"] = viewer
    return view

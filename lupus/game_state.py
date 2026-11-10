"""Lupus game state management with Redis backend and robust rule engine."""

import json
import math
import os
import random
import re
import time
import uuid
from typing import Any, Optional

import redis

from website.version import get_version_info

from .roles import (
    FACTION_TOWN,
    FACTION_WOLVES,
    ROLE_REGISTRY,
    get_all_roles_catalogue,
    get_role_info,
)

_redis_client = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


def _key(code: str) -> str:
    return f"lupus:game:{code.upper()}"


def get_game(code: str) -> Optional[dict[str, Any]]:
    r = get_redis_client()
    data = r.get(_key(code))
    if data:
        return json.loads(data)
    return None


def save_game(code: str, state: dict[str, Any]) -> None:
    r = get_redis_client()
    r.set(_key(code), json.dumps(state), ex=86400)  # 24h expiration


def delete_game(code: str) -> None:
    r = get_redis_client()
    r.delete(_key(code))


def is_evil_faction_or_threat(player: Optional[dict[str, Any]]) -> bool:
    """Check if player belongs to an evil faction or hostile solo threat.

    Evil: Werewolves, Mafia, Serial Killer, Saboteur Wolf, Disgruntled Ghost.
    Good / Innocent: Citizens/Villagers, Doctor, Detective, Bodyguard, Angel, Mayor, Witch,
                     Watson, Hacker, Traveler, Ghost, and Jester.
    """
    if not player:
        return False
    faction = player.get("faction")
    role = player.get("role")
    if faction == FACTION_WOLVES:
        return True
    if role in ("serial_killer", "saboteur_wolf", "disgruntled_ghost"):
        return True
    return False


def is_evil_for_detective(player: Optional[dict[str, Any]], is_framed: bool = False) -> bool:
    """Check inspection alignment for Detective. Alpha wolf appears Good."""
    if not player:
        return False
    if is_framed:
        return True
    if player.get("role") == "alpha_wolf":
        return False
    return is_evil_faction_or_threat(player)


def get_voter_weight(state: dict[str, Any], voter_id: str) -> int:
    """Return vote weight for voter. Public Mayor has double vote (weight = 2)."""
    if not voter_id or str(voter_id).startswith("tally_") or str(voter_id).startswith("gm_vote_"):
        return 1
    player = state.get("players", {}).get(voter_id)
    if player and player.get("role") == "mayor":
        is_public = (
            player.get("is_public_mayor", False)
            or state.get("settings", {}).get("mayor_type") == "public"
            or state.get("settings", {}).get("public_mayor", False)
        )
        if is_public:
            return 2
    return 1


def create_initial_state(
    code: str,
    title: str,
    password: str = "",
    gm_name: str = "Game Master",
    theme: str = "werewolf",
    settings: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    gm_token = uuid.uuid4().hex
    default_settings = {
        "discussion_timer": 300,  # 5 min
        "defense_timer": 30,  # 30 sec
        "limbo_enabled": True,  # Limbo mechanic
        "staggering_doctor": True,  # Cannot save same player 2 nights in a row
        "doctor_saves_from_sniper": False,  # Doctor save does not stop sniper
        "sniper_bullet_type": "danger",  # "danger", "silver", "mix"
        "sniper_danger_bullets": 1,
        "sniper_silver_bullets": 0,
        "reveal_roles_on_death": 0,  # 0: None, 1: Alignment, 2: Faction, 3: Full Role
        "voting_system": "two_stage_50pct",  # "two_stage_50pct", "two_stage_top_n", "simple_plurality"
        "nomination_threshold_pct": 50,  # 50% of living players needed for nomination
        "mayor_type": "public",  # "public" (cannot be lynched, 2x vote) or "hidden" (secret, 1x vote)
        "public_mayor": True,  # Kept in sync with mayor_type
        "public_heartbreak_cause": False,  # If true, lover heartbreak cause announced; if false, concealed as "found dead"
    }
    if settings:
        default_settings.update(settings)
    # Ensure mayor_type and public_mayor remain synchronized
    if "mayor_type" in default_settings:
        default_settings["public_mayor"] = (default_settings["mayor_type"] == "public")
    elif "public_mayor" in default_settings:
        default_settings["mayor_type"] = "public" if default_settings["public_mayor"] else "hidden"

    state: dict[str, Any] = {
        "code": code.upper(),
        "title": title or f"Lupus Room {code.upper()}",
        "password": password,
        "gm_token": gm_token,
        "gm_name": gm_name,
        "theme": "mafia" if theme == "mafia" else "werewolf",
        "phase": "lobby",  # lobby, night, day_discussion, day_defense, day_voting, gameover
        "round_number": 0,
        "settings": default_settings,
        "timer": {
            "duration": default_settings["discussion_timer"],
            "ends_at": None,
            "paused": True,
            "remaining": default_settings["discussion_timer"],
            "label": "Discussion",
        },
        "deck": [],
        "players": {},
        "player_order": [],
        "night_actions": {},
        "night_stage_index": 0,
        "is_night_zero": False,
        "revealed_inspect": None,
        "player_points": {},
        "death_angel_used": False,
        "voting": {
            "stage": "none",
            "system": default_settings.get("voting_system", "two_stage_50pct"),
            "nomination_votes": {},
            "nominated_player_ids": [],
            "final_votes": {},
            "tie_count": 0,
            "revote_candidates": [],
            "defense_player_id": None,
            "eliminated_player_id": None,
            "elimination_result": None,
            "ballot_locked": False,
        },
        "witch_used_revive": False,
        "witch_used_kill": False,
        "mayor_used_veto": False,
        "mayor_vetoed_ids": [],
        "last_silenced_id": None,
        "saboteur_used": False,
        "hacker_scanned_ids": [],
        "hacker_result": None,
        "day1_no_voting": False,
        "ghost_messages": [],
        "approved_ghost_messages": [],
        "news_bulletins": [],
        "approved_news_bulletins": [],
        "last_lynched_id": None,
        "defense_player_id": None,
        "events_log": [],
        "night_report": [],
        "winner": None,
        "pending_gameover": None,
        "pending_gameover_dismissed": False,
    }
    save_game(code, state)
    return state


def add_player(state: dict[str, Any], name: str, is_offline: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """Register a new player in the room. Generates unique player ID and private reconnect token."""
    player_id = uuid.uuid4().hex[:12]
    token = uuid.uuid4().hex

    player = {
        "id": player_id,
        "name": name.strip(),
        "token": token,
        "role": None,
        "faction": None,
        "status": "alive",  # "alive", "limbo", "dead"
        "used_limbo": False,
        "is_silenced": False,
        "is_suppressed": False,
        "haunted_by": None,
        "is_traveler": False,
        "is_ghost": False,
        "is_successor": False,
        "preassigned_role": None,
        "last_news_post_round": None,
        "used_dead_news_bulletin": False,
        "pending_heartbreak": False,
        "pending_heartbreak_from_id": None,
        "pending_heartbreak_lover_name": None,
        "is_offline": is_offline,
        "connected": True,
        "channel_name": None,
        "lover_id": None,
        "lover_type": None,  # "innocent" or "obsessive"
        "last_guarded_id": None,
        "is_public_mayor": False,
        "sniper_danger_bullets": 1,
        "sniper_silver_bullets": 1 if state.get("settings", {}).get("sniper_bullet_type") == "mix" else 0,
        "sniper_nights_held": 0,
    }
    state["players"][player_id] = player
    if "player_order" not in state or not isinstance(state["player_order"], list):
        state["player_order"] = list(state["players"].keys())
    elif player_id not in state["player_order"]:
        state["player_order"].append(player_id)
    log_event(state, f"{name} entered the room.")
    save_game(state["code"], state)
    return state, player


def remove_player(state: dict[str, Any], player_id: str) -> dict[str, Any]:
    if player_id in state["players"]:
        name = state["players"][player_id]["name"]
        del state["players"][player_id]
        if "player_order" in state and player_id in state["player_order"]:
            state["player_order"].remove(player_id)
        log_event(state, f"{name} left the room.")
        save_game(state["code"], state)
    return state


DEMO_PLAYERS: list[tuple[str, str]] = [
    ("Werewolf", "werewolf"),
    ("Alpha Wolf", "alpha_wolf"),
    ("Detective", "detective"),
    ("Watson", "watson"),
    ("Doctor", "doctor"),
    ("Angel", "angel"),
    ("Vigilante", "sniper"),
    ("Mayor", "mayor"),
    ("Silencer", "silencer"),
    ("Citizen", "villager"),
]

DEMO_PLAYER_NAMES: list[str] = [name for name, _ in DEMO_PLAYERS]

ROLE_NAME_KEYWORDS: list[tuple[str, list[str]]] = [
    # Multi-word or specific evil roles first
    ("alpha_wolf", ["alpha wolf", "alpha_wolf", "lobo alpha", "alpha"]),
    ("saboteur_wolf", ["saboteur wolf", "saboteur", "sabotador", "sabotage"]),
    ("disgruntled_ghost", ["disgruntled ghost", "disgruntled", "bad ghost"]),
    ("serial_killer", ["serial killer", "serial_killer", "serial", "killer", "sk", "assassino"]),
    ("silencer", ["silencer", "silenciador", "muto"]),
    ("werewolf", ["werewolf", "werewolves", "wolf", "lobo", "lupus"]),
    # Specialized good roles
    ("detective", ["detective", "seer", "sherlock", "investigador", "vidente", "cop"]),
    ("watson", ["watson", "helper", "sidekick", "adjunto"]),
    ("doctor", ["doctor", "doc", "medic", "nurse", "healer", "medico"]),
    ("bodyguard", ["bodyguard", "guard", "protector", "guarda"]),
    ("sniper", ["sniper", "vigilante", "hunter", "cacador", "gunner"]),
    ("angel", ["angel", "guardian angel", "anjo"]),
    ("mayor", ["mayor", "prefeito", "burgomestre", "presidente"]),
    ("witch", ["witch", "sorceress", "bruxa", "maga"]),
    ("hacker", ["hacker"]),
    ("traveler", ["traveler", "viajante"]),
    ("successor", ["successor", "understudy", "inheritor", "herdeiro"]),
    ("ghost", ["ghost", "town ghost", "fantasma", "spirit"]),
    ("cupid", ["cupid", "cupido", "obsessive lover"]),
    ("lover", ["lover", "lovers", "innocent lover", "namorado"]),
    ("jester", ["jester", "fool", "clown", "palhaco", "bobo"]),
    ("villager", ["villager", "citizen", "aldeao", "cidadao", "townie", "peasant"]),
]


def match_role_from_name(name: str) -> Optional[str]:
    """Match a player's name against known role keywords.

    Normalizes by stripping non-alphanumeric chars and numbers.
    """
    if not name:
        return None
    clean = re.sub(r"[^a-zA-Z0-9_\s]", " ", name.lower()).strip()
    clean = re.sub(r"\b\d+\b", " ", clean).strip()
    clean = re.sub(r"\s+", " ", clean)

    for role_id, keywords in ROLE_NAME_KEYWORDS:
        for kw in keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, clean):
                return role_id
    return None


def auto_assign_roles_from_names(state: dict[str, Any]) -> int:
    """Scan all joined player names and pre-assign roles that match their names.

    Returns the count of players whose roles were successfully matched and assigned.
    """
    matched = 0
    deck = list(state.get("deck", []))
    for p in state.get("players", {}).values():
        role_id = match_role_from_name(p.get("name", ""))
        if role_id and role_id in ROLE_REGISTRY and ROLE_REGISTRY[role_id].get("enabled", True):
            p["preassigned_role"] = role_id
            if state.get("phase") == "lobby":
                p["role"] = role_id
                p["faction"] = ROLE_REGISTRY[role_id]["faction"]
            matched += 1
            if role_id not in deck:
                if "villager" in deck:
                    deck.remove("villager")
                deck.append(role_id)

    state["deck"] = deck
    if matched > 0:
        log_event(state, f"✨ Auto-assigned {matched} roles based on player names.")
        save_game(state["code"], state)
    return matched


def set_preassigned_role(state: dict[str, Any], player_id: str, role_id: Optional[str]) -> tuple[bool, str]:
    """Pre-assign or clear a role for a player in the pre-game lobby."""
    if player_id not in state.get("players", {}):
        return False, "Player not found."

    player = state["players"][player_id]
    if not role_id or role_id in ("random", "clear", "none"):
        player["preassigned_role"] = None
        if state.get("phase") == "lobby":
            player["role"] = None
            player["faction"] = None
        log_event(state, f"🎲 Cleared pre-assigned role for {player['name']} (will be dealt randomly).")
        save_game(state["code"], state)
        return True, f"Role cleared for {player['name']}."

    role_info = ROLE_REGISTRY.get(role_id)
    if not role_info:
        return False, f"Invalid role '{role_id}'."

    player["preassigned_role"] = role_id
    if state.get("phase") == "lobby":
        player["role"] = role_id
        player["faction"] = role_info["faction"]
        if role_id == "mayor":
            player["is_public_mayor"] = (
                state.get("settings", {}).get("mayor_type", "public") == "public"
                or state.get("settings", {}).get("public_mayor", False)
            )
        else:
            player["is_public_mayor"] = False

    # Ensure pre-assigned role is represented in state['deck']
    deck = list(state.get("deck", []))
    if role_id not in deck:
        if "villager" in deck:
            deck.remove("villager")
        deck.append(role_id)
        state["deck"] = deck

    role_title = role_info.get("title", role_id.title())
    log_event(state, f"🎯 Game Master pre-assigned role '{role_title}' to {player['name']}.")
    save_game(state["code"], state)
    return True, f"Pre-assigned {role_title} to {player['name']}."


def should_autofill_demo(password: str, gm_name: str) -> bool:
    """Check if room credentials match the demo autofill trigger (password 'test' & narrator 'marco')."""
    pw = (password or "").strip().lower()
    gm = (gm_name or "").strip().lower()
    return (pw == "test" or pw.startswith("test") or pw == "demo") and "marco" in gm


def setup_demo_room(state: dict[str, Any]) -> dict[str, Any]:
    """Populate room with 10 demo test players named after their roles and pre-assign their roles."""
    existing_names = {p["name"].lower() for p in state.get("players", {}).values()}
    for name, role_id in DEMO_PLAYERS:
        if name.lower() not in existing_names:
            state, player = add_player(state, name, is_offline=False)
            player["preassigned_role"] = role_id
            player["role"] = role_id
            player["faction"] = ROLE_REGISTRY.get(role_id, {}).get("faction", FACTION_TOWN)

    state["deck"] = [role_id for _, role_id in DEMO_PLAYERS]
    log_event(state, "🎮 Demo mode active: 10 test players populated with pre-assigned roles matching their names.")
    save_game(state["code"], state)
    return state


def get_ordered_players(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return list of player dicts sorted according to the physical seating order."""
    order = state.get("player_order", [])
    existing_pids = set(state["players"].keys())
    valid_order = [pid for pid in order if pid in existing_pids]
    # Add any missing player IDs to the end
    for pid in state["players"]:
        if pid not in valid_order:
            valid_order.append(pid)
    state["player_order"] = valid_order
    return [state["players"][pid] for pid in valid_order]


def reorder_players(state: dict[str, Any], new_order: list[str]) -> bool:
    """Set custom physical seating order for table players."""
    existing_pids = set(state["players"].keys())
    cleaned_order = [pid for pid in new_order if pid in existing_pids]
    for pid in state["players"]:
        if pid not in cleaned_order:
            cleaned_order.append(pid)
    state["player_order"] = cleaned_order
    log_event(state, "Game Master updated table seating order.")
    save_game(state["code"], state)
    return True


def move_player(state: dict[str, Any], player_id: str, direction: str) -> bool:
    """Move a player one seat clockwise (down) or counter-clockwise (up)."""
    if player_id not in state["players"]:
        return False
    get_ordered_players(state)
    order = list(state["player_order"])
    idx = order.index(player_id)
    if direction == "up" and idx > 0:
        order[idx], order[idx - 1] = order[idx - 1], order[idx]
    elif direction == "down" and idx < len(order) - 1:
        order[idx], order[idx + 1] = order[idx + 1], order[idx]
    else:
        return False
    state["player_order"] = order
    save_game(state["code"], state)
    return True


def log_event(state: dict[str, Any], message: str) -> None:
    state["events_log"].append(
        {
            "round": state["round_number"],
            "phase": state["phase"],
            "message": message,
            "time": time.time(),
        }
    )
    # Keep last 50 events
    if len(state["events_log"]) > 50:
        state["events_log"] = state["events_log"][-50:]


# --- Timers ---


def start_timer(state: dict[str, Any], duration: int, label: str = "Timer") -> dict[str, Any]:
    now = time.time()
    state["timer"] = {
        "duration": duration,
        "ends_at": now + duration,
        "paused": False,
        "remaining": duration,
        "label": label,
    }
    save_game(state["code"], state)
    return state


def pause_timer(state: dict[str, Any]) -> dict[str, Any]:
    if not state["timer"]["paused"] and state["timer"]["ends_at"]:
        remaining = max(0, int(state["timer"]["ends_at"] - time.time()))
        state["timer"]["paused"] = True
        state["timer"]["remaining"] = remaining
        state["timer"]["ends_at"] = None
        save_game(state["code"], state)
    return state


def resume_timer(state: dict[str, Any]) -> dict[str, Any]:
    if state["timer"]["paused"]:
        now = time.time()
        rem = state["timer"]["remaining"]
        state["timer"]["paused"] = False
        state["timer"]["ends_at"] = now + rem
        save_game(state["code"], state)
    return state


def reset_timer(state: dict[str, Any], duration: Optional[int] = None) -> dict[str, Any]:
    dur = duration or state["timer"]["duration"]
    state["timer"] = {
        "duration": dur,
        "ends_at": None,
        "paused": True,
        "remaining": dur,
        "label": state["timer"]["label"],
    }
    save_game(state["code"], state)
    return state


def adjust_timer(state: dict[str, Any], delta_seconds: int) -> dict[str, Any]:
    """Add or subtract seconds from the running or paused game timer."""
    timer = state.setdefault(
        "timer",
        {
            "duration": 300,
            "ends_at": None,
            "paused": True,
            "remaining": 300,
            "label": "Discussion",
        },
    )
    now = time.time()
    if not timer.get("paused", True) and timer.get("ends_at"):
        cur_rem = max(0, int(timer["ends_at"] - now))
        new_rem = max(0, cur_rem + delta_seconds)
        timer["ends_at"] = now + new_rem
        timer["remaining"] = new_rem
        timer["duration"] = max(new_rem, timer.get("duration", 300) + delta_seconds)
    else:
        cur_rem = timer.get("remaining", timer.get("duration", 300))
        new_rem = max(0, cur_rem + delta_seconds)
        timer["remaining"] = new_rem
        timer["duration"] = max(new_rem, timer.get("duration", 300) + delta_seconds)
        timer["ends_at"] = None
    save_game(state["code"], state)
    return state


# --- Role Dealing ---


def set_deck(state: dict[str, Any], role_list: list[str]) -> dict[str, Any]:
    state["deck"] = list(role_list)
    save_game(state["code"], state)
    return state


def deal_roles(state: dict[str, Any], role_list: Optional[list[str]] = None) -> dict[str, Any]:
    """Distribute roles to all registered players, respecting any pre-assigned roles."""
    deck = list(role_list) if role_list is not None else list(state.get("deck", []))
    player_ids = list(state["players"].keys())

    # Map of player_id -> preassigned role_id
    preassigned: dict[str, str] = {}
    for pid in player_ids:
        p = state["players"][pid]
        p_role = p.get("preassigned_role") or (
            p.get("role") if state.get("phase") == "lobby" and p.get("role") else None
        )
        if p_role and p_role in ROLE_REGISTRY:
            preassigned[pid] = p_role

    # Deduct preassigned roles from deck pool
    deck_pool = list(deck)
    assigned_roles: dict[str, str] = {}
    for pid, r_id in preassigned.items():
        assigned_roles[pid] = r_id
        if r_id in deck_pool:
            deck_pool.remove(r_id)
        elif "villager" in deck_pool:
            deck_pool.remove("villager")
        elif deck_pool:
            deck_pool.pop()

    unassigned_pids = [pid for pid in player_ids if pid not in assigned_roles]

    # Balance remaining deck_pool with unassigned_pids count
    if len(deck_pool) < len(unassigned_pids):
        deck_pool.extend(["villager"] * (len(unassigned_pids) - len(deck_pool)))
    elif len(deck_pool) > len(unassigned_pids):
        deck_pool = deck_pool[: len(unassigned_pids)]

    random.shuffle(deck_pool)
    random.shuffle(unassigned_pids)

    for pid, r_id in zip(unassigned_pids, deck_pool):
        assigned_roles[pid] = r_id

    # Evil count in dealt deck to calibrate Vigilante bullets
    evil_count = sum(
        1 for r in assigned_roles.values() if ROLE_REGISTRY.get(r, {}).get("faction") == FACTION_WOLVES
    )
    evil_bullets = max(1, evil_count)

    # Check Death Angel constraint: only exists if regular Angel is also dealt!
    has_angel_dealt = any(r == "angel" for r in assigned_roles.values())
    if not has_angel_dealt:
        for pid, r in list(assigned_roles.items()):
            if r == "death_angel":
                assigned_roles[pid] = "villager"
                p_name = state["players"][pid]["name"]
                log_event(
                    state,
                    f"👼 Death Angel ({p_name}) demoted to standard Citizen because no Angel is in play.",
                )

    danger_setting = state.get("settings", {}).get("sniper_danger_bullets")
    silver_setting = state.get("settings", {}).get("sniper_silver_bullets")
    danger_bullets_qty = int(danger_setting) if danger_setting is not None else evil_bullets
    silver_bullets_qty = (
        int(silver_setting)
        if silver_setting is not None
        else (1 if state["settings"].get("sniper_bullet_type") == "mix" else 0)
    )

    for pid, role_id in assigned_roles.items():
        role_info = ROLE_REGISTRY.get(role_id, ROLE_REGISTRY["villager"])
        state["players"][pid]["role"] = role_id
        state["players"][pid]["preassigned_role"] = role_id
        state["players"][pid]["faction"] = role_info["faction"]
        state["players"][pid]["status"] = "dead" if role_id == "ghost" else "alive"
        state["players"][pid]["used_limbo"] = False
        state["players"][pid]["is_silenced"] = False
        state["players"][pid]["is_suppressed"] = False
        state["players"][pid]["haunted_by"] = None
        state["players"][pid]["lover_id"] = None
        state["players"][pid]["lover_type"] = None
        state["players"][pid]["is_traveler"] = role_id == "traveler"
        state["players"][pid]["is_ghost"] = role_id == "ghost"
        state["players"][pid]["is_successor"] = role_id == "successor"
        if role_id == "successor":
            state["players"][pid]["status"] = "waiting"
        state["players"][pid]["is_public_mayor"] = (
            role_id == "mayor"
            and (
                state.get("settings", {}).get("mayor_type", "public") == "public"
                or state.get("settings", {}).get("public_mayor", False)
            )
        )
        state["players"][pid]["sniper_danger_bullets"] = danger_bullets_qty if role_id == "sniper" else 0
        state["players"][pid]["sniper_silver_bullets"] = silver_bullets_qty if role_id == "sniper" else 0
        state["players"][pid]["death_angel_strikes"] = 1 if role_id == "death_angel" else 0
        state["players"][pid]["sniper_nights_held"] = 0

    # Automatically bind lovers if players were dealt the citizen lover role
    lover_pids = [pid for pid in player_ids if state["players"][pid]["role"] == "lover"]
    if len(lover_pids) % 2 != 0:
        lonely_pid = lover_pids.pop()
        state["players"][lonely_pid]["role"] = "villager"
        state["players"][lonely_pid]["faction"] = FACTION_TOWN

    for i in range(0, len(lover_pids), 2):
        p1_id, p2_id = lover_pids[i], lover_pids[i + 1]
        state["players"][p1_id]["lover_id"] = p2_id
        state["players"][p1_id]["lover_type"] = "innocent"
        state["players"][p2_id]["lover_id"] = p1_id
        state["players"][p2_id]["lover_type"] = "innocent"
        p1_name = state["players"][p1_id]["name"]
        p2_name = state["players"][p2_id]["name"]
        log_event(state, f"💘 Secret bond formed! Two Citizens ({p1_name} and {p2_name}) are bound as Innocent Lovers!")

    state["deck"] = [assigned_roles[pid] for pid in player_ids]
    log_event(state, f"Distributed {len(state['deck'])} roles to players.")
    save_game(state["code"], state)
    return state


def _reset_voting_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": "none",
        "system": state.get("settings", {}).get("voting_system", "two_stage_50pct"),
        "nomination_votes": {},
        "nominated_player_ids": [],
        "final_votes": {},
        "tie_count": 0,
        "revote_candidates": [],
        "defense_player_id": None,
        "eliminated_player_id": None,
        "elimination_result": None,
        "ballot_locked": False,
    }


def start_game(state: dict[str, Any], role_list: Optional[list[str]] = None) -> dict[str, Any]:
    """Transition from Pre-Game Lobby to Night 0, dealing roles to all joined players."""
    deal_roles(state, role_list)
    state["phase"] = "night"
    state["round_number"] = 0  # Starts with Night 0
    state["is_night_zero"] = True
    state["night_actions"] = {}
    state["night_report"] = []
    state["night_stage_index"] = 0
    state["revealed_inspect"] = None
    state["voting"] = _reset_voting_state(state)
    state["defense_player_id"] = None
    state["winner"] = None
    state["witch_used_revive"] = False
    state["witch_used_kill"] = False
    state["death_angel_used"] = False
    state["mayor_used_veto"] = False
    state["mayor_vetoed_ids"] = []
    state["last_silenced_id"] = None
    state["saboteur_used"] = False
    state["hacker_scanned_ids"] = []
    state["hacker_result"] = None
    state["day1_no_voting"] = False
    state["player_points"] = {}
    state["ghost_messages"] = []
    state["approved_ghost_messages"] = []
    reset_timer(state, state["settings"].get("discussion_timer", 300))
    pause_timer(state)
    log_event(state, f"🚀 Game started with {len(state['players'])} players! Night 0 begins.")
    save_game(state["code"], state)
    return state


def return_to_lobby(state: dict[str, Any]) -> dict[str, Any]:
    """End or reset the active game back to the Pre-Game Lobby while keeping players connected."""
    state["phase"] = "lobby"
    state["round_number"] = 0
    state["is_night_zero"] = False
    state["night_actions"] = {}
    state["night_report"] = []
    state["night_stage_index"] = 0
    state["revealed_inspect"] = None
    state["voting"] = _reset_voting_state(state)
    state["defense_player_id"] = None
    state["winner"] = None
    state["pending_gameover"] = None
    state["pending_gameover_dismissed"] = False
    state["broadcast_message"] = None
    state["mayor_vetoed_ids"] = []
    state["last_silenced_id"] = None
    state["saboteur_used"] = False
    state["hacker_scanned_ids"] = []
    state["hacker_result"] = None
    state["day1_no_voting"] = False
    state["ghost_messages"] = []
    state["approved_ghost_messages"] = []
    pause_timer(state)
    for p in state["players"].values():
        p["role"] = None
        p["faction"] = None
        p["status"] = "alive"
        p["used_limbo"] = False
        p["is_silenced"] = False
        p["is_suppressed"] = False
        p["haunted_by"] = None
        p["is_traveler"] = False
        p["is_ghost"] = False
        p["lover_id"] = None
        p["lover_type"] = None
        p["last_guarded_id"] = None
        p["sniper_danger_bullets"] = 1
        p["sniper_silver_bullets"] = 1 if state["settings"].get("sniper_bullet_type") == "mix" else 0
        p["sniper_nights_held"] = 0
    log_event(state, "Returned to Pre-Game Lobby. Ready to configure roles for a new game.")
    save_game(state["code"], state)
    return state


def set_round_number(state: dict[str, Any], round_number: int) -> dict[str, Any]:
    """Manually adjust round number to correct for missed rounds."""
    state["round_number"] = max(0, int(round_number))
    save_game(state["code"], state)
    return state


def set_broadcast_message(state: dict[str, Any], message: str) -> dict[str, Any]:
    """Push or clear a live announcement banner on all players' screens."""
    clean_msg = message.strip() if message else None
    state["broadcast_message"] = clean_msg
    if clean_msg:
        log_event(state, f"📢 Announcement: {clean_msg}")
    save_game(state["code"], state)
    return state


def set_manual_player_role(state: dict[str, Any], player_id: str, role_id: str) -> dict[str, Any]:
    if state.get("phase") == "lobby":
        set_preassigned_role(state, player_id, role_id)
        return state

    if player_id in state["players"]:
        role_info = ROLE_REGISTRY.get(role_id, ROLE_REGISTRY["villager"])
        old_role = state["players"][player_id].get("role")
        state["players"][player_id]["role"] = role_id
        state["players"][player_id]["faction"] = role_info["faction"]

        # If unassigning lover, unlink partner
        if old_role == "lover" and role_id != "lover":
            old_partner_id = state["players"][player_id].get("lover_id")
            if old_partner_id and old_partner_id in state["players"]:
                state["players"][old_partner_id]["lover_id"] = None
                state["players"][old_partner_id]["lover_type"] = None
            state["players"][player_id]["lover_id"] = None
            state["players"][player_id]["lover_type"] = None

        # If assigning lover, check if there is an unpartnered lover to bind with
        if role_id == "lover":
            state["players"][player_id]["lover_type"] = "innocent"
            unpartnered = [p for p in state["players"].values() if p.get("role") == "lover" and not p.get("lover_id")]
            if len(unpartnered) >= 2:
                p1, p2 = unpartnered[0], unpartnered[1]
                p1["lover_id"] = p2["id"]
                p1["lover_type"] = "innocent"
                p2["lover_id"] = p1["id"]
                p2["lover_type"] = "innocent"
                log_event(
                    state,
                    f"💘 Secret bond formed! Two Citizens ({p1['name']} and {p2['name']}) are bound as Innocent Lovers!",
                )

        if role_id == "successor":
            state["players"][player_id]["status"] = "waiting"
            state["players"][player_id]["is_successor"] = True
            log_event(state, f"⏳ {state['players'][player_id]['name']} joined as the Successor, waiting to inherit the role of the next fallen player!")

        if role_id == "mayor":
            state["players"][player_id]["is_public_mayor"] = (
                state.get("settings", {}).get("mayor_type", "public") == "public"
                or state.get("settings", {}).get("public_mayor", False)
            )

        if role_id == "sniper":
            danger_setting = state.get("settings", {}).get("sniper_danger_bullets", 1)
            silver_setting = state.get("settings", {}).get("sniper_silver_bullets", 0)
            state["players"][player_id]["sniper_danger_bullets"] = int(danger_setting)
            state["players"][player_id]["sniper_silver_bullets"] = int(silver_setting)
            state["players"][player_id]["sniper_nights_held"] = 0

        save_game(state["code"], state)
    return state


def assign_midgame_role(state: dict[str, Any], player_id: str, role_id: str) -> tuple[bool, str]:
    """Assign a role to a player who joins or changes status mid-game.

    Supports:
      - 'traveler': Confirmed good citizen, status alive.
      - 'ghost': Town spirit, status dead, can haunt and message.
      - 'disgruntled_ghost': Neutral power-suppressing spirit, status dead.
    """
    if player_id not in state.get("players", {}):
        return False, "Player not found."

    player = state["players"][player_id]
    role_info = ROLE_REGISTRY.get(role_id)
    if not role_info:
        return False, f"Invalid role '{role_id}'."

    player["role"] = role_id
    player["faction"] = role_info["faction"]

    if role_id == "traveler":
        player["status"] = "alive"
        player["is_traveler"] = True
        player["is_ghost"] = False
        player["is_successor"] = False
        msg = f"🧳 {player['name']} joined the game as a Confirmed Traveler on the side of Good!"
    elif role_id == "ghost":
        player["status"] = "dead"
        player["is_ghost"] = True
        player["is_traveler"] = False
        player["is_successor"] = False
        msg = f"👻 {player['name']} joined as a Spectral Ghost (Town Spirit)!"
    elif role_id == "disgruntled_ghost":
        player["status"] = "dead"
        player["is_ghost"] = False
        player["is_traveler"] = False
        player["is_successor"] = False
        msg = f"👿 {player['name']} entered as a Disgruntled Ghost!"
    elif role_id == "successor":
        player["status"] = "waiting"
        player["is_successor"] = True
        player["is_ghost"] = False
        player["is_traveler"] = False
        msg = f"⏳ {player['name']} joined as the Successor (Understudy), waiting to inherit the role of the next fallen player!"
    else:
        player["is_traveler"] = False
        player["is_ghost"] = False
        player["is_successor"] = False
        msg = f"🎭 {player['name']} was assigned role {role_info['names']['werewolf']} mid-game."

    log_event(state, msg)
    check_win_condition(state)
    save_game(state["code"], state)
    return True, msg


def submit_ghost_message(state: dict[str, Any], player_id: str, message: str) -> tuple[bool, str]:
    """Town Ghost submits a spectral message for GM moderation."""
    player = state.get("players", {}).get(player_id)
    if not player or player.get("role") != "ghost":
        return False, "Only Ghosts can submit spectral messages."

    clean_msg = (message or "").strip()
    if not clean_msg:
        return False, "Message cannot be empty."
    if len(clean_msg) > 160:
        clean_msg = clean_msg[:160]

    msg_id = uuid.uuid4().hex[:8]
    entry = {
        "id": msg_id,
        "player_id": player_id,
        "player_name": player["name"],
        "message": clean_msg,
        "approved": False,
        "round": state.get("round_number", 1),
        "created_at": time.time(),
    }
    state.setdefault("ghost_messages", []).append(entry)
    log_event(state, f"👻 Ghost {player['name']} submitted a spectral message for GM review: '{clean_msg}'")
    save_game(state["code"], state)
    return True, "Message submitted to Game Master for review."


def approve_ghost_message(state: dict[str, Any], message_id: str, approved: bool = True) -> tuple[bool, str]:
    """Game Master approves or rejects a ghost's spectral message to be announced at dawn."""
    messages = state.setdefault("ghost_messages", [])
    found = None
    for m in messages:
        if m["id"] == message_id:
            m["approved"] = approved
            found = m
            break
    if not found:
        return False, "Message not found."

    appr_list = state.setdefault("approved_ghost_messages", [])
    if approved:
        if not any(x["id"] == message_id for x in appr_list):
            appr_list.append(found)
        log_event(state, f"📜 Game Master approved Ghost message from {found['player_name']}: '{found['message']}'")
        msg_str = "Spectral message approved for dawn broadcast."
    else:
        state["approved_ghost_messages"] = [x for x in appr_list if x["id"] != message_id]
        log_event(state, f"❌ Game Master rejected Ghost message from {found['player_name']}.")
        msg_str = "Spectral message rejected."

    save_game(state["code"], state)
    return True, msg_str


def submit_news_bulletin(
    state: dict[str, Any],
    player_id: str,
    message: str,
    anonymous: bool = False,
) -> tuple[bool, str]:
    """Player submits an announcement, accusation, or gossip for the Morning Gazette."""
    player = state.get("players", {}).get(player_id)
    if not player:
        return False, "Player not found."

    current_round = state.get("round_number", 1)
    if player["status"] == "alive":
        if player.get("last_news_post_round") == current_round:
            return False, "You can only submit one news bulletin per day."
    elif player["status"] in ("dead", "limbo"):
        if player.get("used_dead_news_bulletin", False):
            return False, "Deceased and Limbo souls may only submit one news bulletin total."
    else:
        return False, "Waiting players cannot submit bulletins yet."

    clean_msg = (message or "").strip()
    if not clean_msg:
        return False, "Bulletin text cannot be empty."
    if len(clean_msg) > 200:
        clean_msg = clean_msg[:200]

    bulletin_id = uuid.uuid4().hex[:8]
    is_dead = player["status"] in ("dead", "limbo")
    entry = {
        "id": bulletin_id,
        "round": current_round,
        "player_id": player_id,
        "player_name": player["name"],
        "anonymous": bool(anonymous),
        "message": clean_msg,
        "status": "pending",
        "created_at": time.time(),
        "is_dead_author": is_dead,
    }
    state.setdefault("news_bulletins", []).append(entry)
    if player["status"] == "alive":
        player["last_news_post_round"] = current_round
    else:
        player["used_dead_news_bulletin"] = True

    byline_note = " (as Anonymous)" if anonymous else ""
    log_event(state, f"🗞️ {player['name']} submitted a bulletin for GM review{byline_note}: '{clean_msg}'")
    save_game(state["code"], state)
    return True, "Bulletin submitted to Game Master for review."


def approve_news_bulletin(
    state: dict[str, Any],
    bulletin_id: str,
    approved: bool = True,
) -> tuple[bool, str]:
    """Game Master approves or rejects a news bulletin for the morning gazette."""
    bulletins = state.setdefault("news_bulletins", [])
    found = None
    for b in bulletins:
        if b["id"] == bulletin_id:
            b["status"] = "approved" if approved else "rejected"
            b["approved"] = approved
            found = b
            break
    if not found:
        return False, "Bulletin not found."

    appr_list = state.setdefault("approved_news_bulletins", [])
    if approved:
        if not any(x["id"] == bulletin_id for x in appr_list):
            appr_list.append(found)
        byline = "Anonymous" if found.get("anonymous") else found["player_name"]
        log_event(state, f"🗞️ GM approved bulletin by {byline}: '{found['message']}'")
        msg_str = "Bulletin approved for morning reading."
    else:
        state["approved_news_bulletins"] = [x for x in appr_list if x["id"] != bulletin_id]
        log_event(state, f"❌ GM rejected bulletin by {found['player_name']}.")
        msg_str = "Bulletin rejected."

    save_game(state["code"], state)
    return True, msg_str


def check_and_trigger_successor_inheritance(state: dict[str, Any], deceased_id: str) -> Optional[str]:
    """When a player dies, check if an active Successor is waiting to inherit their mantle.

    If deceased was a lover with a surviving partner, Successor steps in as new lover, preventing heartbreak.
    """
    if deceased_id not in state.get("players", {}):
        return None

    deceased = state["players"][deceased_id]
    successor = None
    for p in state["players"].values():
        if (p.get("role") == "successor" or p.get("is_successor")) and p.get("status") == "waiting":
            successor = p
            break
    if not successor:
        return None

    target_role = deceased.get("role", "villager")
    role_info = ROLE_REGISTRY.get(target_role, ROLE_REGISTRY["villager"])
    successor["role"] = target_role
    successor["faction"] = role_info["faction"]
    successor["status"] = "alive"
    successor["is_successor"] = False
    successor["inherited_from_name"] = deceased["name"]

    if target_role == "sniper":
        successor["sniper_danger_bullets"] = deceased.get("sniper_danger_bullets", 1)
        successor["sniper_silver_bullets"] = deceased.get("sniper_silver_bullets", 0)
        successor["sniper_nights_held"] = 0

    lover_id = deceased.get("lover_id")
    if lover_id and lover_id in state["players"]:
        partner = state["players"][lover_id]
        if partner["status"] in ("alive", "limbo"):
            successor["lover_id"] = lover_id
            successor["lover_type"] = deceased.get("lover_type", "innocent")
            partner["lover_id"] = successor["id"]
            partner["pending_heartbreak"] = False
            partner["pending_heartbreak_from_id"] = None
            partner["pending_heartbreak_lover_name"] = None
            role_title = role_info["names"].get("werewolf", target_role)
            msg = (
                f"💘 {successor['name']} stepped in as Successor, inheriting {deceased['name']}'s mantle as "
                f"{role_title} and becoming {partner['name']}'s new lover! Heartbreak was averted!"
            )
            log_event(state, msg)
            return msg

    role_title = role_info["names"].get("werewolf", target_role)
    msg = f"⏳ {successor['name']} stepped into the game as Successor, inheriting {deceased['name']}'s mantle as {role_title} ({role_info['faction'].upper()})!"
    log_event(state, msg)
    return msg


# --- Status & Limbo ---


def set_player_status(
    state: dict[str, Any],
    player_id: str,
    new_status: str,
    stagger_lover_heartbreak: bool = False,
) -> dict[str, Any]:
    """Change player status between 'alive', 'limbo', and 'dead'. Handles lover cascade and successor inheritance."""
    if player_id not in state["players"]:
        return state

    player = state["players"][player_id]
    player["status"] = new_status

    if new_status == "limbo":
        player["used_limbo"] = True
        player["death_reveal"] = None
        log_event(state, f"{player['name']} entered Limbo.")
    elif new_status == "dead":
        player["used_limbo"] = True
        state["pending_gameover_dismissed"] = False

        # Calculate quantified role reveal strictly upon permanent death ("death death")
        level = state.get("settings", {}).get("reveal_roles_on_death", 0)
        if level is True:
            level = 3
        elif level is False or level is None:
            level = 0
        else:
            try:
                level = int(level)
            except (ValueError, TypeError):
                level = 0

        reveal_msg = ""
        if level > 0:
            role_id = player.get("role", "villager")
            faction = player.get("faction", FACTION_TOWN)
            theme = state.get("theme", "werewolf")
            from .roles import get_faction_display, get_role_info

            r_info = get_role_info(role_id, theme)
            if level == 1:
                align_str = (
                    "GOOD"
                    if faction == FACTION_TOWN
                    else ("EVIL" if faction == FACTION_WOLVES else "NEUTRAL")
                )
                reveal_msg = f"Alignment: {align_str}"
            elif level == 2:
                reveal_msg = f"Faction: {get_faction_display(faction, theme)}"
            else:
                reveal_msg = f"Role: {r_info['emoji']} {r_info['name']}"

            player["death_reveal"] = reveal_msg
            log_event(state, f"🪦 {player['name']} died permanently. [{reveal_msg}]")
        else:
            player["death_reveal"] = None
            log_event(state, f"{player['name']} died.")

        # First check if successor inherits the deceased's role!
        check_and_trigger_successor_inheritance(state, player_id)

        # Check lover cascade
        lover_id = player.get("lover_id")
        if lover_id and lover_id in state["players"]:
            lover = state["players"][lover_id]
            # If a successor took over and bound to the lover, heartbreak is averted!
            if lover.get("lover_id") == player_id and lover["status"] != "dead":
                if stagger_lover_heartbreak:
                    lover["pending_heartbreak"] = True
                    lover["pending_heartbreak_from_id"] = player_id
                    lover["pending_heartbreak_lover_name"] = player["name"]
                    log_event(
                        state,
                        f"💔 {lover['name']} is grief-stricken over {player['name']}'s execution... they will perish of grief at dawn unless saved!",
                    )
                else:
                    lover["status"] = "dead"
                    lover["used_limbo"] = True
                    log_event(state, f"{lover['name']} died of a broken heart following their lover {player['name']}!")
    elif new_status == "alive":
        log_event(state, f"{player['name']} returned to life!")
        state["pending_gameover"] = None
        state["pending_gameover_dismissed"] = False

    check_win_condition(state)
    save_game(state["code"], state)
    return state


def toggle_player_silence(state: dict[str, Any], player_id: str) -> tuple[bool, str]:
    """Toggle a player's silenced status for the day."""
    if player_id not in state.get("players", {}):
        return False, "Player not found."
    player = state["players"][player_id]
    player["is_silenced"] = not player.get("is_silenced", False)
    status_str = "silenced" if player["is_silenced"] else "unsilenced"
    emoji = "🤐" if player["is_silenced"] else "🔊"
    log_event(state, f"{emoji} {player['name']} was {status_str} by the Game Master.")
    save_game(state["code"], state)
    return True, f"Player {player['name']} {status_str}."


def rename_player(state: dict[str, Any], player_id: str, new_name: str) -> tuple[bool, str]:
    """Rename an existing player in the room state."""
    new_name = (new_name or "").strip()
    if not new_name:
        return False, "Player name cannot be empty."
    if len(new_name) > 24:
        new_name = new_name[:24]

    players = state.get("players", {})
    if player_id not in players:
        return False, "Player not found."

    for pid, p in players.items():
        if pid != player_id and p["name"].strip().lower() == new_name.lower():
            return False, f"Name '{new_name}' is already taken by another player."

    old_name = players[player_id]["name"]
    players[player_id]["name"] = new_name
    log_event(state, f"✏️ {old_name} was renamed to {new_name}.")
    save_game(state["code"], state)
    return True, f"Renamed to {new_name}."


def guess_angel_in_limbo(state: dict[str, Any], player_id: str, guessed_angel_id: str) -> tuple[bool, str]:
    """Limbo mechanic: Player gets 1 guess total to identify the Angel.
    If correct AND Angel is alive: revived!
    If incorrect (or Angel is dead): permanently dies.
    """
    if player_id not in state["players"]:
        return False, "Player not found."
    player = state["players"][player_id]

    if player["status"] != "limbo":
        return False, "You are not currently in Limbo."

    if guessed_angel_id not in state["players"]:
        return False, "Invalid target selected."

    target = state["players"][guessed_angel_id]
    player["used_limbo"] = True
    if target["role"] == "angel" and target["status"] == "alive":
        set_player_status(state, player_id, "alive")
        msg = f"✨ Divine Revelation! {player['name']} found the Angel ({target['name']}) and returned to the living!"
        log_event(state, msg)
        save_game(state["code"], state)
        return True, msg
    else:
        set_player_status(state, player_id, "dead")
        reveal_suffix = f" [{player.get('death_reveal')}]" if player.get("death_reveal") else ""
        msg = f"💀 {player['name']} guessed wrong ({target['name']} is not the living Angel) and died permanently.{reveal_suffix}"
        log_event(state, msg)
        save_game(state["code"], state)
        return False, msg


def point_at_player(
    state: dict[str, Any], source_id: str, target_id: Optional[str]
) -> dict[str, Any]:
    """Record or clear a real-time player pointing gesture."""
    points = state.setdefault("player_points", {})
    if not target_id:
        points.pop(source_id, None)
    else:
        points[source_id] = target_id
    save_game(state["code"], state)
    return state


def clear_all_player_points(state: dict[str, Any]) -> dict[str, Any]:
    """Clear all active player pointing gestures."""
    state["player_points"] = {}
    save_game(state["code"], state)
    return state


def coroner_leak_to_gazette(
    state: dict[str, Any], player_id: str, reveal_type: str = "alignment"
) -> tuple[bool, str]:
    """GM action to officially leak a deceased player's alignment or full role to the Town Gazette."""
    if player_id not in state.get("players", {}):
        return False, "Player not found."
    player = state["players"][player_id]
    if player.get("status") not in ("dead", "limbo"):
        return False, "Can only leak autopsy report for fallen players."

    theme = state.get("theme", "werewolf")
    from .roles import get_role_info

    if reveal_type == "role":
        r_info = get_role_info(player.get("role", "villager"), theme)
        msg_text = f"Coroner's Report: Autopsy confirms {player['name']} was {r_info['emoji']} {r_info['name']}."
    else:
        faction = player.get("faction", FACTION_TOWN)
        align_str = (
            "GOOD"
            if faction == FACTION_TOWN
            else ("EVIL" if faction == FACTION_WOLVES else "NEUTRAL")
        )
        msg_text = f"Coroner's Report: Autopsy of {player['name']} confirms alignment: {align_str}."

    bulletins = state.setdefault("approved_news_bulletins", [])
    bulletins.append(
        {
            "id": uuid.uuid4().hex[:8],
            "player_id": "gm_coroner",
            "player_name": "Official Coroner",
            "message": msg_text,
            "anonymous": False,
            "timestamp": time.time(),
        }
    )
    log_event(state, f"🗞️ {msg_text}")
    save_game(state["code"], state)
    return True, msg_text


# --- Night Actions & Resolution Engine ---


def get_night_stages(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Determine the active ordered stages for the night phase.

    Roles dealt in the game deck are called even if dead to prevent revealing
    casualties through omission.
    """
    stages = []
    players = state.get("players", {})
    theme = state.get("theme", "werewolf")
    is_mafia = theme == "mafia"
    actions = state.get("night_actions", {})
    ordered = get_ordered_players(state)
    round_num = state.get("round_number", 0)

    def is_role_in_game(r_id: str) -> bool:
        if r_id == "framer":
            return False
        if r_id in state.get("deck", []):
            return True
        return any(p.get("role") == r_id for p in players.values())

    def get_role_actors(r_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "seat_number": idx + 1,
                "status": p.get("status", "alive"),
                "is_alive": p.get("status") == "alive",
                "last_guarded_id": p.get("last_guarded_id"),
            }
            for idx, p in enumerate(ordered)
            if p.get("role") == r_id
        ]

    # =========================================================================
    # NIGHT 0: Introductory night with weapons holstered. No kills allowed!
    # =========================================================================
    if state.get("is_night_zero", False):
        # 1. Citizen Lovers Awaken
        if is_role_in_game("lover"):
            lover_actors = get_role_actors("lover")
            stages.append(
                {
                    "id": "lovers_meet",
                    "title": "💘 Innocent Lovers Awaken",
                    "role_id": "lover",
                    "actors": lover_actors,
                    "is_alive": True,
                    "script": "Innocent Lovers, open your eyes, discreetly make eye contact with your partner, and close your eyes.",
                    "target_ids": [a["id"] for a in lover_actors],
                    "target_names": [a["name"] for a in lover_actors],
                    "is_complete": True,
                }
            )

        # 2. Cupid (Binds Obsessive Lovers)
        if is_role_in_game("cupid"):
            cupid_actors = get_role_actors("cupid")
            current_lovers = actions.get("cupid_lovers", [])
            stages.append(
                {
                    "id": "cupid",
                    "title": "💘 Cupid (Obsessive Lovers)",
                    "role_id": "cupid",
                    "actors": cupid_actors,
                    "is_alive": True,
                    "script": "Cupid, wake up! Silently point at two players you bind as Obsessive Lovers.",
                    "target_ids": current_lovers,
                    "target_names": [players[pid]["name"] for pid in current_lovers if pid in players],
                    "is_complete": len(current_lovers) == 2 or not cupid_actors,
                }
            )

        # 3. Watson identifies Detective
        if is_role_in_game("watson"):
            watson_actors = get_role_actors("watson")
            detectives = [p["name"] for p in players.values() if p.get("role") == "detective"]
            det_name = detectives[0] if detectives else "Unknown"
            stages.append(
                {
                    "id": "watson_intro",
                    "title": "🕵️‍♂️ Watson Identification",
                    "role_id": "watson",
                    "actors": watson_actors,
                    "is_alive": True,
                    "script": f"Watson, wake up! Look at me... {det_name} is your Detective. Protect them! Watson, close your eyes.",
                    "target_name": det_name,
                    "is_complete": True,
                }
            )

        # 4. Hacker scan
        if is_role_in_game("hacker"):
            hacker_actors = get_role_actors("hacker")
            hacker_targets = actions.get("hacker_targets", [])
            stages.append(
                {
                    "id": "hacker",
                    "title": "💻 Hacker Scan",
                    "role_id": "hacker",
                    "actors": hacker_actors,
                    "is_alive": True,
                    "script": "Hacker, wake up! Silently point at the group of players (2-3) you want to scan for evil presence.",
                    "target_ids": hacker_targets,
                    "target_names": [players[pid]["name"] for pid in hacker_targets if pid in players],
                    "is_complete": len(hacker_targets) >= 2 or not hacker_actors,
                }
            )

        # 5. Wolves Meet (No attack!)
        wolves = [
            {
                "id": p["id"],
                "name": p["name"],
                "seat_number": idx + 1,
                "status": p.get("status", "alive"),
                "is_alive": p.get("status") == "alive",
            }
            for idx, p in enumerate(ordered)
            if p.get("faction") == FACTION_WOLVES
        ]
        has_wolves = bool(wolves) or any(
            r in ("werewolf", "alpha_wolf", "saboteur_wolf", "silencer") for r in state.get("deck", [])
        )
        if has_wolves:
            stages.append(
                {
                    "id": "wolves_meet",
                    "title": "🐺 Mafia Introduction" if is_mafia else "🐺 Werewolves Meet",
                    "role_id": "werewolf",
                    "actors": wolves,
                    "is_alive": True,
                    "script": (
                        "Mafia, open your eyes and look around! Acknowledge your family. No hits tonight; close your eyes."
                        if is_mafia
                        else "Werewolves, open your eyes and look around! Acknowledge your pack. No hunting tonight; close your eyes."
                    ),
                    "is_complete": True,
                }
            )

        # 6. Dawn Review (Day 0)
        stages.append(
            {
                "id": "review",
                "title": "🌅 Dawn Breaks (Day 0)",
                "role_id": "narrator",
                "actors": [],
                "is_alive": True,
                "script": "The village awakens peacefully for Day 0! Player introductions and suspicions only today; no daytime voting.",
                "is_complete": True,
            }
        )
        return stages

    # 1. Disgruntled Ghost (Called early in the night: power suppression)
    if is_role_in_game("disgruntled_ghost"):
        dg_actors = get_role_actors("disgruntled_ghost")
        dg_target_id = actions.get("disgruntled_ghost_target")
        stages.append(
            {
                "id": "disgruntled_ghost",
                "title": "👿 Disgruntled Ghost",
                "role_id": "disgruntled_ghost",
                "actors": dg_actors,
                "is_alive": True,  # Ghost exists in spirit
                "script": "Disgruntled Ghost, wake up! Silently point at the player whose powers you will suppress tonight.",
                "target_id": dg_target_id,
                "target_name": players[dg_target_id]["name"] if dg_target_id in players else None,
                "is_complete": bool(dg_target_id),
            }
        )

    # 2. Hacker (Night 1 only)
    if round_num <= 1 and is_role_in_game("hacker"):
        hacker_actors = get_role_actors("hacker")
        is_alive = any(a["is_alive"] for a in hacker_actors)
        hacker_targets = actions.get("hacker_targets", [])
        stages.append(
            {
                "id": "hacker",
                "title": "💻 Hacker Scan",
                "role_id": "hacker",
                "actors": hacker_actors,
                "is_alive": is_alive,
                "script": "Hacker, wake up! Silently point at the group of players (2-3) you want to scan for evil presence.",
                "target_ids": hacker_targets,
                "target_names": [players[pid]["name"] for pid in hacker_targets if pid in players],
                "is_complete": len(hacker_targets) >= 2 or not is_alive,
            }
        )

    # 3. Citizen Lovers Meet (Night 1 only)
    if round_num <= 1 and is_role_in_game("lover"):
        lover_actors = get_role_actors("lover")
        is_alive = any(a["is_alive"] for a in lover_actors)
        lover_names = [a["name"] for a in lover_actors]
        stages.append(
            {
                "id": "lovers_meet",
                "title": "💘 Innocent Lovers Awaken",
                "role_id": "lover",
                "actors": lover_actors,
                "is_alive": is_alive,
                "script": "Innocent Lovers, open your eyes, discreetly make eye contact with your partner, and close your eyes.",
                "target_ids": [a["id"] for a in lover_actors],
                "target_names": lover_names,
                "is_complete": True,
            }
        )

    # 4. Cupid (Night 1 only)
    if round_num <= 1 and is_role_in_game("cupid"):
        cupid_actors = get_role_actors("cupid")
        is_alive = any(a["is_alive"] for a in cupid_actors)
        current_lovers = actions.get("cupid_lovers", [])
        stages.append(
            {
                "id": "cupid",
                "title": "💘 Cupid (Obsessive Lovers)",
                "role_id": "cupid",
                "actors": cupid_actors,
                "is_alive": is_alive,
                "script": "Cupid, wake up! Silently point at two players you bind as Obsessive Lovers.",
                "target_ids": current_lovers,
                "target_names": [players[pid]["name"] for pid in current_lovers if pid in players],
                "is_complete": len(current_lovers) == 2 or not is_alive,
            }
        )

    # 5. Saboteur Wolf (1-time power suppression + role steal)
    if is_role_in_game("saboteur_wolf") and not state.get("saboteur_used", False):
        sab_actors = get_role_actors("saboteur_wolf")
        is_alive = any(a["is_alive"] for a in sab_actors)
        sab_target_id = actions.get("saboteur_target")
        stages.append(
            {
                "id": "saboteur_wolf",
                "title": "🐺⚡ Saboteur Wolf",
                "role_id": "saboteur_wolf",
                "actors": sab_actors,
                "is_alive": is_alive,
                "script": "Saboteur Wolf, wake up! If using your 1-time sabotage, silently point at a citizen to steal and suppress their power.",
                "target_id": sab_target_id,
                "target_name": players[sab_target_id]["name"] if sab_target_id in players else None,
                "is_complete": bool(sab_target_id) or not is_alive,
            }
        )

    # 6. Werewolves / Mafia
    has_wolves = any(p.get("faction") == FACTION_WOLVES for p in players.values()) or any(
        r in ("werewolf", "alpha_wolf", "saboteur_wolf", "silencer") for r in state.get("deck", [])
    )
    if has_wolves:
        wolves = [
            {
                "id": p["id"],
                "name": p["name"],
                "seat_number": idx + 1,
                "status": p.get("status", "alive"),
                "is_alive": p.get("status") == "alive",
            }
            for idx, p in enumerate(ordered)
            if p.get("faction") == FACTION_WOLVES
        ]
        is_alive = any(w["is_alive"] for w in wolves)
        wolf_target_id = actions.get("wolf_target")
        wolf_target_name = players[wolf_target_id]["name"] if wolf_target_id in players else None
        stages.append(
            {
                "id": "wolves",
                "title": "🐺 Mafia Hit" if is_mafia else "🐺 Werewolves Hunt",
                "role_id": "werewolf",
                "actors": wolves,
                "is_alive": is_alive,
                "script": (
                    "Mafia, wake up! Silently agree and point at your victim."
                    if is_mafia
                    else "Werewolves, wake up! Look at each other and silently point at your victim."
                ),
                "target_id": wolf_target_id,
                "target_name": wolf_target_name,
                "is_complete": bool(wolf_target_id) or not is_alive,
            }
        )

    # 7. Silencer (Staggered: cannot silence same player twice in a row)
    if is_role_in_game("silencer"):
        silencers = get_role_actors("silencer")
        is_alive = any(s["is_alive"] for s in silencers)
        s_target_id = actions.get("silencer_target")
        last_silenced_id = state.get("last_silenced_id")
        stages.append(
            {
                "id": "silencer",
                "title": "🤐 Consigliere (Silence)" if is_mafia else "🤐 Silencer Spell",
                "role_id": "silencer",
                "actors": silencers,
                "is_alive": is_alive,
                "last_silenced_id": last_silenced_id,
                "script": "Silencer, wake up! Silently point at the player who cannot speak tomorrow (cannot be yesterday's target; silenced players can still vote!).",
                "target_id": s_target_id,
                "target_name": players[s_target_id]["name"] if s_target_id in players else None,
                "is_complete": bool(s_target_id) or not is_alive,
            }
        )

    # 8. Detective
    if is_role_in_game("detective"):
        detectives = get_role_actors("detective")
        is_alive = any(d["is_alive"] for d in detectives)
        det_query = actions.get("detective_query", {})
        det_target_id = det_query.get("target_id")
        stages.append(
            {
                "id": "detective",
                "title": "🔍 Detective Investigation",
                "role_id": "detective",
                "actors": detectives,
                "is_alive": is_alive,
                "script": "Detective, wake up! Silently point at the person you want to inspect.",
                "target_id": det_target_id,
                "target_name": players[det_target_id]["name"] if det_target_id in players else None,
                "result": det_query.get("result"),
                "is_evil": det_query.get("is_evil"),
                "is_complete": bool(det_target_id) or not is_alive,
            }
        )

    # 9. Doctor / Medic
    if is_role_in_game("doctor"):
        doctors = get_role_actors("doctor")
        is_alive = any(d["is_alive"] for d in doctors)
        doc_target_id = actions.get("doctor_protect")
        last_guarded = doctors[0].get("last_guarded_id") if doctors else None
        stages.append(
            {
                "id": "doctor",
                "title": "🩺 Doctor / Guard",
                "role_id": "doctor",
                "actors": doctors,
                "is_alive": is_alive,
                "script": "Doctor, wake up! Silently point at the player you want to protect tonight.",
                "target_id": doc_target_id,
                "target_name": players[doc_target_id]["name"] if doc_target_id in players else None,
                "last_guarded_id": last_guarded,
                "is_complete": bool(doc_target_id) or not is_alive,
            }
        )

    # 10. Bodyguard
    if is_role_in_game("bodyguard"):
        bodyguards = get_role_actors("bodyguard")
        is_alive = any(b["is_alive"] for b in bodyguards)
        bg_target_id = actions.get("bodyguard_protect")
        stages.append(
            {
                "id": "bodyguard",
                "title": "🛡️ Bodyguard Shield",
                "role_id": "bodyguard",
                "actors": bodyguards,
                "is_alive": is_alive,
                "script": "Bodyguard, wake up! Silently point at who you will shield with your life (cannot protect yourself).",
                "target_id": bg_target_id,
                "target_name": players[bg_target_id]["name"] if bg_target_id in players else None,
                "is_complete": bool(bg_target_id) or not is_alive,
            }
        )

    # 11. Witch
    if is_role_in_game("witch"):
        witches = get_role_actors("witch")
        is_alive = any(w["is_alive"] for w in witches)
        has_revive = not state.get("witch_used_revive", False)
        has_kill = not state.get("witch_used_kill", False)
        w_act = actions.get("witch_action", {})
        victim_id = actions.get("wolf_target")
        victim_name = players[victim_id]["name"] if victim_id in players else "Nobody"
        stages.append(
            {
                "id": "witch",
                "title": "🧙‍♀️ Witch / Chemist",
                "role_id": "witch",
                "actors": witches,
                "is_alive": is_alive,
                "script": (
                    f"Witch, wake up! Tonight's victim is {victim_name}. "
                    "Do you want to use your revival potion? Do you want to poison someone? (Cannot self-heal if attacked tonight!)"
                )
                if victim_id
                else "Witch, wake up! Do you want to use your revival potion or lethal poison?",
                "victim_name": victim_name,
                "revive": w_act.get("revive", False),
                "has_revive_potion": has_revive,
                "has_kill_potion": has_kill,
                "kill_target_id": w_act.get("kill_target"),
                "kill_target_name": players[w_act["kill_target"]]["name"]
                if w_act.get("kill_target") in players
                else None,
                "is_complete": bool(w_act) or not is_alive or (not has_revive and not has_kill),
            }
        )

    # 12. Vigilante / Sniper
    if is_role_in_game("sniper"):
        snipers = get_role_actors("sniper")
        is_alive = any(s["is_alive"] for s in snipers)
        s_act = actions.get("sniper_shot", {})
        s_target_id = s_act.get("target_id")
        sniper_p = snipers[0] if snipers else {}
        danger_bullets = state["players"].get(sniper_p.get("id"), {}).get("sniper_danger_bullets", 1)
        silver_bullets = state["players"].get(sniper_p.get("id"), {}).get("sniper_silver_bullets", 0)
        stages.append(
            {
                "id": "sniper",
                "title": "🎯 Vigilante / Sniper",
                "role_id": "sniper",
                "actors": snipers,
                "is_alive": is_alive,
                "danger_bullets": danger_bullets,
                "silver_bullets": silver_bullets,
                "script": (
                    "Vigilante, wake up! Silently point if you wish to shoot someone tonight, or shake head to pass. "
                    "Danger bullets kill evil but backfire on innocents; Silver bullets are safe!"
                ),
                "target_id": s_target_id,
                "target_name": players[s_target_id]["name"] if s_target_id in players else None,
                "bullet_type": s_act.get("bullet_type", "danger"),
                "is_complete": bool(s_target_id) or not is_alive,
            }
        )

    # 13. Serial Killer
    if is_role_in_game("serial_killer"):
        sks = get_role_actors("serial_killer")
        is_alive = any(s["is_alive"] for s in sks)
        sk_target_id = actions.get("sk_target")
        stages.append(
            {
                "id": "serial_killer",
                "title": "🔪 Serial Killer Strike",
                "role_id": "serial_killer",
                "actors": sks,
                "is_alive": is_alive,
                "script": "Serial Killer, wake up! Silently point at your solo victim.",
                "target_id": sk_target_id,
                "target_name": players[sk_target_id]["name"] if sk_target_id in players else None,
                "is_complete": bool(sk_target_id) or not is_alive,
            }
        )

    # 14. Wolf Hunter
    if is_role_in_game("wolf_hunter"):
        hunters = get_role_actors("wolf_hunter")
        is_alive = any(h["is_alive"] for h in hunters)
        wh_target_id = actions.get("wolf_hunter_target")
        stages.append(
            {
                "id": "wolf_hunter",
                "title": "🏹 Wolf Hunter Strike",
                "role_id": "wolf_hunter",
                "actors": hunters,
                "is_alive": is_alive,
                "script": "Wolf Hunter, wake up! Point at a player to hunt. If they are a werewolf, they die; if not, your shot backfires and you die!",
                "target_id": wh_target_id,
                "target_name": players[wh_target_id]["name"] if wh_target_id in players else None,
                "is_complete": bool(wh_target_id) or not is_alive,
            }
        )

    # 15. Death Angel (can strike from living or Limbo)
    if is_role_in_game("death_angel"):
        death_angels = get_role_actors("death_angel")
        can_act = any(da["status"] in ("alive", "limbo") for da in death_angels) and not state.get("death_angel_used", False)
        da_target_id = actions.get("death_angel_target")
        stages.append(
            {
                "id": "death_angel",
                "title": "👼🗡️ Death Angel Strike",
                "role_id": "death_angel",
                "actors": death_angels,
                "is_alive": can_act,
                "script": "Death Angel, wake up! Point at a soul hovering in Limbo to sever their earthly tether permanently (limit: 1 strike per game).",
                "target_id": da_target_id,
                "target_name": players[da_target_id]["name"] if da_target_id in players else None,
                "is_complete": bool(da_target_id) or not can_act,
            }
        )

    # 16. Town Ghost Haunt
    if is_role_in_game("ghost"):
        ghost_actors = get_role_actors("ghost")
        ghost_target_id = actions.get("ghost_haunt")
        stages.append(
            {
                "id": "ghost",
                "title": "👻 Town Ghost Haunt",
                "role_id": "ghost",
                "actors": ghost_actors,
                "is_alive": True,  # Spirit acts from beyond
                "script": "Town Ghost, wake up! Silently point at the player you wish to haunt tonight.",
                "target_id": ghost_target_id,
                "target_name": players[ghost_target_id]["name"] if ghost_target_id in players else None,
                "is_complete": bool(ghost_target_id),
            }
        )

    # 17. Mayor Veto (Once Per Person!)
    if is_role_in_game("mayor"):
        mayors = get_role_actors("mayor")
        is_alive = any(m["is_alive"] for m in mayors)
        last_lynched_id = state.get("last_lynched_id")
        vetoed_ids = state.get("mayor_vetoed_ids", [])
        has_veto = (last_lynched_id is not None) and (last_lynched_id not in vetoed_ids)
        last_lynched_name = players[last_lynched_id]["name"] if last_lynched_id in players else None
        if round_num <= 1 or not last_lynched_name:
            script = "Mayor, wake up! Look at me so I know who you are... Mayor, close your eyes."
        else:
            script = f"Mayor, wake up! Yesterday, {last_lynched_name} was executed. Do you wish to exercise your veto to pardon them? (Limit: once per person)."
        stages.append(
            {
                "id": "mayor",
                "title": "🎖️ Mayor Veto",
                "role_id": "mayor",
                "actors": mayors,
                "is_alive": is_alive,
                "has_veto": has_veto,
                "last_lynched_id": last_lynched_id,
                "last_lynched_name": last_lynched_name,
                "veto": actions.get("mayor_veto", False),
                "script": script,
                "is_complete": True,
            }
        )

    # 18. Limbo Angel Guessing Stage (Penultimate stage when souls are in Limbo)
    limbo_souls = [p for p in ordered if p.get("status") == "limbo"]
    if limbo_souls:
        stages.append(
            {
                "id": "limbo_angel_guess",
                "title": "🌫️ Limbo Souls: Angel Guess",
                "role_id": None,
                "actors": limbo_souls,
                "is_alive": True,
                "limbo_players": [
                    {"id": p["id"], "name": p["name"], "seat_number": p.get("seat_number", 0)}
                    for p in limbo_souls
                ],
                "script": (
                    "Call souls in Limbo one by one in secret. Ask: 'Do you wish to use your 1 guess "
                    "for the Angel tonight?' If correct and Angel lives, they return to life! If wrong, they pass away permanently."
                ),
                "is_complete": True,
            }
        )

    # 19. Dawn Review (Always final stage)
    stages.append(
        {
            "id": "review",
            "title": "☀️ Dawn Review & Resolve",
            "role_id": None,
            "actors": [],
            "is_alive": True,
            "script": (
                "Review all registered night actions. When ready, wake up the town to "
                "announce dawn and start day discussion!"
            ),
            "is_complete": True,
        }
    )

    return stages


def record_gm_night_action(
    state: dict[str, Any],
    stage_id: str,
    target_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> tuple[bool, str]:
    """Store night action directly registered by the Game Master from player finger-pointing."""
    actions = state.setdefault("night_actions", {})
    players = state.get("players", {})

    if stage_id == "disgruntled_ghost":
        actions["disgruntled_ghost_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Disgruntled Ghost target set to: {name}")
        save_game(state["code"], state)
        return True, f"Disgruntled Ghost targets: {name}"

    elif stage_id == "hacker":
        targets = list(actions.get("hacker_targets", []))
        if target_id:
            if target_id in targets:
                targets.remove(target_id)
            else:
                targets.append(target_id)
        actions["hacker_targets"] = targets
        log_event(state, f"Hacker targets updated: {len(targets)} players selected")
        save_game(state["code"], state)
        return True, f"Hacker selected {len(targets)} players"

    elif stage_id == "saboteur_wolf":
        actions["saboteur_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Saboteur Wolf target set to: {name}")
        save_game(state["code"], state)
        return True, f"Saboteur Wolf targets: {name}"

    elif stage_id == "ghost":
        actions["ghost_haunt"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Town Ghost haunt target set to: {name}")
        save_game(state["code"], state)
        return True, f"Ghost haunts: {name}"

    elif stage_id == "wolves":
        actions["wolf_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Wolves victim set to: {name}")
        save_game(state["code"], state)
        return True, f"Wolves target: {name}"

    elif stage_id == "silencer":
        if target_id and target_id == state.get("last_silenced_id"):
            return False, "Cannot silence the same player two nights in a row (staggered rule)."
        actions["silencer_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Silencer target set to: {name}")
        save_game(state["code"], state)
        return True, f"Silencer target: {name}"

    elif stage_id == "detective":
        if not target_id or target_id not in players:
            return False, "Invalid inspection target."
        target = players[target_id]
        is_framed = actions.get("framer_target") == target_id
        is_evil = is_evil_for_detective(target, is_framed=is_framed)
        result_text = "Evil" if is_evil else "Good"
        det_actor = next(
            (p["id"] for p in players.values() if p["role"] == "detective" and p["status"] == "alive"), None
        )
        actions["detective_query"] = {
            "actor_id": det_actor,
            "target_id": target_id,
            "target_name": target["name"],
            "result": result_text,
            "is_evil": is_evil,
        }
        log_event(state, f"Detective inspected {target['name']}: {result_text}")
        save_game(state["code"], state)
        return True, f"{target['name']} is {result_text}"

    elif stage_id == "doctor":
        actions["doctor_protect"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Doctor protect set to: {name}")
        save_game(state["code"], state)
        return True, f"Doctor protects: {name}"

    elif stage_id == "bodyguard":
        bg_actor = next(
            (p["id"] for p in players.values() if p["role"] == "bodyguard" and p["status"] == "alive"), None
        )
        actions["bodyguard_protect"] = target_id
        actions["bodyguard_actor"] = bg_actor
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Bodyguard target set to: {name}")
        save_game(state["code"], state)
        return True, f"Bodyguard guards: {name}"

    elif stage_id == "witch":
        extra = extra or {}
        revive = bool(extra.get("revive"))
        kill_target = extra.get("kill_target")
        actions["witch_action"] = {
            "revive": revive,
            "kill_target": kill_target,
        }
        log_event(state, f"Witch action set (revive={revive}, kill={kill_target})")
        save_game(state["code"], state)
        return True, "Witch action updated"

    elif stage_id == "sniper":
        extra = extra or {}
        sniper_actor = next(
            (p["id"] for p in players.values() if p["role"] == "sniper" and p["status"] == "alive"), None
        )
        bullet_type = extra.get("bullet_type", "danger")
        actions["sniper_shot"] = {
            "actor_id": sniper_actor,
            "target_id": target_id,
            "bullet_type": bullet_type,
        }
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Sniper shot set to: {name} (bullet: {bullet_type})")
        save_game(state["code"], state)
        return True, f"Sniper shot: {name} ({bullet_type})"

    elif stage_id == "serial_killer":
        actions["sk_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Serial Killer target set to: {name}")
        save_game(state["code"], state)
        return True, f"Serial Killer target: {name}"

    elif stage_id == "mayor":
        extra = extra or {}
        veto = bool(extra.get("veto", True))
        last_lynched = state.get("last_lynched_id")
        vetoed_ids = state.get("mayor_vetoed_ids", [])
        if veto:
            if not last_lynched:
                return False, "No executed player to veto."
            if last_lynched in vetoed_ids:
                return False, "Mayor has already vetoed this player once (limit 1 veto per person)."
            actions["mayor_veto"] = True
            victim_name = players[last_lynched]["name"] if last_lynched in players else "None"
            log_event(state, f"Game Master recorded Mayor veto: {victim_name} pardoned")
            save_game(state["code"], state)
            return True, f"Mayor veto: {victim_name}"
        else:
            actions.pop("mayor_veto", None)
            log_event(state, "Game Master cleared Mayor veto")
            save_game(state["code"], state)
            return True, "Mayor veto cleared"

    elif stage_id == "cupid":
        lovers = list(actions.get("cupid_lovers", []))
        if target_id:
            if target_id in lovers:
                lovers.remove(target_id)
            else:
                if len(lovers) >= 2:
                    lovers = [lovers[1], target_id]
                else:
                    lovers.append(target_id)
        actions["cupid_lovers"] = lovers[:2]
        log_event(state, f"Cupid lovers updated: {lovers}")
        save_game(state["code"], state)
        return True, f"Cupid lovers: {len(actions['cupid_lovers'])} selected"

    elif stage_id == "wolf_hunter":
        actions["wolf_hunter_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Wolf Hunter target set to: {name}")
        save_game(state["code"], state)
        return True, f"Wolf Hunter targets: {name}"

    elif stage_id == "death_angel":
        actions["death_angel_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Death Angel strike set to: {name}")
        save_game(state["code"], state)
        return True, f"Death Angel strikes: {name}"

    return False, "Unknown stage"


def clear_gm_night_action(state: dict[str, Any], stage_id: str) -> None:
    actions = state.setdefault("night_actions", {})
    mapping = {
        "disgruntled_ghost": "disgruntled_ghost_target",
        "hacker": "hacker_targets",
        "saboteur_wolf": "saboteur_target",
        "wolves": "wolf_target",
        "wolf_hunter": "wolf_hunter_target",
        "death_angel": "death_angel_target",
        "silencer": "silencer_target",
        "framer": "framer_target",
        "detective": "detective_query",
        "doctor": "doctor_protect",
        "bodyguard": "bodyguard_protect",
        "witch": "witch_action",
        "sniper": "sniper_shot",
        "serial_killer": "sk_target",
        "ghost": "ghost_haunt",
        "mayor": "mayor_veto",
        "cupid": "cupid_lovers",
    }
    key = mapping.get(stage_id)
    if key and key in actions:
        del actions[key]
        save_game(state["code"], state)


def set_night_stage_index(state: dict[str, Any], index: int) -> None:
    stages = get_night_stages(state)
    max_idx = max(0, len(stages) - 1)
    state["night_stage_index"] = max(0, min(index, max_idx))
    save_game(state["code"], state)


def reveal_detective_to_player(state: dict[str, Any]) -> None:
    query = state.get("night_actions", {}).get("detective_query")
    if query:
        state["revealed_inspect"] = query
        log_event(state, "Game Master revealed inspection result to Detective.")
        save_game(state["code"], state)


def submit_night_action(
    state: dict[str, Any],
    actor_id: str,
    action_type: str,
    target_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> tuple[bool, str]:
    """Store night action from a role for the GM to execute/resolve."""
    if actor_id not in state["players"]:
        return False, "Invalid actor."

    actor = state["players"][actor_id]
    if actor["status"] != "alive":
        return False, "Only living players can perform night actions."

    actions = state.setdefault("night_actions", {})

    if action_type == "kill":
        if actor["faction"] != FACTION_WOLVES:
            return False, "Not authorized to kill."
        actions["wolf_target"] = target_id
        return True, "Wolf target submitted."

    elif action_type == "inspect":
        if actor["role"] != "detective":
            return False, "Not a detective."
        if not target_id or target_id not in state["players"]:
            return False, "Invalid inspection target."
        target = state["players"][target_id]
        is_framed = actions.get("framer_target") == target_id
        is_evil = is_evil_for_detective(target, is_framed=is_framed)
        result_text = "Evil" if is_evil else "Good"
        actions["detective_query"] = {
            "actor_id": actor_id,
            "target_id": target_id,
            "result": result_text,
        }
        return True, f"Inspection result: {target['name']} is {result_text}."

    elif action_type == "protect":
        if actor["role"] != "doctor":
            return False, "Not a doctor."
        if state["settings"].get("staggering_doctor") and actor.get("last_guarded_id") == target_id:
            return False, "Staggering Doctor rule: You cannot protect the same person two nights in a row!"
        actions["doctor_protect"] = target_id
        return True, "Protection target set."

    elif action_type == "guard_bodyguard":
        if actor["role"] != "bodyguard":
            return False, "Not a bodyguard."
        actions["bodyguard_protect"] = target_id
        actions["bodyguard_actor"] = actor_id
        return True, "Bodyguard protection set."

    elif action_type == "frame":
        if actor["role"] != "framer":
            return False, "Not a framer."
        actions["framer_target"] = target_id
        return True, "Framing target set."

    elif action_type == "solo_kill":
        if actor["role"] != "serial_killer":
            return False, "Not a serial killer."
        actions["sk_target"] = target_id
        return True, "Solo kill target set."

    elif action_type == "shoot":
        if actor["role"] != "sniper":
            return False, "Not a sniper."
        bullet_type = (extra or {}).get("bullet_type", state["settings"].get("sniper_bullet_type", "danger"))
        actions["sniper_shot"] = {
            "actor_id": actor_id,
            "target_id": target_id,
            "bullet_type": bullet_type,
        }
        return True, "Sniper target locked."

    elif action_type == "silence":
        if actor["role"] != "silencer":
            return False, "Not a silencer."
        if target_id and target_id == state.get("last_silenced_id"):
            return False, "Cannot silence the same player two nights in a row."
        actions["silencer_target"] = target_id
        return True, "Silence target set."

    elif action_type == "potion":
        if actor["role"] != "witch":
            return False, "Not a witch."
        revive = bool((extra or {}).get("revive"))
        kill_target = (extra or {}).get("kill_target")
        if revive and state["witch_used_revive"]:
            return False, "Revive potion already used."
        if kill_target and state["witch_used_kill"]:
            return False, "Death potion already used."
        actions["witch_action"] = {
            "revive": revive,
            "kill_target": kill_target,
        }
        return True, "Witch potion action queued."

    elif action_type == "veto":
        if actor["role"] != "mayor":
            return False, "Not a mayor."
        last_lynched = state.get("last_lynched_id")
        if not last_lynched or last_lynched in state.get("mayor_vetoed_ids", []):
            return False, "Cannot veto: Person already vetoed or no executed player."
        actions["mayor_veto"] = True
        return True, "Mayor veto activated."

    elif action_type == "link_lovers":
        if actor["role"] != "cupid":
            return False, "Not cupid."
        lovers = (extra or {}).get("lovers", [])
        if len(lovers) != 2:
            return False, "Cupid must choose exactly two lovers."
        actions["cupid_lovers"] = lovers
        return True, "Lovers bound by destiny."

    save_game(state["code"], state)
    return False, "Unknown action."


def resolve_night(state: dict[str, Any]) -> dict[str, Any]:
    """Execute all night actions and produce the morning dawn report."""
    actions = state.get("night_actions", {})
    report: list[str] = []
    to_kill: set[str] = set()
    to_save: set[str] = set()
    suppressed_pids: set[str] = set()

    # Clear player pointing gestures on dawn
    state["player_points"] = {}

    # =========================================================================
    # NIGHT 0 RESOLUTION: Transition peacefully to Day 0 (Introductions only)
    # =========================================================================
    if state.get("is_night_zero", False):
        state["is_night_zero"] = False
        # Cupid Lovers (Night 0 Obsessive Bond)
        if "cupid_lovers" in actions:
            lovers = actions["cupid_lovers"]
            if len(lovers) == 2:
                l1, l2 = lovers[0], lovers[1]
                if l1 in state["players"] and l2 in state["players"]:
                    state["players"][l1]["lover_id"] = l2
                    state["players"][l1]["lover_type"] = "obsessive"
                    state["players"][l2]["lover_id"] = l1
                    state["players"][l2]["lover_type"] = "obsessive"
                    log_event(
                        state,
                        f"💘 Cupid bound {state['players'][l1]['name']} and {state['players'][l2]['name']} as Obsessive Lovers!",
                    )

        # Hacker Night 0 Scan
        if actions.get("hacker_targets"):
            scanned_ids = actions["hacker_targets"]
            state["hacker_scanned_ids"] = list(scanned_ids)
            total_scanned = len(scanned_ids)
            evil_count = sum(
                1
                for pid in scanned_ids
                if pid in state["players"]
                and is_evil_faction_or_threat(state["players"][pid])
            )
            if evil_count == total_scanned and total_scanned > 0:
                result_str = "All Evil"
            elif evil_count > (total_scanned / 2.0):
                result_str = "Majority Evil"
            elif total_scanned > 0 and evil_count == (total_scanned / 2.0):
                result_str = "Even Split"
            elif evil_count > 0:
                result_str = "Minority Evil"
            else:
                result_str = "Clean (All Good)"
            state["hacker_result"] = result_str
            state["hacker_evil_count"] = evil_count
            state["hacker_total_count"] = total_scanned

        # Transition to Day 0
        state["phase"] = "day_discussion"
        state["round_number"] = 0
        state["is_day_zero"] = True
        state["night_actions"] = {}
        state["night_stage_index"] = 0
        state["revealed_inspect"] = None
        state["voting"] = _reset_voting_state(state)
        state["night_report"] = [
            "☀️ Dawn breaks over Day 0. The village awakens peacefully!",
            "💬 Day 0 is reserved for player introductions and initial suspicions. Voting and executions begin on Day 1.",
        ]
        start_timer(state, state["settings"].get("discussion_timer", 300), "Day 0 Introductions")
        check_win_condition(state)
        save_game(state["code"], state)
        return state

    # Reset per-night temporary suppression and haunted markers
    for p in state["players"].values():
        p["is_suppressed"] = False
        p["haunted_by"] = None

    # --- 1. Disgruntled Ghost (Early Power Suppression) ---
    has_disgruntled = any(p["role"] == "disgruntled_ghost" for p in state["players"].values())
    dg_target = actions.get("disgruntled_ghost_target")
    if has_disgruntled and dg_target and dg_target in state["players"]:
        suppressed_pids.add(dg_target)
        state["players"][dg_target]["is_suppressed"] = True
        log_event(state, f"👿 Disgruntled Ghost suppressed powers of {state['players'][dg_target]['name']} tonight.")

    # --- 2. Saboteur Wolf (1-Time Suppression + Role Steal) ---
    has_living_saboteur = any(
        p["role"] == "saboteur_wolf" and p["status"] == "alive" for p in state["players"].values()
    )
    sab_target = actions.get("saboteur_target")
    if has_living_saboteur and not state.get("saboteur_used") and sab_target and sab_target in state["players"]:
        suppressed_pids.add(sab_target)
        t_player = state["players"][sab_target]
        t_player["is_suppressed"] = True
        state["saboteur_used"] = True
        actions["saboteur_stolen_role"] = t_player.get("role")
        log_event(
            state, f"⚡ Saboteur Wolf suppressed {t_player['name']} and uncovered their role ({t_player.get('role')})!"
        )

    # --- 3. Hacker Intel Announcement (Dawn of Day 1) ---
    if state.get("round_number", 1) == 1 and state.get("hacker_scanned_ids"):
        res = state.get("hacker_result", "Clean")
        evil_c = state.get("hacker_evil_count", 0)
        tot_c = state.get("hacker_total_count", len(state["hacker_scanned_ids"]))
        report.append(
            f"💻 Hacker Intel: Scanned suspects evaluated as '{res}' ({evil_c} of {tot_c} Evil)!"
        )
        log_event(state, f"💻 Hacker scan revealed: {res}")

    # --- 4. Cupid Lovers (Fallback / Dynamic Bind) ---
    if "cupid_lovers" in actions:
        lovers = actions["cupid_lovers"]
        if len(lovers) == 2:
            l1, l2 = lovers[0], lovers[1]
            if l1 in state["players"] and l2 in state["players"]:
                state["players"][l1]["lover_id"] = l2
                state["players"][l1]["lover_type"] = "obsessive"
                state["players"][l2]["lover_id"] = l1
                state["players"][l2]["lover_type"] = "obsessive"
                log_event(
                    state,
                    f"💘 Cupid bound {state['players'][l1]['name']} and {state['players'][l2]['name']} as Obsessive Lovers!",
                )

    # --- 5. Doctor Protect ---
    doc_target = actions.get("doctor_protect")
    doc_actor = next((p for p in state["players"].values() if p["role"] == "doctor" and p["status"] == "alive"), None)
    if doc_actor and doc_actor["id"] not in suppressed_pids and doc_target and doc_target in state["players"]:
        to_save.add(doc_target)
        doc_actor["last_guarded_id"] = doc_target

    # --- 6. Bodyguard Shield Setup ---
    bg_actor = next((p for p in state["players"].values() if p["role"] == "bodyguard" and p["status"] == "alive"), None)
    bg_target = actions.get("bodyguard_protect")
    bg_active = (
        bg_actor is not None
        and bg_actor["id"] not in suppressed_pids
        and bg_target is not None
        and bg_target in state["players"]
        and bg_actor["id"] != bg_target
    )

    # --- 7. Attacks: Werewolves, Serial Killer, Vigilante/Sniper ---
    has_living_wolves = any(
        p.get("faction") == FACTION_WOLVES and p["status"] == "alive" for p in state["players"].values()
    )
    wolf_target = actions.get("wolf_target")
    wolf_attack = wolf_target if (has_living_wolves and wolf_target in state["players"]) else None

    sk_actor = next(
        (p for p in state["players"].values() if p["role"] == "serial_killer" and p["status"] == "alive"), None
    )
    sk_target = actions.get("sk_target")
    sk_attack = (
        sk_target if (sk_actor and sk_actor["id"] not in suppressed_pids and sk_target in state["players"]) else None
    )

    sniper_actor = next(
        (p for p in state["players"].values() if p["role"] == "sniper" and p["status"] == "alive"), None
    )
    sniper_act = actions.get("sniper_shot", {})
    sniper_target = sniper_act.get("target_id")
    sniper_bullet_type = sniper_act.get("bullet_type", "danger")

    # Vigilante shooting & restraint bonus:
    if sniper_actor:
        if sniper_target:
            sniper_actor["sniper_nights_held"] = 0
            if sniper_bullet_type == "silver":
                sniper_actor["sniper_silver_bullets"] = max(0, sniper_actor.get("sniper_silver_bullets", 0) - 1)
            else:
                sniper_actor["sniper_danger_bullets"] = max(0, sniper_actor.get("sniper_danger_bullets", 0) - 1)
        else:
            sniper_actor["sniper_nights_held"] = sniper_actor.get("sniper_nights_held", 0) + 1
            if sniper_actor["sniper_nights_held"] >= 2:
                sniper_actor["sniper_silver_bullets"] = sniper_actor.get("sniper_silver_bullets", 0) + 1
                sniper_actor["sniper_nights_held"] = 0
                log_event(state, f"🎯 {sniper_actor['name']} held fire for 2 rounds and earned a safe Silver Bullet!")

    # Bodyguard Interceptions against Wolf and SK:
    if bg_active:
        if wolf_attack == bg_target:
            to_save.add(bg_target)
            to_kill.add(bg_actor["id"])
            log_event(state, f"🛡️ Bodyguard intercepted werewolf attack on {state['players'][bg_target]['name']}!")
            wolf_attack = None
        if sk_attack == bg_target:
            to_save.add(bg_target)
            to_kill.add(bg_actor["id"])
            log_event(state, f"🛡️ Bodyguard intercepted Serial Killer attack on {state['players'][bg_target]['name']}!")
            sk_attack = None

    if wolf_attack and wolf_attack not in to_save:
        to_kill.add(wolf_attack)
    if sk_attack and sk_attack not in to_save:
        to_kill.add(sk_attack)

    # Vigilante / Sniper Shot Resolution:
    if (
        sniper_actor
        and sniper_actor["id"] not in suppressed_pids
        and sniper_target
        and sniper_target in state["players"]
    ):
        s_target_player = state["players"][sniper_target]
        target_is_evil = is_evil_faction_or_threat(s_target_player)

        if bg_active and bg_target == sniper_target:
            if target_is_evil:
                # Bodyguard shields evil target from Vigilante and dies; evil survives
                to_kill.add(bg_actor["id"])
                to_save.add(sniper_target)
                log_event(state, f"🛡️ Bodyguard shielded evil target {s_target_player['name']} from Vigilante and died!")
            else:
                # Bodyguard was protecting innocent. Danger bullet backfires; both target & bodyguard survive
                if sniper_bullet_type == "danger":
                    to_kill.add(sniper_actor["id"])
                    log_event(
                        state,
                        "🎯 Vigilante shot innocent protected by Bodyguard! Gun backfired and shooter died of guilt.",
                    )
        else:
            if target_is_evil:
                if sniper_target not in to_save:
                    to_kill.add(sniper_target)
                    log_event(state, f"🎯 Vigilante eliminated evil threat {s_target_player['name']}!")
            else:
                if sniper_bullet_type == "danger":
                    # Danger bullet backfires into shooter! Innocent target is unharmed.
                    to_kill.add(sniper_actor["id"])
                    log_event(
                        state,
                        f"🎯 Vigilante shot innocent {s_target_player['name']}! Gun backfired and shooter died of guilt (target survives unharmed).",
                    )
                else:
                    log_event(
                        state,
                        f"🎯 Vigilante shot innocent {s_target_player['name']} with safe Silver Bullet. No harm done.",
                    )

    # --- 8. Wolf Hunter Strike ---
    wh_actor = next(
        (p for p in state["players"].values() if p["role"] == "wolf_hunter" and p["status"] == "alive"),
        None,
    )
    wh_target = actions.get("wolf_hunter_target")
    if (
        wh_actor
        and wh_actor["id"] not in suppressed_pids
        and wh_target
        and wh_target in state["players"]
    ):
        t_player = state["players"][wh_target]
        if t_player.get("faction") == FACTION_WOLVES:
            if wh_target not in to_save:
                to_kill.add(wh_target)
            log_event(state, f"🏹 Wolf Hunter eliminated Werewolf threat {t_player['name']}!")
        else:
            # Shot innocent / non-wolf -> Hunter dies!
            to_kill.add(wh_actor["id"])
            log_event(
                state,
                f"🏹 Wolf Hunter shot non-wolf {t_player['name']}! Gun backfired and hunter died of guilt (target survives unharmed).",
            )

    # --- 9. Death Angel Strike (Targets soul in Limbo) ---
    da_actor = next(
        (
            p
            for p in state["players"].values()
            if p["role"] == "death_angel" and p["status"] in ("alive", "limbo")
        ),
        None,
    )
    da_target = actions.get("death_angel_target")
    if (
        da_actor
        and da_actor["id"] not in suppressed_pids
        and da_target
        and da_target in state["players"]
        and not state.get("death_angel_used", False)
    ):
        if state["players"][da_target]["status"] == "limbo":
            state["death_angel_used"] = True
            set_player_status(state, da_target, "dead")
            t_name = state["players"][da_target]["name"]
            reveal_suffix = (
                f" [{state['players'][da_target].get('death_reveal')}]"
                if state["players"][da_target].get("death_reveal")
                else ""
            )
            report.append(
                f"👼🗡️ Death Angel struck {t_name} in Limbo, severing their earthly tether forever!{reveal_suffix}"
            )
            log_event(state, f"👼🗡️ Death Angel permanently eliminated {t_name} from Limbo.")

    # --- 10. Witch Action (Revive / Poison) ---
    witch_actor = next((p for p in state["players"].values() if p["role"] == "witch" and p["status"] == "alive"), None)
    witch_act = actions.get("witch_action", {})
    if witch_actor and witch_actor["id"] not in suppressed_pids:
        # Crucial rule: Witch can only act if alive and CANNOT self-heal if attacked tonight!
        if witch_actor["id"] in to_kill:
            log_event(state, "🧙‍♀️ Witch was attacked tonight and could not brew potions!")
        else:
            if witch_act.get("revive") and not state.get("witch_used_revive", False):
                w_victim = actions.get("wolf_target")
                if w_victim and w_victim in to_kill:
                    to_kill.remove(w_victim)
                    state["witch_used_revive"] = True
                    log_event(state, f"🧙‍♀️ Witch used revival potion to save {state['players'][w_victim]['name']}!")
            if witch_act.get("kill_target") and not state.get("witch_used_kill", False):
                w_poison = witch_act["kill_target"]
                if w_poison in state["players"]:
                    to_kill.add(w_poison)
                    state["witch_used_kill"] = True
                    log_event(state, f"🧙‍♀️ Witch used poison on {state['players'][w_poison]['name']}!")

    # --- 11. Silencer (Staggered Rule) ---
    silencer_actor = next(
        (p for p in state["players"].values() if p["role"] == "silencer" and p["status"] == "alive"), None
    )
    silencer_target = actions.get("silencer_target")
    for p in state["players"].values():
        p["is_silenced"] = False
    if silencer_actor and silencer_actor["id"] not in suppressed_pids and silencer_target in state["players"]:
        last_silenced = state.get("last_silenced_id")
        if silencer_target != last_silenced:
            state["players"][silencer_target]["is_silenced"] = True
            state["last_silenced_id"] = silencer_target
            report.append(
                f"🤐 {state['players'][silencer_target]['name']} is silenced for the day (cannot speak, but can still vote!)."
            )

    # --- 12. Town Ghost Haunt & Spectral Messages ---
    ghost_haunt = actions.get("ghost_haunt")
    if ghost_haunt and ghost_haunt in state["players"]:
        state["players"][ghost_haunt]["haunted_by"] = "ghost"

    appr_ghost_msgs = state.get("approved_ghost_messages", [])
    if appr_ghost_msgs:
        for gm in appr_ghost_msgs:
            report.append(f'👻 Spectral Message from beyond: "{gm["message"]}"')
        state["approved_ghost_messages"] = []

    # --- 13. Mayor Veto (Once Per Person!) ---
    mayor_actor = next((p for p in state["players"].values() if p["role"] == "mayor" and p["status"] == "alive"), None)
    if (
        actions.get("mayor_veto")
        and mayor_actor
        and mayor_actor["id"] not in suppressed_pids
        and state.get("last_lynched_id")
    ):
        lynched_id = state["last_lynched_id"]
        vetoed_ids = state.setdefault("mayor_vetoed_ids", [])
        if lynched_id in state["players"] and lynched_id not in vetoed_ids:
            vetoed_ids.append(lynched_id)
            state["mayor_used_veto"] = True
            set_player_status(state, lynched_id, "alive")
            p_name = state["players"][lynched_id]["name"]
            report.append(f"📜 The Mayor exercised official veto! {p_name} was pardoned and returned alive!")
            lover_id = state["players"][lynched_id].get("lover_id")
            if lover_id and lover_id in state["players"]:
                set_player_status(state, lover_id, "alive")
                report.append(f"❤️ {state['players'][lover_id]['name']} was revived as their lover returned to life!")

    # --- 14. Casualties & Limbo (Concealed Angel Death) ---
    limbo_on = state["settings"].get("limbo_enabled", True)
    has_living_angel = any(p["role"] == "angel" and p["status"] == "alive" for p in state["players"].values())

    killed_players: set[str] = set()
    for pid in to_kill:
        p = state["players"][pid]
        if limbo_on and has_living_angel and not p["used_limbo"]:
            set_player_status(state, pid, "limbo")
            report.append(
                f"🌫️ {p['name']} fell during the night, but hovers in Limbo with one chance to guess the Angel!"
            )
        else:
            set_player_status(state, pid, "dead")
            killed_players.add(pid)
            reveal_suffix = f" [{p.get('death_reveal')}]" if p.get("death_reveal") else ""
            report.append(f"🪦 {p['name']} was slain in the night.{reveal_suffix}")

    # Check Limbo souls when Angel is dead:
    if not has_living_angel:
        for p in list(state["players"].values()):
            if p["status"] == "limbo":
                set_player_status(state, p["id"], "dead")
                reveal_suffix = f" [{p.get('death_reveal')}]" if p.get("death_reveal") else ""
                report.append(
                    f"🌫️ With the Angel absent, {p['name']}'s spirit passed from Limbo into eternal death.{reveal_suffix}"
                )

    for pid in list(killed_players):
        p = state["players"][pid]
        lover_id = p.get("lover_id")
        if lover_id and lover_id in state["players"] and lover_id not in killed_players:
            lover = state["players"][lover_id]
            # Check if successor inherits the deceased's role!
            succ_msg = check_and_trigger_successor_inheritance(state, pid)
            if not succ_msg:
                set_player_status(state, lover_id, "dead")
                killed_players.add(lover_id)
                reveal_suffix = f" [{lover.get('death_reveal')}]" if lover.get("death_reveal") else ""
                if state.get("settings", {}).get("public_heartbreak_cause", False):
                    report.append(
                        f"💔 {lover['name']} died of a broken heart following their lover {p['name']}!{reveal_suffix}"
                    )
                else:
                    report.append(f"🪦 {lover['name']} was slain in the night.{reveal_suffix}")
            else:
                report.append(succ_msg)

    # Check pending heartbreak (from yesterday's day vote execution)
    for p in list(state["players"].values()):
        if p.get("status") == "alive" and p.get("pending_heartbreak"):
            # Check if successor saved them
            if p.get("lover_id") and state["players"].get(p["lover_id"], {}).get("status") == "alive":
                p["pending_heartbreak"] = False
            else:
                p["status"] = "dead"
                p["used_limbo"] = True
                p["pending_heartbreak"] = False
                killed_players.add(p["id"])
                if state.get("settings", {}).get("public_heartbreak_cause", False):
                    lover_name = p.get("pending_heartbreak_lover_name", "their lover")
                    report.append(f"💔 {p['name']} died of a broken heart over their fallen lover {lover_name}!")
                else:
                    report.append(f"🪦 {p['name']} was found dead at dawn.")

    # Gazette / News Bulletins
    appr_bulletins = state.get("approved_news_bulletins", [])
    for b in appr_bulletins:
        byline = "Anonymous Informant" if b.get("anonymous") else b.get("player_name", "Villager")
        report.append(f'🗞️ Gazette: {byline} writes: "{b["message"]}"')

    if not to_kill:
        report.append("☀️ Dawn breaks over a peaceful night. No one died!")

    state["night_report"] = report
    state["night_actions"] = {}
    state["night_stage_index"] = 0
    state["revealed_inspect"] = None
    state["voting"] = _reset_voting_state(state)
    state["phase"] = "day_discussion"

    start_timer(state, state["settings"].get("discussion_timer", 300), "Discussion")
    check_win_condition(state)
    save_game(state["code"], state)
    return state


# --- Day Voting & Trial Engine ---


def get_living_players(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in state.get("players", {}).values() if p.get("status") == "alive"]


def get_nomination_threshold(state: dict[str, Any]) -> int:
    """Calculate votes needed to secure an official nomination (default 50% of living players)."""
    living = get_living_players(state)
    count = len(living)
    if count == 0:
        return 1
    pct = state.get("settings", {}).get("nomination_threshold_pct", 50)
    return max(1, math.ceil(count * (pct / 100.0)))


def start_voting_session(state: dict[str, Any], system: Optional[str] = None) -> dict[str, Any]:
    """Initiate day voting. Blocks Day 0 voting and Day 1 voting if Hacker Intel announcement was active."""
    if state.get("is_day_zero", False):
        log_event(state, "🚫 Day 0 voting blocked: Introductions and suspicions only.")
        return state

    if state.get("day1_no_voting") and state.get("round_number", 1) <= 1:
        log_event(state, "🚫 Day 1 voting blocked: Introductions and suspicions only per Hacker Intel.")
        return state

    voting_system = system or state.get("settings", {}).get("voting_system", "two_stage_50pct")
    initial_stage = "final_vote" if voting_system == "simple_plurality" else "nomination"
    living_ids = [p["id"] for p in get_living_players(state)] if voting_system == "simple_plurality" else []

    state["phase"] = "day_voting"
    state["voting"] = {
        "stage": initial_stage,
        "system": voting_system,
        "nomination_votes": {},
        "nominated_player_ids": living_ids,
        "final_votes": {},
        "tie_count": 0,
        "revote_candidates": [],
        "defense_player_id": None,
        "eliminated_player_id": None,
        "elimination_result": None,
        "ballot_locked": False,
    }
    log_event(state, f"🗳️ Voting session opened! System: {voting_system}. Stage: {initial_stage}.")
    save_game(state["code"], state)
    return state


def toggle_nomination_vote(state: dict[str, Any], voter_id: str, candidate_id: str) -> tuple[bool, str]:
    """A voter toggles their hand for a candidate during nomination (multi-vote allowed).
    Silenced players CAN vote. Limbo players CANNOT vote.
    """
    voting = state.setdefault("voting", {})
    if voting.get("stage") != "nomination":
        return False, "Not in nomination phase."

    players = state.get("players", {})
    if candidate_id not in players or players[candidate_id]["status"] != "alive":
        return False, "Candidate must be alive."

    if voter_id not in players or players[voter_id]["status"] != "alive":
        return False, "Only living players can vote."

    votes_map = voting.setdefault("nomination_votes", {})
    voters = set(votes_map.get(candidate_id, []))
    if voter_id in voters:
        voters.remove(voter_id)
        msg = f"Removed nomination vote for {players[candidate_id]['name']}."
    else:
        voters.add(voter_id)
        msg = f"Added nomination vote for {players[candidate_id]['name']}."

    votes_map[candidate_id] = list(voters)
    update_nominated_candidates(state)
    save_game(state["code"], state)
    return True, msg


def set_nomination_tally_direct(state: dict[str, Any], candidate_id: str, count: int) -> bool:
    """GM directly sets hand-raise vote count for a candidate during in-person play."""
    voting = state.setdefault("voting", {})
    players = state.get("players", {})
    if candidate_id not in players:
        return False
    votes_map = voting.setdefault("nomination_votes", {})
    count = max(0, int(count))
    votes_map[candidate_id] = [f"tally_{i}" for i in range(count)]
    update_nominated_candidates(state)
    save_game(state["code"], state)
    return True


def update_nominated_candidates(state: dict[str, Any]) -> list[str]:
    """Recalculate which candidates meet the nomination criteria."""
    voting = state.get("voting", {})
    system = voting.get("system", "two_stage_50pct")
    votes_map = voting.get("nomination_votes", {})

    if system == "two_stage_50pct":
        threshold = get_nomination_threshold(state)
        nominees = [
            cid
            for cid, voters in votes_map.items()
            if sum(get_voter_weight(state, vid) for vid in voters) >= threshold
            and state["players"].get(cid, {}).get("status") == "alive"
        ]
    elif system == "two_stage_top_n":
        sorted_cands = sorted(
            [
                (cid, sum(get_voter_weight(state, vid) for vid in v))
                for cid, v in votes_map.items()
                if len(v) > 0 and state["players"].get(cid, {}).get("status") == "alive"
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        nominees = [cid for cid, _ in sorted_cands[:2]]
    else:
        nominees = [p["id"] for p in get_living_players(state)]

    voting["nominated_player_ids"] = nominees
    return nominees


def toggle_official_nomination(state: dict[str, Any], player_id: str) -> bool:
    """GM manually adds or removes a player as an official nominee."""
    voting = state.setdefault("voting", {})
    nominees = set(voting.setdefault("nominated_player_ids", []))
    if player_id in nominees:
        nominees.remove(player_id)
    else:
        nominees.add(player_id)
    voting["nominated_player_ids"] = list(nominees)
    save_game(state["code"], state)
    return True


def proceed_to_defense(state: dict[str, Any], player_id: Optional[str] = None) -> dict[str, Any]:
    """Move to defense stage for nominated players."""
    voting = state.setdefault("voting", {})
    voting["stage"] = "defense"
    voting["defense_player_id"] = player_id
    if player_id and player_id in state["players"]:
        name = state["players"][player_id]["name"]
        start_timer(state, state["settings"].get("defense_timer", 30), f"Defense: {name}")
    save_game(state["code"], state)
    return state


def return_to_nominations(state: dict[str, Any]) -> dict[str, Any]:
    """Return from defense or final vote stage back to nomination stage."""
    voting = state.setdefault("voting", {})
    voting["stage"] = "nomination"
    voting["defense_player_id"] = None
    voting["ballot_locked"] = False
    timer_duration = state.get("settings", {}).get("discussion_timer", 300)
    start_timer(state, timer_duration, "Nominations")
    log_event(state, "↩️ Returned to nominations stage.")
    save_game(state["code"], state)
    return state


def proceed_to_final_vote(state: dict[str, Any]) -> tuple[bool, str]:
    """Lock in nominees and start the final single-vote execution ballot."""
    voting = state.setdefault("voting", {})
    nominees = voting.get("nominated_player_ids", [])
    if not nominees:
        return False, "Cannot start final vote: No players were nominated!"

    voting["stage"] = "final_vote"
    voting["final_votes"] = {}
    voting["ballot_locked"] = True
    voting["tie_count"] = 0
    voting["revote_candidates"] = []
    nominee_names = [state["players"][pid]["name"] for pid in nominees if pid in state["players"]]
    log_event(state, f"⚖️ Final execution vote started for nominees: {nominee_names}.")
    save_game(state["code"], state)
    return True, "Final vote active."


def cast_final_vote(state: dict[str, Any], voter_id: str, candidate_id: Optional[str]) -> tuple[bool, str]:
    """A voter casts their vote for one of the nominated candidates (or abstains with None).
    Silenced players CAN vote. Limbo players CANNOT vote.
    """
    voting = state.setdefault("voting", {})
    stage = voting.get("stage")
    if stage not in ("final_vote", "revote"):
        return False, "Not currently in final voting or revote stage."

    players = state.get("players", {})
    voter = players.get(voter_id)
    if not voter or voter["status"] != "alive":
        return False, "Only living players can vote."

    allowed = (
        set(voting.get("revote_candidates", [])) if stage == "revote" else set(voting.get("nominated_player_ids", []))
    )

    if candidate_id is not None and candidate_id not in allowed:
        return False, "Candidate is not on the ballot."

    final_votes = voting.setdefault("final_votes", {})
    if candidate_id is None:
        final_votes.pop(voter_id, None)
        msg = f"{voter['name']} abstained."
    else:
        final_votes[voter_id] = candidate_id
        msg = f"{voter['name']} voted for {players[candidate_id]['name']}."

    save_game(state["code"], state)
    return True, msg


def record_gm_final_vote_tally(state: dict[str, Any], candidate_id: str, count: int) -> bool:
    """GM directly sets vote count for candidate in final vote (for in-person hand raises)."""
    voting = state.setdefault("voting", {})
    stage = voting.get("stage")
    if stage not in ("final_vote", "revote"):
        return False

    final_votes = voting.setdefault("final_votes", {})
    to_del = [k for k, v in final_votes.items() if v == candidate_id and str(k).startswith("gm_vote_")]
    for k in to_del:
        del final_votes[k]

    for i in range(max(0, int(count))):
        final_votes[f"gm_vote_{candidate_id}_{i}"] = candidate_id

    save_game(state["code"], state)
    return True


def tally_and_resolve_vote(state: dict[str, Any]) -> tuple[str, str]:
    """Execute the tie-breaking and elimination resolution engine!
    Tie rules:
      1. On first tie: revote exclusively among people tied.
      2. On second tie: no one gets eliminated!
    """
    voting = state.setdefault("voting", {})
    stage = voting.get("stage")
    players = state.get("players", {})
    final_votes = voting.get("final_votes", {})

    allowed = (
        set(voting.get("revote_candidates", [])) if stage == "revote" else set(voting.get("nominated_player_ids", []))
    )
    if not allowed:
        return "error", "No candidates on the ballot."

    counts = {cid: 0 for cid in allowed}
    for voter_id, cand_id in final_votes.items():
        if cand_id in counts:
            weight = get_voter_weight(state, voter_id)
            counts[cand_id] += weight

    max_votes = max(counts.values()) if counts else 0
    if max_votes == 0:
        voting["stage"] = "completed"
        voting["eliminated_player_id"] = None
        voting["elimination_result"] = "no_votes"
        msg = "☀️ No votes were cast! The town agrees on peace today."
        log_event(state, msg)
        save_game(state["code"], state)
        return "no_votes", msg

    top_candidates = [cid for cid, v in counts.items() if v == max_votes]

    # --- TIE RESOLUTION ---
    if len(top_candidates) > 1:
        tie_count = voting.get("tie_count", 0)
        tied_names = [players[cid]["name"] for cid in top_candidates if cid in players]

        if tie_count == 0:
            # FIRST TIE: Runoff revote among tied candidates!
            voting["tie_count"] = 1
            voting["stage"] = "revote"
            voting["revote_candidates"] = top_candidates
            voting["final_votes"] = {}
            joined_tied = ", ".join(tied_names)
            msg = (
                f"⚖️ TIE between {joined_tied} ({max_votes} votes each)! Runoff revote initiated among tied candidates."
            )
            log_event(state, msg)
            save_game(state["code"], state)
            return "revote", msg
        else:
            # SECOND TIE: No one gets eliminated!
            voting["stage"] = "completed"
            voting["eliminated_player_id"] = None
            voting["elimination_result"] = "spared_on_tie"
            msg = f"🕊️ SECOND TIE between {', '.join(tied_names)}! On second tie, NO ONE gets eliminated today!"
            log_event(state, msg)
            save_game(state["code"], state)
            return "spared_on_tie", msg

    # --- SINGLE WINNER: ELIMINATION / EXECUTION ---
    victim_id = top_candidates[0]
    victim = players[victim_id]
    state["last_lynched_id"] = victim_id
    voting["eliminated_player_id"] = victim_id

    # Check PUBLIC MAYOR IMMUNITY: Public Mayor cannot be voted out!
    is_public_mayor = victim.get("role") == "mayor" and (
        victim.get("is_public_mayor", False)
        or state.get("settings", {}).get("mayor_type") == "public"
        or state.get("settings", {}).get("public_mayor", False)
    )
    if is_public_mayor:
        voting["stage"] = "completed"
        voting["eliminated_player_id"] = None
        voting["elimination_result"] = "mayor_immune"
        state["last_lynched_id"] = None
        msg = (
            f"🎖️ {victim['name']} received {max_votes} votes, but holds executive immunity as Public Mayor "
            f"and cannot be voted out by the town!"
        )
        log_event(state, msg)
        check_win_condition(state)
        save_game(state["code"], state)
        return "mayor_immune", msg

    # Check JESTER instant win!
    if victim.get("role") == "jester":
        state["pending_gameover"] = {
            "winner": "jester",
            "reason": f"The Jester ({victim['name']}) was executed by town vote and won SOLO VICTORY!",
            "faction_name": "Jester",
        }
        voting["stage"] = "completed"
        voting["elimination_result"] = "jester_win"
        set_player_status(state, victim_id, "dead")
        msg = f"🃏 The Jester ({victim['name']}) was executed by town vote and won SOLO VICTORY!"
        log_event(state, msg)
        save_game(state["code"], state)
        return "jester_win", msg

    # Check Limbo vs Dead (Players can only go to Limbo ONCE; on second vote straight to dead)
    limbo_on = state.get("settings", {}).get("limbo_enabled", True)
    has_living_angel = any(p["role"] == "angel" and p["status"] == "alive" for p in players.values())

    if limbo_on and has_living_angel and not victim["used_limbo"]:
        set_player_status(state, victim_id, "limbo")
        voting["elimination_result"] = "limbo"
        msg = f"🌫️ {victim['name']} received {max_votes} votes and was banished to Limbo (can guess Angel to return)!"
    else:
        lover_id = victim.get("lover_id")
        lover_broken_heart_msg = ""
        if lover_id and lover_id in players and players[lover_id]["status"] == "alive":
            lover = players[lover_id]
            lover_broken_heart_msg = f" (💔 {lover['name']} is stricken with grief and will succumb to heartbreak at dawn unless saved!)"

        set_player_status(state, victim_id, "dead", stagger_lover_heartbreak=True)
        voting["elimination_result"] = "dead"
        msg = f"🪦 {victim['name']} received {max_votes} votes and was executed by town vote!{lover_broken_heart_msg}"

    voting["stage"] = "completed"
    log_event(state, msg)
    check_win_condition(state)
    save_game(state["code"], state)
    return "eliminated", msg


def reset_voting(state: dict[str, Any]) -> dict[str, Any]:
    state["voting"] = _reset_voting_state(state)
    save_game(state["code"], state)
    return state


def get_voting_view(state: dict[str, Any], is_gm: bool = False, player_id: Optional[str] = None) -> dict[str, Any]:
    voting = state.get("voting", {})
    stage = voting.get("stage", "none")
    system = voting.get("system", state.get("settings", {}).get("voting_system", "two_stage_50pct"))
    threshold = get_nomination_threshold(state)
    living = get_living_players(state)
    ordered = get_ordered_players(state)

    nom_votes = voting.get("nomination_votes", {})
    official_nominees = set(voting.get("nominated_player_ids", []))
    final_votes = voting.get("final_votes", {})
    revote_cands = set(voting.get("revote_candidates", []))

    nomination_candidates = []
    for idx, p in enumerate(ordered):
        if p["status"] == "alive":
            pid = p["id"]
            v_list = nom_votes.get(pid, [])
            vote_weight_total = sum(get_voter_weight(state, vid) for vid in v_list)
            nomination_candidates.append(
                {
                    "id": pid,
                    "seat_number": idx + 1,
                    "name": p["name"],
                    "vote_count": vote_weight_total,
                    "is_nominated": pid in official_nominees,
                    "has_my_vote": player_id in v_list if player_id else False,
                }
            )

    allowed_ids = revote_cands if stage == "revote" else official_nominees
    final_candidates = []
    for idx, p in enumerate(ordered):
        pid = p["id"]
        if pid in allowed_ids and p["status"] == "alive":
            vote_weight_total = sum(get_voter_weight(state, vid) for vid, cid in final_votes.items() if cid == pid)
            final_candidates.append(
                {
                    "id": pid,
                    "seat_number": idx + 1,
                    "name": p["name"],
                    "vote_count": vote_weight_total,
                }
            )

    my_vote = final_votes.get(player_id) if player_id else None
    eliminated_name = None
    if voting.get("eliminated_player_id"):
        eliminated_name = state.get("players", {}).get(voting["eliminated_player_id"], {}).get("name")

    return {
        "stage": stage,
        "system": system,
        "threshold_votes": threshold,
        "living_count": len(living),
        "nomination_candidates": nomination_candidates,
        "official_nominee_ids": list(official_nominees),
        "final_candidates": final_candidates,
        "tie_count": voting.get("tie_count", 0),
        "is_revote": stage == "revote",
        "my_vote": my_vote,
        "defense_player_id": voting.get("defense_player_id"),
        "defense_player_name": state.get("players", {}).get(voting.get("defense_player_id"), {}).get("name"),
        "eliminated_player_id": voting.get("eliminated_player_id"),
        "eliminated_player_name": eliminated_name,
        "elimination_result": voting.get("elimination_result"),
        "ballot_locked": voting.get("ballot_locked", False),
    }


# --- Win Conditions ---


def check_win_condition(state: dict[str, Any]) -> Optional[str]:
    """Check if Town, Wolves, Lovers, Jester, or Serial Killer have achieved victory.
    Stores a pending_gameover record for the Game Master to trigger.
    """
    if state.get("phase") == "gameover":
        return state.get("winner")

    if state.get("pending_gameover"):
        return state["pending_gameover"].get("winner")

    if state.get("pending_gameover_dismissed"):
        return None

    alive_players = [p for p in state["players"].values() if p["status"] == "alive"]
    if not alive_players:
        state["pending_gameover"] = {
            "winner": "tie",
            "reason": "All players have perished. Nobody survived.",
            "faction_name": "Nobody (Tie)",
        }
        return "tie"

    # Check Obsessive Lovers win (only win if they are the last 2 players alive)
    if len(alive_players) == 2:
        p1, p2 = alive_players[0], alive_players[1]
        if p1.get("lover_id") == p2["id"] and p1.get("lover_type") == "obsessive":
            state["pending_gameover"] = {
                "winner": "lovers",
                "reason": f"Love conquers all! Obsessive Lovers {p1['name']} and {p2['name']} are the last survivors!",
                "faction_name": "The Lovers",
            }
            return "lovers"

    wolves_count = sum(1 for p in alive_players if p["faction"] == FACTION_WOLVES)
    sk_count = sum(1 for p in alive_players if p.get("role") == "serial_killer")

    # Serial Killer solo victory:
    # "if all wolfs die and they don't they win, we don't need to go through more day night cycles"
    if sk_count > 0 and wolves_count == 0:
        sk_player = next(p for p in alive_players if p.get("role") == "serial_killer")
        state["pending_gameover"] = {
            "winner": "serial_killer",
            "reason": f"All Werewolves have perished! The Serial Killer ({sk_player['name']}) claims instant solo victory!",
            "faction_name": "Serial Killer",
        }
        return "serial_killer"

    if wolves_count == 0 and sk_count == 0:
        theme = state.get("theme", "werewolf")
        faction_name = "Villagers" if theme == "werewolf" else "Civilians"
        state["pending_gameover"] = {
            "winner": "town",
            "reason": f"Victory for the {faction_name}! All evil threats have been vanquished.",
            "faction_name": faction_name,
        }
        return "town"

    if wolves_count >= (len(alive_players) - wolves_count):
        theme = state.get("theme", "werewolf")
        faction_name = "Werewolves" if theme == "werewolf" else "Mafia"
        state["pending_gameover"] = {
            "winner": "wolves",
            "reason": f"Victory for the {faction_name}! They have overrun the town.",
            "faction_name": faction_name,
        }
        return "wolves"

    state["pending_gameover"] = None
    return None


def trigger_game_over(state: dict[str, Any], winner: Optional[str] = None) -> dict[str, Any]:
    """Host explicitly triggers the gameover state and announces winners."""
    if not winner:
        pending = state.get("pending_gameover")
        if pending and pending.get("winner"):
            winner = pending["winner"]
        else:
            winner = check_win_condition(state) or "town"

    state["winner"] = winner
    state["phase"] = "gameover"
    state["pending_gameover"] = None
    state["pending_gameover_dismissed"] = False

    theme = state.get("theme", "werewolf")
    if winner == "town":
        faction_name = "Villagers" if theme == "werewolf" else "Civilians"
        msg = f"🏆 GAME OVER! Victory for the {faction_name}!"
    elif winner == "wolves":
        faction_name = "Werewolves" if theme == "werewolf" else "Mafia"
        msg = f"🐺 GAME OVER! Victory for the {faction_name}!"
    elif winner == "lovers":
        msg = "💘 GAME OVER! Love conquers all! The Lovers have won!"
    elif winner == "jester":
        msg = "🃏 GAME OVER! The Jester tricked everyone and claimed solo victory!"
    elif winner == "serial_killer":
        msg = "🔪 GAME OVER! The Serial Killer claimed solo victory!"
    elif winner == "tie":
        msg = "💀 GAME OVER! It is a tie - all souls have perished!"
    else:
        msg = f"🏁 GAME OVER! Winner: {winner.title()}"

    log_event(state, msg)
    save_game(state["code"], state)
    return state


def dismiss_pending_gameover(state: dict[str, Any]) -> dict[str, Any]:
    """Host dismisses or defers the victory condition alert to continue playing."""
    state["pending_gameover"] = None
    state["pending_gameover_dismissed"] = True
    save_game(state["code"], state)
    return state


# --- Sanitized Views for Clients ---


def get_sanitized_player_view(state: dict[str, Any], player_id: str) -> dict[str, Any]:
    """Client view for a specific player: hides secret GM data and others' secret roles."""
    player = state["players"].get(player_id)
    if not player:
        return {}

    theme = state.get("theme", "werewolf")
    is_wolf = player["faction"] == FACTION_WOLVES
    lover_id = player.get("lover_id")

    is_gameover = state.get("phase") == "gameover"
    ordered_players = get_ordered_players(state)
    public_players = []
    for idx, p in enumerate(ordered_players):
        pid = p["id"]
        p_role = get_role_info(p["role"], theme) if (is_gameover and p.get("role")) else None
        is_public_mayor = p.get("role") == "mayor" and (
            p.get("is_public_mayor", False)
            or state.get("settings", {}).get("mayor_type") == "public"
            or state.get("settings", {}).get("public_mayor", False)
        )
        public_players.append(
            {
                "id": p["id"],
                "seat_number": idx + 1,
                "name": p["name"],
                "status": p["status"],
                "is_silenced": p["is_silenced"],
                "is_traveler": p.get("is_traveler", False) or p.get("role") == "traveler",
                "is_ghost": p.get("is_ghost", False) or p.get("role") == "ghost",
                "is_public_mayor": is_public_mayor,
                "is_me": pid == player_id,
                "is_lover": pid == lover_id,
                "is_pack_mate": is_wolf and p["faction"] == FACTION_WOLVES and pid != player_id,
                "death_reveal": p.get("death_reveal") if p["status"] == "dead" else None,
                "point_target_id": state.get("player_points", {}).get(pid),
                "role": p_role,
            }
        )

    my_role_info = get_role_info(player["role"], theme) if player.get("role") else None

    revealed_inspect = None
    if player.get("role") == "detective":
        revealed_inspect = state.get("revealed_inspect")

    # Watson view: knows who the Detective is
    watson_detective_name = None
    watson_detective_id = None
    if player.get("role") == "watson":
        det = next((p for p in state["players"].values() if p.get("role") == "detective"), None)
        if det:
            watson_detective_name = det["name"]
            watson_detective_id = det["id"]

    # Saboteur stolen role view for wolves
    stolen_role_info = None
    if is_wolf and state.get("night_actions", {}).get("saboteur_stolen_role"):
        stolen_role_info = get_role_info(state["night_actions"]["saboteur_stolen_role"], theme)

    cannot_speak = (player["status"] == "limbo") or player.get("is_silenced", False)

    night_stage_title = None
    if state.get("phase") == "night":
        stages = get_night_stages(state)
        idx = state.get("night_stage_index", 0)
        if 0 <= idx < len(stages):
            night_stage_title = stages[idx]["title"]

    timer_data = dict(state["timer"])
    if not timer_data["paused"] and timer_data["ends_at"]:
        timer_data["remaining"] = max(0, int(timer_data["ends_at"] - time.time()))

    deck_role_ids = list(state.get("deck", []))
    if not deck_role_ids:
        for p in state.get("players", {}).values():
            if p.get("role"):
                deck_role_ids.append(p["role"])

    roles_in_play = []
    seen_roles = set()
    for rid in deck_role_ids:
        if rid not in seen_roles and rid in ROLE_REGISTRY and ROLE_REGISTRY[rid].get("enabled", True):
            seen_roles.add(rid)
            r_info = get_role_info(rid, theme)
            roles_in_play.append(
                {
                    "id": rid,
                    "name": r_info["name"],
                    "emoji": r_info["emoji"],
                    "faction": r_info["faction"],
                }
            )

    cur_rnd = state.get("round_number", 1)
    if player["status"] == "alive":
        can_submit_news = player.get("last_news_post_round") != cur_rnd
        news_submitted_this_round = player.get("last_news_post_round") == cur_rnd
    elif player["status"] in ("dead", "limbo"):
        can_submit_news = not player.get("used_dead_news_bulletin", False)
        news_submitted_this_round = player.get("used_dead_news_bulletin", False)
    else:
        can_submit_news = False
        news_submitted_this_round = False

    published_news = [
        {
            "id": b["id"],
            "byline": "Anonymous Informant" if b.get("anonymous") else b.get("player_name", "Villager"),
            "message": b["message"],
            "round": b.get("round", 1),
        }
        for b in state.get("approved_news_bulletins", [])
    ]

    return {
        "code": state["code"],
        "title": state["title"],
        "theme": theme,
        "phase": state["phase"],
        "round_number": state["round_number"],
        "me": {
            "id": player["id"],
            "name": player["name"],
            "status": player["status"],
            "is_silenced": player["is_silenced"],
            "cannot_speak": cannot_speak,
            "used_limbo": player["used_limbo"],
            "role": my_role_info,
            "lover_name": state["players"][lover_id]["name"] if lover_id and lover_id in state["players"] else None,
            "lover_type": player.get("lover_type"),
            "watson_detective_name": watson_detective_name,
            "watson_detective_id": watson_detective_id,
            "is_traveler": player.get("is_traveler", False) or player.get("role") == "traveler",
            "is_ghost": player.get("is_ghost", False) or player.get("role") == "ghost",
            "is_successor": player.get("is_successor", False) or player.get("role") == "successor",
            "pending_heartbreak": player.get("pending_heartbreak", False),
            "can_submit_news": can_submit_news,
            "news_submitted_this_round": news_submitted_this_round,
            "sniper_danger_bullets": player.get("sniper_danger_bullets", 0),
            "sniper_silver_bullets": player.get("sniper_silver_bullets", 0),
            "death_angel_strikes": player.get("death_angel_strikes", 0),
            "is_public_mayor": player.get("role") == "mayor" and (
                player.get("is_public_mayor", False)
                or state.get("settings", {}).get("mayor_type") == "public"
                or state.get("settings", {}).get("public_mayor", False)
            ),
        },
        "players": public_players,
        "roles_in_play": roles_in_play,
        "player_points": state.get("player_points", {}),
        "my_point_target_id": state.get("player_points", {}).get(player_id),
        "timer": timer_data,
        "night_stage_title": night_stage_title,
        "revealed_inspect": revealed_inspect,
        "saboteur_stolen_role": stolen_role_info,
        "hacker_result": state.get("hacker_result"),
        "day1_no_voting": state.get("day1_no_voting", False),
        "voting": get_voting_view(state, is_gm=False, player_id=player_id),
        "night_report": state.get("night_report", []),
        "news_bulletins": published_news,
        "winner": state.get("winner"),
        "broadcast_message": state.get("broadcast_message"),
        "settings": {
            "limbo_enabled": state["settings"].get("limbo_enabled", True),
            "voting_system": state["settings"].get("voting_system", "two_stage_50pct"),
            "mayor_type": state["settings"].get(
                "mayor_type", "public" if state["settings"].get("public_mayor", False) else "hidden"
            ),
            "public_mayor": state["settings"].get("public_mayor", False),
            "sniper_danger_bullets": state["settings"].get("sniper_danger_bullets", 1),
            "sniper_silver_bullets": state["settings"].get("sniper_silver_bullets", 0),
            "public_heartbreak_cause": state["settings"].get("public_heartbreak_cause", False),
            "reveal_roles_on_death": state["settings"].get("reveal_roles_on_death", 0),
        },
        "app_version": get_version_info()["display"],
        "commit_hash": get_version_info()["commit"],
    }


def get_gm_view(state: dict[str, Any]) -> dict[str, Any]:
    """Complete, unrestricted view for the Game Master cockpit."""
    theme = state.get("theme", "werewolf")

    ordered_players = get_ordered_players(state)
    all_players = []
    for idx, p in enumerate(ordered_players):
        lover_name = state["players"][p["lover_id"]]["name"] if p.get("lover_id") in state["players"] else None
        role_info = get_role_info(p["role"], theme) if p.get("role") else None
        if not role_info and p.get("preassigned_role"):
            role_info = get_role_info(p["preassigned_role"], theme)
        all_players.append(
            {
                "id": p["id"],
                "seat_number": idx + 1,
                "name": p["name"],
                "token": p["token"],
                "status": p["status"],
                "role": role_info,
                "preassigned_role": p.get("preassigned_role"),
                "is_silenced": p["is_silenced"],
                "is_suppressed": p.get("is_suppressed", False),
                "is_traveler": p.get("is_traveler", False) or p.get("role") == "traveler",
                "is_ghost": p.get("is_ghost", False) or p.get("role") == "ghost",
                "is_successor": p.get("is_successor", False) or p.get("role") == "successor",
                "pending_heartbreak": p.get("pending_heartbreak", False),
                "is_offline": p["is_offline"],
                "used_limbo": p["used_limbo"],
                "lover_name": lover_name,
                "lover_type": p.get("lover_type"),
                "last_guarded_id": p.get("last_guarded_id"),
                "death_reveal": p.get("death_reveal") if p["status"] == "dead" else None,
                "sniper_danger_bullets": p.get("sniper_danger_bullets", 0),
                "sniper_silver_bullets": p.get("sniper_silver_bullets", 0),
                "death_angel_strikes": p.get("death_angel_strikes", 0),
                "is_public_mayor": p.get("role") == "mayor" and (
                    p.get("is_public_mayor", False)
                    or state.get("settings", {}).get("mayor_type") == "public"
                    or state.get("settings", {}).get("public_mayor", False)
                ),
                "point_target_id": state.get("player_points", {}).get(p["id"]),
            }
        )

    timer_data = dict(state["timer"])
    if not timer_data["paused"] and timer_data["ends_at"]:
        timer_data["remaining"] = max(0, int(timer_data["ends_at"] - time.time()))

    return {
        "code": state["code"],
        "title": state["title"],
        "password": state.get("password", ""),
        "gm_token": state.get("gm_token", ""),
        "theme": theme,
        "phase": state["phase"],
        "round_number": state["round_number"],
        "players": all_players,
        "player_points": state.get("player_points", {}),
        "death_angel_used": state.get("death_angel_used", False),
        "deck": [get_role_info(r, theme) for r in state.get("deck", [])],
        "raw_deck": state.get("deck", []),
        "available_roles": get_all_roles_catalogue(theme, include_midgame=True),
        "player_count": len(all_players),
        "timer": timer_data,
        "night_stages": get_night_stages(state),
        "night_stage_index": state.get("night_stage_index", 0),
        "revealed_inspect": state.get("revealed_inspect"),
        "voting": get_voting_view(state, is_gm=True),
        "night_actions": state.get("night_actions", {}),
        "night_report": state.get("night_report", []),
        "events_log": state.get("events_log", [])[-25:],
        "settings": state.get("settings", {}),
        "winner": state.get("winner"),
        "pending_gameover": state.get("pending_gameover"),
        "broadcast_message": state.get("broadcast_message"),
        "witch_used_revive": state.get("witch_used_revive", False),
        "witch_used_kill": state.get("witch_used_kill", False),
        "mayor_used_veto": state.get("mayor_used_veto", False),
        "mayor_vetoed_ids": state.get("mayor_vetoed_ids", []),
        "saboteur_used": state.get("saboteur_used", False),
        "hacker_result": state.get("hacker_result"),
        "day1_no_voting": state.get("day1_no_voting", False),
        "ghost_messages": state.get("ghost_messages", []),
        "approved_ghost_messages": state.get("approved_ghost_messages", []),
        "news_bulletins": state.get("news_bulletins", []),
        "approved_news_bulletins": state.get("approved_news_bulletins", []),
        "app_version": get_version_info()["display"],
        "commit_hash": get_version_info()["commit"],
    }

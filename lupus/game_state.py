"""Lupus game state management with Redis backend and robust rule engine."""

import json
import os
import random
import time
import uuid
from typing import Any, Optional

import redis

from .roles import (
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
        "reveal_roles_on_death": True,
        "voting_system": "two_stage_50pct",  # "two_stage_50pct", "two_stage_top_n", "simple_plurality"
        "nomination_threshold_pct": 50,  # 50% of living players needed for nomination
    }
    if settings:
        default_settings.update(settings)

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
        "revealed_inspect": None,
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
        "last_lynched_id": None,
        "defense_player_id": None,
        "events_log": [],
        "night_report": [],
        "winner": None,
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
        "is_offline": is_offline,
        "connected": True,
        "channel_name": None,
        "lover_id": None,
        "last_guarded_id": None,
        "sniper_danger_bullets": 1,
        "sniper_silver_bullets": 1 if state["settings"].get("sniper_bullet_type") == "mix" else 0,
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


# --- Role Dealing ---


def set_deck(state: dict[str, Any], role_list: list[str]) -> dict[str, Any]:
    state["deck"] = list(role_list)
    save_game(state["code"], state)
    return state


def deal_roles(state: dict[str, Any], role_list: Optional[list[str]] = None) -> dict[str, Any]:
    """Distribute roles randomly to all registered players."""
    deck = list(role_list) if role_list is not None else list(state.get("deck", []))
    player_ids = list(state["players"].keys())

    # If deck count differs from player count, pad or trim with villagers
    if len(deck) < len(player_ids):
        deck.extend(["villager"] * (len(player_ids) - len(deck)))
    elif len(deck) > len(player_ids):
        deck = deck[: len(player_ids)]

    random.shuffle(deck)
    random.shuffle(player_ids)

    for pid, role_id in zip(player_ids, deck):
        role_info = ROLE_REGISTRY.get(role_id, ROLE_REGISTRY["villager"])
        state["players"][pid]["role"] = role_id
        state["players"][pid]["faction"] = role_info["faction"]
        state["players"][pid]["status"] = "alive"
        state["players"][pid]["used_limbo"] = False
        state["players"][pid]["is_silenced"] = False
        state["players"][pid]["lover_id"] = None

    state["deck"] = deck
    log_event(state, f"Distributed {len(deck)} roles to players.")
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
    """Transition from Pre-Game Lobby to Night 1, dealing roles to all joined players."""
    deal_roles(state, role_list)
    state["phase"] = "night"
    state["round_number"] = 1
    state["night_actions"] = {}
    state["night_report"] = []
    state["night_stage_index"] = 0
    state["revealed_inspect"] = None
    state["voting"] = _reset_voting_state(state)
    state["defense_player_id"] = None
    state["winner"] = None
    state["witch_used_revive"] = False
    state["witch_used_kill"] = False
    state["mayor_used_veto"] = False
    reset_timer(state, state["settings"].get("discussion_timer", 300))
    pause_timer(state)
    log_event(state, f"🚀 Game started with {len(state['players'])} players! Round 1 (Night) begins.")
    save_game(state["code"], state)
    return state


def return_to_lobby(state: dict[str, Any]) -> dict[str, Any]:
    """End or reset the active game back to the Pre-Game Lobby while keeping players connected."""
    state["phase"] = "lobby"
    state["round_number"] = 0
    state["night_actions"] = {}
    state["night_report"] = []
    state["night_stage_index"] = 0
    state["revealed_inspect"] = None
    state["voting"] = _reset_voting_state(state)
    state["defense_player_id"] = None
    state["winner"] = None
    state["broadcast_message"] = None
    pause_timer(state)
    for p in state["players"].values():
        p["role"] = None
        p["faction"] = None
        p["status"] = "alive"
        p["used_limbo"] = False
        p["is_silenced"] = False
        p["lover_id"] = None
        p["last_guarded_id"] = None
        p["sniper_danger_bullets"] = 1
        p["sniper_silver_bullets"] = 1 if state["settings"].get("sniper_bullet_type") == "mix" else 0
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
    if player_id in state["players"]:
        role_info = ROLE_REGISTRY.get(role_id, ROLE_REGISTRY["villager"])
        state["players"][player_id]["role"] = role_id
        state["players"][player_id]["faction"] = role_info["faction"]
        save_game(state["code"], state)
    return state


# --- Status & Limbo ---


def set_player_status(state: dict[str, Any], player_id: str, new_status: str) -> dict[str, Any]:
    """Change player status between 'alive', 'limbo', and 'dead'. Handles Cupid lover cascade."""
    if player_id not in state["players"]:
        return state

    player = state["players"][player_id]
    player["status"] = new_status

    if new_status == "limbo":
        player["used_limbo"] = True
        log_event(state, f"{player['name']} entered Limbo.")
    elif new_status == "dead":
        log_event(state, f"{player['name']} died.")
        # Check Cupid lover cascade!
        lover_id = player.get("lover_id")
        if lover_id and lover_id in state["players"]:
            lover = state["players"][lover_id]
            if lover["status"] != "dead":
                lover["status"] = "dead"
                log_event(state, f"{lover['name']} died of a broken heart following their lover {player['name']}!")
    elif new_status == "alive":
        log_event(state, f"{player['name']} returned to life!")

    check_win_condition(state)
    save_game(state["code"], state)
    return state


def guess_angel_in_limbo(state: dict[str, Any], player_id: str, guessed_angel_id: str) -> tuple[bool, str]:
    """Limbo mechanic: Player guesses who the Angel is. If correct, revived!"""
    if player_id not in state["players"]:
        return False, "Player not found."
    player = state["players"][player_id]

    if player["status"] != "limbo":
        return False, "You are not currently in Limbo."

    if guessed_angel_id not in state["players"]:
        return False, "Invalid target selected."

    target = state["players"][guessed_angel_id]
    if target["role"] == "angel":
        player["status"] = "alive"
        msg = f"✨ Divine Revelation! {player['name']} found the Angel ({target['name']}) and returned to the living!"
        log_event(state, msg)
        save_game(state["code"], state)
        return True, msg
    else:
        # Failed guess: player permanently dies
        player["status"] = "dead"
        msg = f"💀 {player['name']} guessed wrong ({target['name']} is not Angel) and died."
        log_event(state, msg)
        save_game(state["code"], state)
        return False, msg


# --- Night Actions & Resolution Engine ---


def get_night_stages(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Determine the active ordered stages for the night phase based on living roles."""
    stages = []
    players = state.get("players", {})
    theme = state.get("theme", "werewolf")
    is_mafia = theme == "mafia"
    actions = state.get("night_actions", {})
    ordered = get_ordered_players(state)
    round_num = state.get("round_number", 1)

    def living_with_role(r_id: str) -> list[dict[str, Any]]:
        return [
            {"id": p["id"], "name": p["name"], "seat_number": idx + 1, "last_guarded_id": p.get("last_guarded_id")}
            for idx, p in enumerate(ordered)
            if p.get("role") == r_id and p.get("status") == "alive"
        ]

    # 1. Cupid (Night 1 only, if Cupid in game and alive)
    cupid_players = living_with_role("cupid")
    if round_num <= 1 and cupid_players:
        current_lovers = actions.get("cupid_lovers", [])
        stages.append(
            {
                "id": "cupid",
                "title": "💘 Cupid (Matchmaker)" if is_mafia else "💘 Cupid (Lovers)",
                "role_id": "cupid",
                "actors": cupid_players,
                "script": "Cupid, wake up! Silently point at two players you bind as lovers.",
                "target_ids": current_lovers,
                "target_names": [players[pid]["name"] for pid in current_lovers if pid in players],
                "is_complete": len(current_lovers) == 2,
            }
        )

    # 2. Werewolves / Mafia
    wolves = [
        {"id": p["id"], "name": p["name"], "seat_number": idx + 1}
        for idx, p in enumerate(ordered)
        if p.get("faction") == FACTION_WOLVES and p.get("status") == "alive"
    ]
    wolf_target_id = actions.get("wolf_target")
    wolf_target_name = players[wolf_target_id]["name"] if wolf_target_id in players else None
    stages.append(
        {
            "id": "wolves",
            "title": "🐺 Mafia Hit" if is_mafia else "🐺 Werewolves Hunt",
            "role_id": "werewolf",
            "actors": wolves,
            "script": "Mafia, wake up! Silently agree and point at your victim."
            if is_mafia
            else "Werewolves, wake up! Look at each other and silently point at your victim.",
            "target_id": wolf_target_id,
            "target_name": wolf_target_name,
            "is_complete": bool(wolf_target_id),
        }
    )

    # 3. Silencer
    silencer_players = living_with_role("silencer")
    if silencer_players:
        s_target_id = actions.get("silencer_target")
        stages.append(
            {
                "id": "silencer",
                "title": "🤐 Consigliere (Silence)" if is_mafia else "🤐 Silencer Spell",
                "role_id": "silencer",
                "actors": silencer_players,
                "script": "Silencer, wake up! Silently point at the player who cannot speak tomorrow.",
                "target_id": s_target_id,
                "target_name": players[s_target_id]["name"] if s_target_id in players else None,
                "is_complete": bool(s_target_id),
            }
        )

    # 4. Framer
    framer_players = living_with_role("framer")
    if framer_players:
        f_target_id = actions.get("framer_target")
        stages.append(
            {
                "id": "framer",
                "title": "🎭 Framer / Swindler",
                "role_id": "framer",
                "actors": framer_players,
                "script": "Framer, wake up! Silently point at someone to frame so they appear evil to the Detective.",
                "target_id": f_target_id,
                "target_name": players[f_target_id]["name"] if f_target_id in players else None,
                "is_complete": bool(f_target_id),
            }
        )

    # 5. Detective
    detective_players = living_with_role("detective")
    if detective_players:
        det_query = actions.get("detective_query", {})
        det_target_id = det_query.get("target_id")
        stages.append(
            {
                "id": "detective",
                "title": "🔍 Detective Investigation",
                "role_id": "detective",
                "actors": detective_players,
                "script": "Detective, wake up! Silently point at the person you want to inspect.",
                "target_id": det_target_id,
                "target_name": players[det_target_id]["name"] if det_target_id in players else None,
                "result": det_query.get("result"),
                "is_evil": det_query.get("is_evil"),
                "is_complete": bool(det_target_id),
            }
        )

    # 6. Doctor / Medic
    doctor_players = living_with_role("doctor")
    if doctor_players:
        doc_target_id = actions.get("doctor_protect")
        last_guarded = doctor_players[0].get("last_guarded_id") if doctor_players else None
        stages.append(
            {
                "id": "doctor",
                "title": "🩺 Doctor / Guard",
                "role_id": "doctor",
                "actors": doctor_players,
                "script": "Doctor, wake up! Silently point at the player you want to protect tonight.",
                "target_id": doc_target_id,
                "target_name": players[doc_target_id]["name"] if doc_target_id in players else None,
                "last_guarded_id": last_guarded,
                "is_complete": bool(doc_target_id),
            }
        )

    # 7. Bodyguard
    bodyguard_players = living_with_role("bodyguard")
    if bodyguard_players:
        bg_target_id = actions.get("bodyguard_protect")
        stages.append(
            {
                "id": "bodyguard",
                "title": "🛡️ Bodyguard Shield",
                "role_id": "bodyguard",
                "actors": bodyguard_players,
                "script": "Bodyguard, wake up! Silently point at who you will shield with your life.",
                "target_id": bg_target_id,
                "target_name": players[bg_target_id]["name"] if bg_target_id in players else None,
                "is_complete": bool(bg_target_id),
            }
        )

    # 8. Witch
    witch_players = living_with_role("witch")
    has_revive = not state.get("witch_used_revive", False)
    has_kill = not state.get("witch_used_kill", False)
    if witch_players and (has_revive or has_kill):
        w_act = actions.get("witch_action", {})
        victim_id = actions.get("wolf_target")
        victim_name = players[victim_id]["name"] if victim_id in players else "Nobody"
        stages.append(
            {
                "id": "witch",
                "title": "🧙‍♀️ Witch / Chemist",
                "role_id": "witch",
                "actors": witch_players,
                "script": (
                    f"Witch, wake up! Tonight's victim is {victim_name}. "
                    "Do you want to use your revival potion? Do you want to poison someone?"
                ),
                "victim_name": victim_name,
                "revive": w_act.get("revive", False),
                "has_revive_potion": has_revive,
                "has_kill_potion": has_kill,
                "kill_target_id": w_act.get("kill_target"),
                "kill_target_name": players[w_act["kill_target"]]["name"]
                if w_act.get("kill_target") in players
                else None,
                "is_complete": bool(w_act),
            }
        )

    # 9. Sniper
    sniper_players = living_with_role("sniper")
    if sniper_players:
        s_act = actions.get("sniper_shot", {})
        s_target_id = s_act.get("target_id")
        stages.append(
            {
                "id": "sniper",
                "title": "🎯 Sniper / Vigilante",
                "role_id": "sniper",
                "actors": sniper_players,
                "script": (
                    "Sniper, wake up! Silently point if you wish to shoot someone tonight, "
                    "or shake head to pass."
                ),
                "target_id": s_target_id,
                "target_name": players[s_target_id]["name"] if s_target_id in players else None,
                "bullet_type": s_act.get("bullet_type", "danger"),
                "is_complete": bool(s_target_id),
            }
        )

    # 10. Serial Killer
    sk_players = living_with_role("serial_killer")
    if sk_players:
        sk_target_id = actions.get("sk_target")
        stages.append(
            {
                "id": "serial_killer",
                "title": "🔪 Serial Killer Strike",
                "role_id": "serial_killer",
                "actors": sk_players,
                "script": "Serial Killer, wake up! Silently point at your solo victim.",
                "target_id": sk_target_id,
                "target_name": players[sk_target_id]["name"] if sk_target_id in players else None,
                "is_complete": bool(sk_target_id),
            }
        )

    # 11. Dawn Review (Always final stage)
    stages.append(
        {
            "id": "review",
            "title": "☀️ Dawn Review & Resolve",
            "role_id": None,
            "actors": [],
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

    if stage_id == "wolves":
        actions["wolf_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Wolves victim set to: {name}")
        save_game(state["code"], state)
        return True, f"Wolves target: {name}"

    elif stage_id == "silencer":
        actions["silencer_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Silencer target set to: {name}")
        save_game(state["code"], state)
        return True, f"Silencer target: {name}"

    elif stage_id == "framer":
        actions["framer_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Framer target set to: {name}")
        save_game(state["code"], state)
        return True, f"Framer target: {name}"

    elif stage_id == "detective":
        if not target_id or target_id not in players:
            return False, "Invalid inspection target."
        target = players[target_id]
        is_framed = actions.get("framer_target") == target_id
        is_evil = (
            (target["faction"] == FACTION_WOLVES or target["role"] == "serial_killer")
            and target["role"] != "alpha_wolf"
        ) or is_framed
        result_text = "Evil / Enemy" if is_evil else "Good / Innocent"
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
        actions["sniper_shot"] = {
            "actor_id": sniper_actor,
            "target_id": target_id,
            "bullet_type": extra.get("bullet_type", "danger"),
        }
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Sniper shot set to: {name}")
        save_game(state["code"], state)
        return True, f"Sniper shot: {name}"

    elif stage_id == "serial_killer":
        actions["sk_target"] = target_id
        name = players[target_id]["name"] if target_id in players else "None"
        log_event(state, f"Serial Killer target set to: {name}")
        save_game(state["code"], state)
        return True, f"Serial Killer target: {name}"

    elif stage_id == "cupid":
        extra = extra or {}
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

    return False, "Unknown stage"


def clear_gm_night_action(state: dict[str, Any], stage_id: str) -> None:
    actions = state.setdefault("night_actions", {})
    mapping = {
        "wolves": "wolf_target",
        "silencer": "silencer_target",
        "framer": "framer_target",
        "detective": "detective_query",
        "doctor": "doctor_protect",
        "bodyguard": "bodyguard_protect",
        "witch": "witch_action",
        "sniper": "sniper_shot",
        "serial_killer": "sk_target",
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

    if action_type == "kill":  # Werewolf / Mafioso
        if actor["faction"] != FACTION_WOLVES:
            return False, "Not authorized to kill."
        actions["wolf_target"] = target_id
        return True, "Wolf target submitted."

    elif action_type == "inspect":  # Detective / Cop
        if actor["role"] != "detective":
            return False, "Not a detective."
        if not target_id or target_id not in state["players"]:
            return False, "Invalid inspection target."
        target = state["players"][target_id]
        # Check if framed!
        is_framed = actions.get("framer_target") == target_id
        is_evil = (
            (target["faction"] == FACTION_WOLVES or target["role"] == "serial_killer")
            and target["role"] != "alpha_wolf"
        ) or is_framed
        result_text = "Evil / Enemy" if is_evil else "Good / Innocent"
        actions["detective_query"] = {
            "actor_id": actor_id,
            "target_id": target_id,
            "result": result_text,
        }
        return True, f"Inspection result: {target['name']} is {result_text}."

    elif action_type == "protect":  # Doctor / Guard
        if actor["role"] != "doctor":
            return False, "Not a doctor."
        # Staggering doctor check:
        if state["settings"].get("staggering_doctor") and actor.get("last_guarded_id") == target_id:
            return False, "Staggering Doctor rule: You cannot protect the same person two nights in a row!"
        actions["doctor_protect"] = target_id
        return True, "Protection target set."

    elif action_type == "guard_bodyguard":  # Bodyguard
        if actor["role"] != "bodyguard":
            return False, "Not a bodyguard."
        actions["bodyguard_protect"] = target_id
        actions["bodyguard_actor"] = actor_id
        return True, "Bodyguard protection set."

    elif action_type == "frame":  # Framer
        if actor["role"] != "framer":
            return False, "Not a framer."
        actions["framer_target"] = target_id
        return True, "Framing target set."

    elif action_type == "solo_kill":  # Serial Killer
        if actor["role"] != "serial_killer":
            return False, "Not a serial killer."
        actions["sk_target"] = target_id
        return True, "Solo kill target set."

    elif action_type == "shoot":  # Sniper
        if actor["role"] != "sniper":
            return False, "Not a sniper."
        bullet_type = (extra or {}).get("bullet_type", state["settings"].get("sniper_bullet_type", "danger"))
        actions["sniper_shot"] = {
            "actor_id": actor_id,
            "target_id": target_id,
            "bullet_type": bullet_type,
        }
        return True, "Sniper target locked."

    elif action_type == "silence":  # Magic Wolf / Silencer
        if actor["role"] != "silencer":
            return False, "Not a silencer."
        actions["silencer_target"] = target_id
        return True, "Silence target set."

    elif action_type == "potion":  # Witch
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

    elif action_type == "veto":  # Mayor
        if actor["role"] != "mayor":
            return False, "Not a mayor."
        if state["mayor_used_veto"]:
            return False, "Mayor veto already used."
        actions["mayor_veto"] = True
        return True, "Mayor veto activated."

    elif action_type == "link_lovers":  # Cupid
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
    """Execute all night actions and produce the morning report."""
    actions = state.get("night_actions", {})
    report: list[str] = []
    to_kill: set[str] = set()
    to_save: set[str] = set()

    # 1. Cupid (Night 1 link)
    if "cupid_lovers" in actions:
        l1, l2 = actions["cupid_lovers"]
        if l1 in state["players"] and l2 in state["players"]:
            state["players"][l1]["lover_id"] = l2
            state["players"][l2]["lover_id"] = l1
            report.append("💘 Cupid has secretly linked two souls in eternal bond.")

    # 2. Doctor protect
    doc_target = actions.get("doctor_protect")
    if doc_target and doc_target in state["players"]:
        to_save.add(doc_target)
        # Record last guarded for staggering doctor
        for p in state["players"].values():
            if p["role"] == "doctor":
                p["last_guarded_id"] = doc_target

    # 2b. Bodyguard protect & sacrifice
    bg_target = actions.get("bodyguard_protect")
    bg_actor = actions.get("bodyguard_actor")
    wolf_target = actions.get("wolf_target")
    if bg_target and bg_target in state["players"] and wolf_target == bg_target:
        if wolf_target not in to_save:
            to_save.add(bg_target)
            if bg_actor and bg_actor in state["players"]:
                to_kill.add(bg_actor)
                bg_name = state["players"][bg_actor]["name"]
                t_name = state["players"][bg_target]["name"]
                report.append(f"🛡️ The Bodyguard ({bg_name}) sacrificed their life to protect {t_name} from death!")

    # 3. Werewolf kill
    if wolf_target and wolf_target in state["players"]:
        if wolf_target in to_save:
            report.append("🛡️ Protection shielded the victim from death.")
        else:
            to_kill.add(wolf_target)

    # 4. Witch action
    witch_act = actions.get("witch_action", {})
    if witch_act.get("revive") and wolf_target:
        if wolf_target in to_kill:
            to_kill.remove(wolf_target)
            state["witch_used_revive"] = True
            report.append("🧪 A mystical potion preserved a life from the jaws of death.")
    if witch_act.get("kill_target"):
        w_kill = witch_act["kill_target"]
        if w_kill in state["players"]:
            to_kill.add(w_kill)
            state["witch_used_kill"] = True
            report.append("💀 A lethal poison was administered during the dark hours.")

    # 4b. Serial Killer solo kill
    sk_target = actions.get("sk_target")
    if sk_target and sk_target in state["players"]:
        if sk_target in to_save:
            report.append("🛡️ Protection shielded a victim from the Serial Killer's blade.")
        else:
            to_kill.add(sk_target)
            sk_victim = state["players"][sk_target]["name"]
            report.append(f"🔪 A mysterious killer struck in the shadows! {sk_victim} was eliminated.")

    # 5. Sniper shot
    sniper_act = actions.get("sniper_shot")
    if sniper_act:
        s_target_id = sniper_act.get("target_id")
        b_type = sniper_act.get("bullet_type", "danger")
        actor_id = sniper_act.get("actor_id")
        if s_target_id and s_target_id in state["players"]:
            s_target = state["players"][s_target_id]
            is_evil_wolf = s_target["faction"] == FACTION_WOLVES
            # Doctor saving from sniper toggle:
            protected_from_sniper = (s_target_id in to_save) and state["settings"].get(
                "doctor_saves_from_sniper", False
            )

            if protected_from_sniper:
                report.append("🛡️ The sniper's bullet was deflected by the Doctor's guard!")
            else:
                to_kill.add(s_target_id)
                if is_evil_wolf:
                    report.append("🎯 A sniper shot found its mark in the heart of evil!")
                else:
                    report.append("💥 A tragic mistake! A sniper bullet hit an innocent civilian.")
                    if b_type == "danger" and actor_id and actor_id in state["players"]:
                        # Danger bullet: sniper dies of guilt!
                        to_kill.add(actor_id)
                        report.append("⚡ The sniper's danger bullet rebounded — the sniper died of remorse.")

    # 6. Silencer action
    silencer_target = actions.get("silencer_target")
    # Reset previous day silences
    for p in state["players"].values():
        p["is_silenced"] = False
    if silencer_target and silencer_target in state["players"]:
        state["players"][silencer_target]["is_silenced"] = True
        report.append(
            f"🤐 {state['players'][silencer_target]['name']} has been cast under a silencing spell for the day!"
        )

    # 7. Mayor veto of yesterday's vote
    if actions.get("mayor_veto") and state.get("last_lynched_id"):
        lynched_id = state["last_lynched_id"]
        if lynched_id in state["players"]:
            p_name = state["players"][lynched_id]["name"]
            state["players"][lynched_id]["status"] = "alive"
            state["mayor_used_veto"] = True
            report.append(f"📜 The Mayor exercised official veto! {p_name} was pardoned and returned alive!")

    # 8. Apply casualties (handling Limbo)
    limbo_on = state["settings"].get("limbo_enabled", True)
    has_angel = any(p["role"] == "angel" and p["status"] != "dead" for p in state["players"].values())

    for pid in to_kill:
        p = state["players"][pid]
        if limbo_on and has_angel and not p["used_limbo"]:
            p["status"] = "limbo"
            p["used_limbo"] = True
            report.append(
                f"🌫️ {p['name']} fell during the night, but hovers in Limbo with one chance to guess the Angel!"
            )
        else:
            p["status"] = "dead"
            report.append(f"🪦 {p['name']} was slain in the night.")
            # Cupid lover cascade
            lover_id = p.get("lover_id")
            if lover_id and lover_id in state["players"]:
                lover = state["players"][lover_id]
                if lover["status"] != "dead":
                    lover["status"] = "dead"
                    report.append(f"💔 {lover['name']} perished from profound grief over their lover {p['name']}!")

    if not to_kill:
        report.append("☀️ Dawn breaks over a peaceful night. No one died!")

    state["night_report"] = report
    state["night_actions"] = {}  # Clear for next night
    state["night_stage_index"] = 0
    state["revealed_inspect"] = None
    state["voting"] = _reset_voting_state(state)
    state["phase"] = "day_discussion"
    state["round_number"] += 1

    # Start discussion timer
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
    import math

    return max(1, math.ceil(count * (pct / 100.0)))


def start_voting_session(state: dict[str, Any], system: Optional[str] = None) -> dict[str, Any]:
    """Initiate day voting. Transitions to nomination (or directly to final vote if simple plurality)."""
    voting_system = system or state.get("settings", {}).get("voting_system", "two_stage_50pct")
    initial_stage = "final_vote" if voting_system == "simple_plurality" else "nomination"
    living_ids = [p["id"] for p in get_living_players(state)] if voting_system == "simple_plurality" else []

    state["phase"] = "day_voting"
    state["voting"] = {
        "stage": initial_stage,  # "nomination", "defense", "final_vote", "revote", "completed"
        "system": voting_system,
        "nomination_votes": {},  # candidate_id: [voter_ids]
        "nominated_player_ids": living_ids,
        "final_votes": {},  # voter_id: candidate_id
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
    """A voter toggles their hand for a candidate during nomination (multi-vote allowed)."""
    voting = state.setdefault("voting", {})
    if voting.get("stage") != "nomination":
        return False, "Not in nomination phase."

    players = state.get("players", {})
    if candidate_id not in players or players[candidate_id]["status"] != "alive":
        return False, "Candidate must be alive."

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
            if len(voters) >= threshold and state["players"].get(cid, {}).get("status") == "alive"
        ]
    elif system == "two_stage_top_n":
        sorted_cands = sorted(
            [
                (cid, len(v))
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
    """A voter casts their single vote for one of the nominated candidates (or abstains with None)."""
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
    Tie rules per user requirement:
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
            counts[cand_id] += 1

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
            voting["final_votes"] = {}  # Clear for fresh revote
            joined_tied = ", ".join(tied_names)
            msg = (
                f"⚖️ TIE between {joined_tied} ({max_votes} votes each)! "
                "Runoff revote initiated among tied candidates."
            )
            log_event(state, msg)
            save_game(state["code"], state)
            return "revote", msg
        else:
            # SECOND TIE: "on second tie, noone gets eliminated"
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

    # Check JESTER instant win!
    if victim.get("role") == "jester":
        state["winner"] = "jester"
        state["phase"] = "gameover"
        voting["stage"] = "completed"
        voting["elimination_result"] = "jester_win"
        set_player_status(state, victim_id, "dead")
        msg = f"🃏 The Jester ({victim['name']}) was executed by town vote and won SOLO VICTORY!"
        log_event(state, msg)
        save_game(state["code"], state)
        return "jester_win", msg

    # Check Limbo vs Dead
    limbo_on = state.get("settings", {}).get("limbo_enabled", True)
    has_angel = any(p["role"] == "angel" and p["status"] != "dead" for p in players.values())

    if limbo_on and has_angel and not victim["used_limbo"]:
        set_player_status(state, victim_id, "limbo")
        voting["elimination_result"] = "limbo"
        msg = f"🌫️ {victim['name']} received {max_votes} votes and was banished to Limbo (can guess Angel to return)!"
    else:
        set_player_status(state, victim_id, "dead")
        voting["elimination_result"] = "dead"
        msg = f"🪦 {victim['name']} received {max_votes} votes and was executed by town vote!"

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
            nomination_candidates.append(
                {
                    "id": pid,
                    "seat_number": idx + 1,
                    "name": p["name"],
                    "vote_count": len(v_list),
                    "is_nominated": pid in official_nominees,
                    "has_my_vote": player_id in v_list if player_id else False,
                }
            )

    allowed_ids = revote_cands if stage == "revote" else official_nominees
    final_candidates = []
    for idx, p in enumerate(ordered):
        pid = p["id"]
        if pid in allowed_ids and p["status"] == "alive":
            vote_count = sum(1 for cid in final_votes.values() if cid == pid)
            final_candidates.append(
                {
                    "id": pid,
                    "seat_number": idx + 1,
                    "name": p["name"],
                    "vote_count": vote_count,
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
    """Check if Town or Wolves have achieved victory."""
    if state.get("winner") == "jester":
        return "jester"

    alive_players = [p for p in state["players"].values() if p["status"] == "alive"]
    if not alive_players:
        state["winner"] = "tie"
        return "tie"

    # Check lovers win (if only 2 alive and they are lovers)
    if len(alive_players) == 2:
        p1, p2 = alive_players[0], alive_players[1]
        if p1.get("lover_id") == p2["id"]:
            state["winner"] = "lovers"
            state["phase"] = "gameover"
            log_event(state, f"💘 Love conquers all! {p1['name']} and {p2['name']} won together!")
            return "lovers"

    wolves_count = sum(1 for p in alive_players if p["faction"] == FACTION_WOLVES)
    sk_count = sum(1 for p in alive_players if p.get("role") == "serial_killer")

    # Check Serial Killer solo victory
    if sk_count > 0 and len(alive_players) <= 2 and wolves_count == 0:
        sk_player = next(p for p in alive_players if p.get("role") == "serial_killer")
        state["winner"] = "serial_killer"
        state["phase"] = "gameover"
        log_event(state, f"🔪 The Serial Killer ({sk_player['name']}) has outlived everyone and claimed solo victory!")
        return "serial_killer"

    if wolves_count == 0 and sk_count == 0:
        state["winner"] = "town"
        state["phase"] = "gameover"
        theme = state.get("theme", "werewolf")
        faction_name = "Villagers" if theme == "werewolf" else "Civilians"
        log_event(state, f"🏆 Victory for the {faction_name}! All evil has been vanquished.")
        return "town"

    if wolves_count >= (len(alive_players) - wolves_count):
        state["winner"] = "wolves"
        state["phase"] = "gameover"
        theme = state.get("theme", "werewolf")
        faction_name = "Werewolves" if theme == "werewolf" else "Mafia"
        log_event(state, f"🐺 Victory for the {faction_name}! They have overrun the town.")
        return "wolves"

    return None


# --- Sanitized Views for Clients ---


def get_sanitized_player_view(state: dict[str, Any], player_id: str) -> dict[str, Any]:
    """Client view for a specific player: hides secret GM data and others' secret roles."""
    player = state["players"].get(player_id)
    if not player:
        return {}

    theme = state.get("theme", "werewolf")
    is_wolf = player["faction"] == FACTION_WOLVES
    lover_id = player.get("lover_id")

    ordered_players = get_ordered_players(state)
    public_players = []
    for idx, p in enumerate(ordered_players):
        pid = p["id"]
        # Only show other players' roles if:
        # 1. Game over
        # 2. Both are wolves
        # 3. Or player is dead and reveal_roles_on_death is enabled
        reveal_role = False
        if state["phase"] == "gameover":
            reveal_role = True
        elif is_wolf and p["faction"] == FACTION_WOLVES:
            reveal_role = True
        elif pid == player_id:
            reveal_role = True
        elif p["status"] == "dead" and state["settings"].get("reveal_roles_on_death", True):
            reveal_role = True

        role_display = None
        if reveal_role and p.get("role"):
            role_display = get_role_info(p["role"], theme)

        public_players.append(
            {
                "id": p["id"],
                "seat_number": idx + 1,
                "name": p["name"],
                "status": p["status"],
                "is_silenced": p["is_silenced"],
                "is_me": pid == player_id,
                "is_lover": pid == lover_id,
                "is_pack_mate": is_wolf and p["faction"] == FACTION_WOLVES and pid != player_id,
                "role": role_display,
            }
        )

    my_role_info = get_role_info(player["role"], theme) if player.get("role") else None

    revealed_inspect = None
    if player.get("role") == "detective":
        revealed_inspect = state.get("revealed_inspect")

    night_stage_title = None
    if state.get("phase") == "night":
        stages = get_night_stages(state)
        idx = state.get("night_stage_index", 0)
        if 0 <= idx < len(stages):
            night_stage_title = stages[idx]["title"]

    # Calculate timer remaining
    timer_data = dict(state["timer"])
    if not timer_data["paused"] and timer_data["ends_at"]:
        timer_data["remaining"] = max(0, int(timer_data["ends_at"] - time.time()))

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
            "used_limbo": player["used_limbo"],
            "role": my_role_info,
            "lover_name": state["players"][lover_id]["name"] if lover_id and lover_id in state["players"] else None,
        },
        "players": public_players,
        "timer": timer_data,
        "night_stage_title": night_stage_title,
        "revealed_inspect": revealed_inspect,
        "voting": get_voting_view(state, is_gm=False, player_id=player_id),
        "night_report": state.get("night_report", []),
        "winner": state.get("winner"),
        "broadcast_message": state.get("broadcast_message"),
        "settings": {
            "limbo_enabled": state["settings"].get("limbo_enabled", True),
            "voting_system": state["settings"].get("voting_system", "two_stage_50pct"),
        },
    }


def get_gm_view(state: dict[str, Any]) -> dict[str, Any]:
    """Complete, unrestricted view for the Game Master cockpit."""
    theme = state.get("theme", "werewolf")

    ordered_players = get_ordered_players(state)
    all_players = []
    for idx, p in enumerate(ordered_players):
        lover_name = state["players"][p["lover_id"]]["name"] if p.get("lover_id") in state["players"] else None
        role_info = get_role_info(p["role"], theme) if p.get("role") else None
        all_players.append(
            {
                "id": p["id"],
                "seat_number": idx + 1,
                "name": p["name"],
                "token": p["token"],
                "status": p["status"],
                "role": role_info,
                "is_silenced": p["is_silenced"],
                "is_offline": p["is_offline"],
                "used_limbo": p["used_limbo"],
                "lover_name": lover_name,
                "last_guarded_id": p.get("last_guarded_id"),
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
        "deck": [get_role_info(r, theme) for r in state.get("deck", [])],
        "raw_deck": state.get("deck", []),
        "available_roles": get_all_roles_catalogue(theme),
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
        "broadcast_message": state.get("broadcast_message"),
        "witch_used_revive": state.get("witch_used_revive", False),
        "witch_used_kill": state.get("witch_used_kill", False),
        "mayor_used_veto": state.get("mayor_used_veto", False),
    }

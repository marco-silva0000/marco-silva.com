"""SmartN (Smart 10 Trivia) Game State Engine.

Redis-backed state machine and game logic:
- Zero-spoiler sanitization for secret answers
- Dual mode: Multi-Device WebSocket and Single-Device Pass & Play
- Push-your-luck mechanics: Answer vs Pass & Bank
- Yes/No scoring flexibility (standard find-true vs prediction scoring)
- Chat answer parsing and host arbitration
"""

import json
import logging
import random
import time
import uuid
from typing import Any

from django.core.cache import cache

from gamerooms.player_colors import assign_distinct_player_color, get_player_initials
from smartn.questions import SMARTN_QUESTIONS, get_deck

logger = logging.getLogger(__name__)

REDIS_PREFIX = "smartn:game:"
ROOM_EXPIRY_SECONDS = 86400  # 24 hours

DEFAULT_SETTINGS = {
    "mode": "multi_device",  # "multi_device" | "single_device"
    "pack": "mix",  # "mix", "geo", "media", "science", "history", "food", "sports"
    "yes_no_scoring": "standard",  # "standard" (true only) | "prediction" (predict true/false)
    "count_filter": "all",  # "all" | "exactly_10"
    "target_score": 20,  # points to win match
    "turn_timer": 0,  # 0 = untimed, or 30/45/60s
}

PACK_CHOICES = [
    ("mix", "🎲 All Topics (Mixed)"),
    ("geo", "🌍 World Geography"),
    ("media", "🎬 Cinema, Movies & Pop Culture"),
    ("science", "🔬 Science, Nature & Space"),
    ("history", "🏛️ History & World Civilizations"),
    ("food", "🍕 Food, Cooking & Culinary"),
    ("sports", "⚽ Sports, Rules & Players"),
]


def _get_cache_key(code: str) -> str:
    return f"{REDIS_PREFIX}{code.upper()}"


def get_game(code: str) -> dict[str, Any] | None:
    data = cache.get(_get_cache_key(code))
    if not data:
        return None
    if isinstance(data, str):
        try:
            return json.loads(data)
        except Exception:
            return None
    return data


def save_game(code: str, state: dict[str, Any]) -> None:
    cache.set(_get_cache_key(code), json.dumps(state), timeout=ROOM_EXPIRY_SECONDS)


def delete_game(code: str) -> None:
    cache.delete(_get_cache_key(code))


def append_event(
    state: dict[str, Any],
    sender: str,
    text: str,
    kind: str = "system",
    player_id: str | None = None,
    color: str | None = None,
    initials: str | None = None,
) -> dict[str, Any]:
    chat_log = state.setdefault("chat_log", [])
    entry = {
        "id": f"msg_{int(time.time() * 1000)}_{random.randint(100, 999)}",
        "sender": sender,
        "text": text,
        "kind": kind,
        "player_id": player_id,
        "color": color,
        "initials": initials,
        "ts": time.time(),
    }
    chat_log.append(entry)
    if len(chat_log) > 80:
        state["chat_log"] = chat_log[-80:]
    return entry


def find_player_by_token(state: dict[str, Any], token: str | None) -> dict[str, Any] | None:
    if not token or not state:
        return None
    for p in state.get("players", []):
        if p.get("token") == token:
            return p
    return None


def find_player_by_name(state: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    if not name or not state:
        return None
    lowered = name.strip().lower()
    for p in state.get("players", []):
        if p.get("name", "").strip().lower() == lowered:
            return p
    return None


def find_player_by_id(state: dict[str, Any], pid: str | None) -> dict[str, Any] | None:
    if not pid or not state:
        return None
    for p in state.get("players", []):
        if p.get("id") == pid:
            return p
    return None


def create_game(code: str, host_name: str = "Host", settings: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = DEFAULT_SETTINGS.copy()
    if settings:
        cfg.update(settings)

    state: dict[str, Any] = {
        "code": code.upper(),
        "phase": "lobby",  # lobby, playing, round_summary, gameover
        "settings": cfg,
        "round_num": 0,
        "players": [],
        "current_player_id": None,
        "turn_order": [],
        "player_statuses": {},  # pid -> "active" | "passed" | "busted"
        "round_baskets": {},  # pid -> int unbanked round points
        "card": None,
        "revealed_capsules": {},  # slot_str -> revealed dict
        "used_question_ids": [],
        "winner_id": None,
        "winner_name": None,
        "winner_reason": None,
        "chat_log": [],
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    save_game(code, state)
    return state


def add_player(
    code_or_state: str | dict[str, Any],
    name: str,
    player_id: str | None = None,
    token: str | None = None,
    is_admin: bool = False,
    color: str | None = None,
    channel_name: str = "",
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    if isinstance(code_or_state, dict):
        state = code_or_state
        code = state["code"]
    else:
        code = code_or_state.upper()
        state = get_game(code)
        if not state:
            state = create_game(code, host_name=name)

    players = state.setdefault("players", [])

    # 1. Check existing by token
    if token:
        existing = find_player_by_token(state, token)
        if existing:
            existing["connected"] = True
            if channel_name:
                existing["channel_name"] = channel_name
            if is_admin:
                existing["is_admin"] = True
            save_game(code, state)
            return state, existing, False

    # 2. Check existing by ID
    if player_id:
        existing = find_player_by_id(state, player_id)
        if existing:
            existing["connected"] = True
            existing["name"] = name
            if channel_name:
                existing["channel_name"] = channel_name
            if is_admin:
                existing["is_admin"] = True
            save_game(code, state)
            return state, existing, False

    # 3. Check existing by name (reconnect if disconnected or lobby)
    by_name = find_player_by_name(state, name)
    if by_name and (not by_name.get("connected", False) or state.get("phase") == "lobby"):
        by_name["connected"] = True
        if channel_name:
            by_name["channel_name"] = channel_name
        if is_admin:
            by_name["is_admin"] = True
        save_game(code, state)
        return state, by_name, False

    # 4. Create new player
    p_color = color or assign_distinct_player_color(players)
    new_pid = player_id or f"p{len(players) + 1}_{uuid.uuid4().hex[:6]}"
    p_token = token or uuid.uuid4().hex[:12]

    player = {
        "id": new_pid,
        "token": p_token,
        "name": name,
        "is_admin": is_admin or len(players) == 0,
        "color": p_color,
        "initials": get_player_initials(name),
        "score": 0,
        "connected": True,
        "is_spectator": False,
        "channel_name": channel_name,
    }
    players.append(player)
    append_event(
        state,
        "System",
        f"👋 {name} joined the Smartbox.",
        player_id=new_pid,
        color=p_color,
        initials=player["initials"],
    )
    save_game(code, state)
    return state, player, True


def kick_player(code: str, player_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None
    players = state.setdefault("players", [])
    target = find_player_by_id(state, player_id)
    if not target:
        return False, "Player not found.", state
    if target.get("is_admin"):
        return False, "Cannot kick the room host.", state

    players.remove(target)
    # Remove from turn order if present
    turn_order = state.get("turn_order", [])
    if player_id in turn_order:
        turn_order.remove(player_id)
        if state.get("current_player_id") == player_id:
            _advance_turn(state)

    append_event(state, "System", f"👢 {target['name']} was removed from the room.")
    save_game(code, state)
    return True, f"{target['name']} removed.", state


def transfer_host(code: str, new_host_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None
    target = find_player_by_id(state, new_host_id)
    if not target:
        return False, "Target player not found.", state

    for p in state.get("players", []):
        p["is_admin"] = p["id"] == new_host_id

    append_event(state, "System", f"👑 Room host transferred to {target['name']}.")
    save_game(code, state)
    return True, f"Host transferred to {target['name']}.", state


def set_player_connection(code: str, player_id: str, connected: bool) -> dict[str, Any] | None:
    state = get_game(code)
    if not state:
        return None
    for p in state.get("players", []):
        if p["id"] == player_id:
            p["connected"] = connected
            break
    save_game(code, state)
    return state


def update_settings(code: str, new_settings: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None
    if state["phase"] != "lobby":
        return False, "Settings can only be changed in the lobby.", state

    cfg = state.setdefault("settings", {})
    if "mode" in new_settings and new_settings["mode"] in ("multi_device", "single_device"):
        cfg["mode"] = new_settings["mode"]
    if "pack" in new_settings:
        cfg["pack"] = str(new_settings["pack"])
    if "yes_no_scoring" in new_settings and new_settings["yes_no_scoring"] in ("standard", "prediction"):
        cfg["yes_no_scoring"] = new_settings["yes_no_scoring"]
    if "count_filter" in new_settings and new_settings["count_filter"] in ("all", "exactly_10"):
        cfg["count_filter"] = new_settings["count_filter"]
    if "target_score" in new_settings:
        try:
            cfg["target_score"] = max(5, min(100, int(new_settings["target_score"])))
        except (ValueError, TypeError):
            pass
    if "turn_timer" in new_settings:
        try:
            cfg["turn_timer"] = max(0, min(120, int(new_settings["turn_timer"])))
        except (ValueError, TypeError):
            pass

    append_event(state, "System", "⚙️ Game settings updated.")
    save_game(code, state)
    return True, "Settings updated.", state


def change_player_color(code: str, player_id: str, new_hex: str) -> bool:
    state = get_game(code)
    if not state:
        return False
    for p in state.get("players", []):
        if p["id"] == player_id:
            p["color"] = new_hex
            save_game(code, state)
            return True
    return False


def _deal_next_card(state: dict[str, Any]) -> dict[str, Any] | None:
    pack = state.get("settings", {}).get("pack", "mix")
    count_filter = state.get("settings", {}).get("count_filter", "all")
    deck = get_deck(pack_filter=pack, count_filter=count_filter)

    used = set(state.get("used_question_ids", []))
    available = [q for q in deck if q["id"] not in used]
    if not available:
        # Reset queue if all questions used
        available = deck
        state["used_question_ids"] = []

    if not available:
        available = SMARTN_QUESTIONS

    selected = random.choice(available)
    state.setdefault("used_question_ids", []).append(selected["id"])
    return selected


def start_game(code: str) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None

    players = [p for p in state.get("players", []) if not p.get("is_spectator")]
    if len(players) < 1:
        return False, "At least 1 player is required to play.", state

    state["phase"] = "playing"
    state["round_num"] = 1
    state["winner_id"] = None
    state["winner_name"] = None
    state["winner_reason"] = None

    # Reset scores
    for p in state["players"]:
        p["score"] = 0

    card = _deal_next_card(state)
    if not card:
        return False, "No questions available.", state

    state["card"] = card
    state["revealed_capsules"] = {}

    # Initialize turn order & round statuses
    turn_order = [p["id"] for p in players]
    random.shuffle(turn_order)
    state["turn_order"] = turn_order
    state["current_player_id"] = turn_order[0]
    state["player_statuses"] = {pid: "active" for pid in turn_order}
    state["round_baskets"] = {pid: 0 for pid in turn_order}

    append_event(state, "System", f"🎬 Match started! Card #{state['round_num']}: {card['prompt']}", kind="start")
    save_game(code, state)
    return True, "Match started.", state


def _advance_turn(state: dict[str, Any]) -> None:
    """Advance turn to the next player whose status is 'active'."""
    turn_order = state.get("turn_order", [])
    cur_id = state.get("current_player_id")
    statuses = state.get("player_statuses", {})

    active_players = [pid for pid in turn_order if statuses.get(pid) == "active"]
    if not active_players:
        _finish_round(state)
        return

    if cur_id in turn_order:
        start_idx = (turn_order.index(cur_id) + 1) % len(turn_order)
    else:
        start_idx = 0

    for i in range(len(turn_order)):
        candidate = turn_order[(start_idx + i) % len(turn_order)]
        if statuses.get(candidate) == "active":
            state["current_player_id"] = candidate
            player = next((p for p in state.get("players", []) if p["id"] == candidate), None)
            p_name = player["name"] if player else "Player"
            append_event(state, "System", f"👉 {p_name}'s turn to pick or pass.")
            return

    _finish_round(state)


def _finish_round(state: dict[str, Any]) -> None:
    """Conclude active card, bank remaining active baskets, and reveal all caps."""
    card = state.get("card") or {}
    items = card.get("items", [])
    revealed = state.setdefault("revealed_capsules", {})

    # 1. Any player who remained 'active' safely banks their round basket points
    statuses = state.get("player_statuses", {})
    baskets = state.setdefault("round_baskets", {})
    players = state.get("players", [])

    for p in players:
        pid = p["id"]
        if statuses.get(pid) == "active":
            pts = baskets.get(pid, 0)
            if pts > 0:
                p["score"] += pts
                append_event(state, "System", f"🔒 {p['name']} banked +{pts} unbanked points at round end.")
            baskets[pid] = 0
            statuses[pid] = "passed"

    # 2. Auto-reveal all remaining unpicked capsules
    for it in items:
        s_str = str(it["slot"])
        if s_str not in revealed:
            revealed[s_str] = {
                "slot": it["slot"],
                "label": it["label"],
                "value": it["value"],
                "is_correct": it["is_correct"],
                "revealed_by": "Board",
                "revealed_result": "unpicked",
                "explanation": it.get("explanation", ""),
            }

    # 3. Check for victory
    target_score = state.get("settings", {}).get("target_score", 20)
    top_player = max(players, key=lambda p: p.get("score", 0), default=None)
    if top_player and top_player.get("score", 0) >= target_score:
        state["phase"] = "gameover"
        state["winner_id"] = top_player["id"]
        state["winner_name"] = top_player["name"]
        state["winner_reason"] = f"Reached target of {target_score} points with {top_player['score']} pts!"
        append_event(
            state,
            "System",
            f"🏆 {top_player['name']} WINS THE MATCH with {top_player['score']} points!",
            kind="gameover",
        )
    else:
        state["phase"] = "round_summary"
        append_event(
            state, "System", f"🏁 Card #{state['round_num']} completed! Review answers and advance.", kind="summary"
        )


def pick_capsule(
    code: str,
    player_id: str,
    slot: int,
    prediction: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None

    if state.get("phase") != "playing":
        return False, "Game is not currently active.", state

    cur_pid = state.get("current_player_id")
    is_single_device = state.get("settings", {}).get("mode") == "single_device"

    # In single device mode, current device holder can act; in multi-device mode, only active player or admin
    player = next((p for p in state.get("players", []) if p["id"] == player_id), None)
    if not player:
        return False, "Player not found.", state

    if not is_single_device and cur_pid != player_id and not player.get("is_admin"):
        return False, "It is not your turn!", state

    active_turn_player = next((p for p in state.get("players", []) if p["id"] == cur_pid), player)
    turn_pid = active_turn_player["id"]

    if state.get("player_statuses", {}).get(turn_pid) != "active":
        return False, f"{active_turn_player['name']} has already passed or busted this round.", state

    card = state.get("card") or {}
    items = card.get("items", [])
    target_item = next((it for it in items if it["slot"] == slot), None)
    if not target_item:
        return False, f"Capsule #{slot} not found on this card.", state

    s_str = str(slot)
    revealed = state.setdefault("revealed_capsules", {})
    if s_str in revealed:
        return False, f"Capsule #{slot} is already revealed!", state

    # Evaluate answer correctness
    yes_no_scoring = state.get("settings", {}).get("yes_no_scoring", "standard")
    is_true_false = card.get("type") == "true_false"
    item_is_correct = bool(target_item.get("is_correct"))

    if is_true_false and yes_no_scoring == "prediction":
        # Player made an explicit prediction (Yes/True or No/False)
        pred_normalized = (prediction or "yes").strip().lower()
        pred_bool = pred_normalized in ("yes", "true", "y", "1")
        is_guess_correct = pred_bool == item_is_correct
    else:
        # Standard Smart 10 rules: capsule is evaluated by its intrinsic correctness
        is_guess_correct = item_is_correct

    baskets = state.setdefault("round_baskets", {})
    statuses = state.setdefault("player_statuses", {})

    if is_guess_correct:
        revealed[s_str] = {
            "slot": slot,
            "label": target_item["label"],
            "value": target_item["value"],
            "is_correct": True,
            "revealed_by": active_turn_player["name"],
            "revealed_result": "correct",
            "explanation": target_item.get("explanation", ""),
        }
        baskets[turn_pid] = baskets.get(turn_pid, 0) + 1
        append_event(
            state,
            "System",
            f"✅ {active_turn_player['name']} opened #{slot} ({target_item['label']}): CORRECT! (+1 round pt, basket: {baskets[turn_pid]})",
            kind="correct",
        )
    else:
        revealed[s_str] = {
            "slot": slot,
            "label": target_item["label"],
            "value": target_item["value"],
            "is_correct": False,
            "revealed_by": active_turn_player["name"],
            "revealed_result": "wrong",
            "explanation": target_item.get("explanation", ""),
        }
        lost_pts = baskets.get(turn_pid, 0)
        baskets[turn_pid] = 0
        statuses[turn_pid] = "busted"
        append_event(
            state,
            "System",
            f"💥 BUST! {active_turn_player['name']} opened #{slot} ({target_item['label']}): WRONG! Lost {lost_pts} round pts and is OUT for this card.",
            kind="bust",
        )

    # Check if all items revealed
    if len(revealed) >= len(items):
        _finish_round(state)
    else:
        _advance_turn(state)

    save_game(code, state)
    return True, "Capsule picked.", state


def pass_turn(code: str, player_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None

    if state.get("phase") != "playing":
        return False, "Game is not currently active.", state

    cur_pid = state.get("current_player_id")
    is_single_device = state.get("settings", {}).get("mode") == "single_device"

    player = next((p for p in state.get("players", []) if p["id"] == player_id), None)
    if not player:
        return False, "Player not found.", state

    if not is_single_device and cur_pid != player_id and not player.get("is_admin"):
        return False, "It is not your turn to pass!", state

    active_turn_player = next((p for p in state.get("players", []) if p["id"] == cur_pid), player)
    turn_pid = active_turn_player["id"]

    statuses = state.setdefault("player_statuses", {})
    if statuses.get(turn_pid) != "active":
        return False, f"{active_turn_player['name']} is already passed or busted.", state

    baskets = state.setdefault("round_baskets", {})
    pts = baskets.get(turn_pid, 0)
    active_turn_player["score"] += pts
    baskets[turn_pid] = 0
    statuses[turn_pid] = "passed"

    append_event(
        state,
        "System",
        f"🔒 {active_turn_player['name']} passed and banked +{pts} points! (Total: {active_turn_player['score']} pts)",
        kind="pass",
    )

    _advance_turn(state)
    save_game(code, state)
    return True, "Turn passed.", state


def host_arbitrate(
    code: str,
    slot: int,
    mark_correct: bool,
    target_player_id: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Host manually overrides capsule outcome or validates an answer."""
    state = get_game(code)
    if not state:
        return False, "Room not found.", None

    card = state.get("card") or {}
    items = card.get("items", [])
    target_item = next((it for it in items if it["slot"] == slot), None)
    if not target_item:
        return False, f"Capsule #{slot} not found.", state

    revealed = state.setdefault("revealed_capsules", {})
    s_str = str(slot)

    target_player = next((p for p in state.get("players", []) if p["id"] == target_player_id), None)
    revealed_by_name = target_player["name"] if target_player else "Host Override"

    revealed[s_str] = {
        "slot": slot,
        "label": target_item["label"],
        "value": target_item["value"],
        "is_correct": mark_correct,
        "revealed_by": revealed_by_name,
        "revealed_result": "correct" if mark_correct else "wrong",
        "explanation": target_item.get("explanation", ""),
    }

    if target_player:
        pid = target_player["id"]
        baskets = state.setdefault("round_baskets", {})
        statuses = state.setdefault("player_statuses", {})
        if mark_correct:
            baskets[pid] = baskets.get(pid, 0) + 1
            statuses[pid] = "active"
            append_event(
                state,
                "Host",
                f"👑 Host validated #{slot} ({target_item['label']}) for {target_player['name']} as CORRECT (+1 pt).",
            )
        else:
            baskets[pid] = 0
            statuses[pid] = "busted"
            append_event(
                state,
                "Host",
                f"👑 Host marked #{slot} ({target_item['label']}) for {target_player['name']} as WRONG (Bust).",
            )

    if len(revealed) >= len(items):
        _finish_round(state)
    else:
        _advance_turn(state)

    save_game(code, state)
    return True, f"Capsule #{slot} arbitrated by Host.", state


def process_chat_answer(code: str, player_id: str, text: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Inspects chat input for matching covered capsule labels or aliases."""
    state = get_game(code)
    if not state or state.get("phase") != "playing":
        return False, "Not in playing phase.", state

    clean = text.strip().lower()
    if not clean or len(clean) < 2:
        return False, "Text too short.", state

    card = state.get("card") or {}
    items = card.get("items", [])
    revealed = state.get("revealed_capsules", {})

    unrevealed_items = [it for it in items if str(it["slot"]) not in revealed]
    matched_item = None

    for it in unrevealed_items:
        # Check slot number (e.g. "slot 1" or "#1" or "1")
        if clean in (str(it["slot"]), f"#{it['slot']}", f"slot {it['slot']}"):
            matched_item = it
            break
        # Check label
        if clean == it["label"].strip().lower() or clean in it["label"].strip().lower():
            matched_item = it
            break
        # Check aliases
        aliases = [a.lower() for a in it.get("aliases", [])]
        if clean in aliases:
            matched_item = it
            break

    if not matched_item:
        return False, "No matching unrevealed capsule found.", state

    # Found a matching capsule! Try picking it
    prediction = "yes"
    if "no" in clean or "false" in clean:
        prediction = "no"

    return pick_capsule(code, player_id, matched_item["slot"], prediction=prediction)


def next_round(code: str) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None

    if state.get("phase") not in ("round_summary", "playing"):
        return False, "Cannot advance to next round from current phase.", state

    card = _deal_next_card(state)
    if not card:
        return False, "No questions available in deck.", state

    state["phase"] = "playing"
    state["round_num"] = state.get("round_num", 0) + 1
    state["card"] = card
    state["revealed_capsules"] = {}

    players = [p for p in state.get("players", []) if not p.get("is_spectator")]
    # Rotate starting player each round
    turn_order = state.get("turn_order", [])
    if turn_order:
        turn_order = turn_order[1:] + turn_order[:1]
    else:
        turn_order = [p["id"] for p in players]
    state["turn_order"] = turn_order
    state["current_player_id"] = turn_order[0] if turn_order else None
    state["player_statuses"] = {pid: "active" for pid in turn_order}
    state["round_baskets"] = {pid: 0 for pid in turn_order}

    append_event(state, "System", f"➡️ Next Card #{state['round_num']}: {card['prompt']}", kind="start")
    save_game(code, state)
    return True, "Advanced to next card.", state


def reset_game(code: str) -> tuple[bool, str, dict[str, Any] | None]:
    state = get_game(code)
    if not state:
        return False, "Room not found.", None

    state["phase"] = "lobby"
    state["round_num"] = 0
    state["card"] = None
    state["revealed_capsules"] = {}
    state["current_player_id"] = None
    state["turn_order"] = []
    state["player_statuses"] = {}
    state["round_baskets"] = {}
    state["winner_id"] = None
    state["winner_name"] = None
    state["winner_reason"] = None

    for p in state.get("players", []):
        p["score"] = 0

    append_event(state, "System", "🔄 Room returned to lobby for a new match.")
    save_game(code, state)
    return True, "Reset to lobby.", state


def get_sanitized_player_view(state: dict[str, Any], viewer_id: str | None = None) -> dict[str, Any]:
    """Sanitizes game state to prevent cheating via DevTools inspection."""
    view = {
        "code": state.get("code"),
        "phase": state.get("phase"),
        "settings": state.get("settings", {}),
        "round_num": state.get("round_num", 0),
        "players": state.get("players", []),
        "current_player_id": state.get("current_player_id"),
        "turn_order": state.get("turn_order", []),
        "player_statuses": state.get("player_statuses", {}),
        "round_baskets": state.get("round_baskets", {}),
        "winner_id": state.get("winner_id"),
        "winner_name": state.get("winner_name"),
        "winner_reason": state.get("winner_reason"),
        "chat_log": state.get("chat_log", []),
    }

    viewer = next((p for p in state.get("players", []) if p["id"] == viewer_id), None)
    view["viewer"] = viewer
    view["is_admin"] = bool(viewer and viewer.get("is_admin"))

    card = state.get("card")
    phase = state.get("phase", "lobby")
    revealed_caps = state.get("revealed_capsules", {})

    if not card:
        view["card"] = None
        view["capsules"] = []
        return view

    # In lobby or playing phase, conceal secret answer details of unrevealed items
    is_revealed_all = phase in ("round_summary", "gameover")

    sanitized_capsules = []
    for it in card.get("items", []):
        s_str = str(it["slot"])
        rev = revealed_caps.get(s_str)
        if rev:
            sanitized_capsules.append(
                {
                    "slot": it["slot"],
                    "label": it["label"],
                    "value": it["value"],
                    "is_correct": rev["is_correct"],
                    "revealed": True,
                    "revealed_by": rev.get("revealed_by"),
                    "revealed_result": rev.get("revealed_result"),
                    "explanation": rev.get("explanation", ""),
                }
            )
        elif is_revealed_all:
            sanitized_capsules.append(
                {
                    "slot": it["slot"],
                    "label": it["label"],
                    "value": it["value"],
                    "is_correct": it["is_correct"],
                    "revealed": True,
                    "revealed_by": "Board",
                    "revealed_result": "unpicked",
                    "explanation": it.get("explanation", ""),
                }
            )
        else:
            # Masked unpicked capsule
            sanitized_capsules.append(
                {
                    "slot": it["slot"],
                    "label": it["label"],
                    "value": None,
                    "is_correct": None,
                    "revealed": False,
                    "revealed_by": None,
                    "revealed_result": None,
                    "explanation": None,
                }
            )

    view["card"] = {
        "id": card.get("id"),
        "pack": card.get("pack"),
        "prompt": card.get("prompt"),
        "type": card.get("type"),
        "n": card.get("n", len(sanitized_capsules)),
    }
    view["capsules"] = sanitized_capsules
    return view

"""Secret Santa & Target Matcher Game State Engine.

Redis-backed state machine and target pairing logic:
- Zero-spoiler sanitization: Players only ever receive their own assigned target.
- Derangement & Hamiltonian Cycle matching algorithm with custom exclusion rules.
- Multi-theme presets: Secret Santa, Secret Assassin, Secret Buddy / Angel, Custom.
- Support for offline / couch participants (Pass & Play / shared device).
- Real-time wishlist and preference synchronization.
"""

import copy
import json
import logging
import random
import time
import uuid
from typing import Any

from django.core.cache import cache

from gamerooms.player_colors import assign_distinct_player_color, get_player_initials

logger = logging.getLogger(__name__)

REDIS_PREFIX = "secretsanta:game:"
ROOM_EXPIRY_SECONDS = 86400 * 30  # 30 days (gift exchanges often span weeks)

DEFAULT_SETTINGS = {
    "theme": "secretsanta",  # "secretsanta" | "assassin" | "buddy" | "custom"
    "custom_title": "Secret Santa",
    "custom_prompt": "Give a thoughtful gift to your assigned person!",
    "budget": "20€ / $20",
    "event_date": "",
    "notes_placeholder": "Wishlist items, favorite treats, sizes, allergies, hints...",
}

THEMES: dict[str, dict[str, str]] = {
    "secretsanta": {
        "id": "secretsanta",
        "name": "Secret Santa",
        "icon": "🎁",
        "role_name": "Secret Santa",
        "target_label": "Your Secret Gift Recipient",
        "action_prompt": "You are giving a gift to:",
        "notes_label": "Wishlist & Preferences",
        "notes_placeholder": "Favorite treats, book genres, hobbies, sizes, allergies...",
        "default_budget": "20€ / $20",
    },
    "assassin": {
        "id": "assassin",
        "name": "Secret Assassin",
        "icon": "🎯",
        "role_name": "Secret Agent",
        "target_label": "Your Assassination Target",
        "action_prompt": "Your secret target is:",
        "notes_label": "Secret Trigger Word / Tag Notes",
        "notes_placeholder": "Location hints, secret trigger word, elimination condition...",
        "default_budget": "",
    },
    "buddy": {
        "id": "buddy",
        "name": "Secret Buddy / Angel",
        "icon": "🤝",
        "role_name": "Secret Angel",
        "target_label": "Your Secret Buddy",
        "action_prompt": "You are looking after:",
        "notes_label": "Kindness Preferences & Likes",
        "notes_placeholder": "Favorite snacks, coffee order, music, little pick-me-ups...",
        "default_budget": "Acts of kindness",
    },
    "custom": {
        "id": "custom",
        "name": "Custom Match",
        "icon": "🎲",
        "role_name": "Participant",
        "target_label": "Your Assigned Match",
        "action_prompt": "Your assigned pair is:",
        "notes_label": "Notes / Preferences",
        "notes_placeholder": "Preferences, availability, topic ideas, guidelines...",
        "default_budget": "",
    },
}


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


def create_game(code: str, title: str = "", creator_token: str = "") -> dict[str, Any]:
    state = {
        "code": code.upper(),
        "title": title or "Secret Santa & Target Matcher",
        "created_at": time.time(),
        "phase": "lobby",  # "lobby" | "matched"
        "matched_at": None,
        "creator_token": creator_token,
        "settings": copy.deepcopy(DEFAULT_SETTINGS),
        "players": {},  # pid -> player dict
        "matches": {},  # giver_pid -> receiver_pid (SERVER ONLY)
        "exclusions": {},  # pid -> list of forbidden target_pids
        "chat_log": [],
    }
    save_game(code, state)
    return state


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
    if len(chat_log) > 100:
        state["chat_log"] = chat_log[-100:]
    return entry


def find_player_by_token(state: dict[str, Any], token: str | None) -> dict[str, Any] | None:
    if not token or not state:
        return None
    players = state.get("players", {})
    if isinstance(players, dict):
        for p in players.values():
            if p.get("token") == token:
                return p
    elif isinstance(players, list):
        for p in players:
            if p.get("token") == token:
                return p
    return None


def find_player_by_name(state: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    if not name or not state:
        return None
    lowered = name.strip().lower()
    players = state.get("players", {})
    if isinstance(players, dict):
        for p in players.values():
            if p.get("name", "").strip().lower() == lowered:
                return p
    elif isinstance(players, list):
        for p in players:
            if p.get("name", "").strip().lower() == lowered:
                return p
    return None


def find_player_by_id(state: dict[str, Any], pid: str | None) -> dict[str, Any] | None:
    if not pid or not state:
        return None
    players = state.get("players", {})
    if isinstance(players, dict):
        return players.get(pid)
    elif isinstance(players, list):
        for p in players:
            if p.get("id") == pid:
                return p
    return None


def is_player_admin(state: dict[str, Any], player: dict[str, Any] | None) -> bool:
    if not player:
        return False
    if player.get("is_admin"):
        return True
    if state.get("creator_token") and player.get("token") == state.get("creator_token"):
        return True
    # If no admin exists in player list, first non-offline player is admin
    players = state.get("players", {})
    player_list = list(players.values()) if isinstance(players, dict) else players
    admins = [p for p in player_list if p.get("is_admin")]
    if not admins and player_list and player_list[0].get("id") == player.get("id"):
        return True
    return False


def add_player(
    state: dict[str, Any],
    name: str,
    token: str | None = None,
    is_admin: bool = False,
    is_offline: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Add a player or reconnect an existing player."""
    clean_name = name.strip()[:40] or "Participant"
    if not isinstance(state.get("players"), dict):
        state["players"] = {}

    existing = find_player_by_token(state, token) if token else None
    if existing:
        existing["connected"] = True
        if is_admin:
            existing["is_admin"] = True
        save_game(state["code"], state)
        return state, existing, False

    by_name = find_player_by_name(state, clean_name)
    if by_name and not is_offline:
        by_name["connected"] = True
        if token:
            by_name["token"] = token
        if is_admin:
            by_name["is_admin"] = True
        save_game(state["code"], state)
        return state, by_name, False

    pid = f"p_{uuid.uuid4().hex[:8]}"
    player_token = token or str(uuid.uuid4())
    color = assign_distinct_player_color(list(state["players"].values()))
    initials = get_player_initials(clean_name)

    # First connected player becomes admin if none set
    is_first = len(state["players"]) == 0
    assigned_admin = is_admin or is_first

    player = {
        "id": pid,
        "name": clean_name,
        "token": player_token,
        "color": color,
        "initials": initials,
        "is_admin": assigned_admin,
        "is_offline": is_offline,
        "connected": not is_offline,
        "wishlist": "",
        "target_id": None,
    }

    state["players"][pid] = player
    save_game(state["code"], state)
    return state, player, True


def add_offline_player(state: dict[str, Any], name: str, added_by_name: str = "") -> dict[str, Any]:
    """Add an offline/couch player on behalf of the host."""
    clean_name = name.strip()[:40] or "Guest"
    state, player, is_new = add_player(
        state=state,
        name=clean_name,
        token=str(uuid.uuid4()),
        is_admin=False,
        is_offline=True,
    )
    msg = f"➕ {clean_name} was added as an offline / couch player"
    if added_by_name:
        msg += f" by {added_by_name}"
    append_event(state, "System", msg, kind="system")
    save_game(state["code"], state)
    return player


def remove_player(state: dict[str, Any], player_id: str) -> bool:
    """Remove a player from the game. Resets matches if already drawn."""
    players = state.get("players", {})
    if player_id not in players:
        return False

    name = players[player_id].get("name", "Player")
    del players[player_id]

    # Clean up exclusions
    exclusions = state.get("exclusions", {})
    if player_id in exclusions:
        del exclusions[player_id]
    for pid, forbidden in list(exclusions.items()):
        if player_id in forbidden:
            exclusions[pid] = [x for x in forbidden if x != player_id]

    # If already matched, matching is broken; reset to lobby
    if state.get("phase") == "matched":
        reset_to_lobby(state)
        append_event(
            state,
            "System",
            f"⚠️ {name} left. Matches were reset back to the lobby.",
            kind="warning",
        )
    else:
        append_event(state, "System", f"👋 {name} was removed from the room.", kind="system")

    save_game(state["code"], state)
    return True


def change_player_color(state: dict[str, Any], player_id: str, new_color: str) -> bool:
    player = find_player_by_id(state, player_id)
    if not player:
        return False
    player["color"] = new_color
    save_game(state["code"], state)
    return True


def update_wishlist(state: dict[str, Any], player_id: str, wishlist_text: str) -> bool:
    player = find_player_by_id(state, player_id)
    if not player:
        return False
    player["wishlist"] = (wishlist_text or "").strip()[:1000]
    save_game(state["code"], state)
    return True


def set_player_exclusions(state: dict[str, Any], player_id: str, excluded_pids: list[str]) -> bool:
    """Set the list of player IDs that player_id cannot be assigned to give a gift to."""
    if player_id not in state.get("players", {}):
        return False
    valid_pids = [pid for pid in excluded_pids if pid in state.get("players", {}) and pid != player_id]
    state.setdefault("exclusions", {})[player_id] = valid_pids
    save_game(state["code"], state)
    return True


def update_settings(state: dict[str, Any], new_settings: dict[str, Any]) -> None:
    settings = state.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))
    theme = new_settings.get("theme")
    if theme in THEMES:
        settings["theme"] = theme
        theme_cfg = THEMES[theme]
        if "custom_title" not in new_settings or not new_settings["custom_title"]:
            settings["custom_title"] = theme_cfg["name"]
        if "budget" not in new_settings:
            settings["budget"] = theme_cfg.get("default_budget", "")

    for field in ("custom_title", "custom_prompt", "budget", "event_date", "notes_placeholder"):
        if field in new_settings:
            settings[field] = str(new_settings[field]).strip()[:150]

    save_game(state["code"], state)


def solve_matching(
    pids: list[str],
    exclusions: dict[str, list[str]],
    prefer_single_cycle: bool = True,
) -> tuple[bool, Any]:
    """Derangement / Hamiltonian Cycle matching engine.

    Guarantees:
    - Every player gives to exactly 1 recipient.
    - Every player receives from exactly 1 giver.
    - Nobody gives to themselves: target(p) != p.
    - Exclusion rules: target(p) not in exclusions[p].
    - Prefers a single Hamiltonian cycle to avoid isolated 2-cycles when N >= 3.
    """
    n = len(pids)
    if n < 2:
        return False, "At least 2 participants are needed to draw secret targets."

    all_pids = set(pids)
    valid_targets: dict[str, list[str]] = {}

    for p in pids:
        excl = set(exclusions.get(p, [])) | {p}
        allowed = list(all_pids - excl)
        if not allowed:
            return False, "Participant has excluded all available targets. Please relax exclusions."
        valid_targets[p] = allowed

    # Check receiver side coverage
    for target in pids:
        potential_givers = [p for p in pids if target in valid_targets[p]]
        if not potential_givers:
            return False, "No participant is permitted to give a gift to one of the players. Please relax exclusions."

    # Strategy 1: Random Hamiltonian Cycle (ideal for Secret Santa)
    if prefer_single_cycle and n >= 2:
        for _ in range(400):
            shuffled = list(pids)
            random.shuffle(shuffled)
            path = [shuffled[0]]
            used = {shuffled[0]}
            possible = True
            for _ in range(n - 1):
                curr = path[-1]
                cand = [t for t in valid_targets[curr] if t not in used]
                if not cand:
                    possible = False
                    break
                nxt = random.choice(cand)
                path.append(nxt)
                used.add(nxt)
            if possible:
                # Check closing edge: path[-1] -> path[0]
                if path[0] in valid_targets[path[-1]]:
                    matches = {}
                    for i in range(n - 1):
                        matches[path[i]] = path[i + 1]
                    matches[path[-1]] = path[0]
                    return True, matches

    # Strategy 2: Randomized Backtracking with MRV (Minimum Remaining Values)
    # Handles complex disjoint exclusion graphs where a single cycle is impossible
    shuffled_pids = list(pids)
    random.shuffle(shuffled_pids)
    shuffled_pids.sort(key=lambda p: len(valid_targets[p]))

    assigned_targets: set[str] = set()
    result_matches: dict[str, str] = {}

    def backtrack(idx: int) -> bool:
        if idx == len(shuffled_pids):
            return True
        giver = shuffled_pids[idx]
        candidates = [t for t in valid_targets[giver] if t not in assigned_targets]
        random.shuffle(candidates)
        # When N >= 4, prioritize candidates that don't create immediate 2-cycles
        if n >= 4:
            candidates.sort(key=lambda c: 1 if (c in result_matches and result_matches[c] == giver) else 0)

        for cand in candidates:
            result_matches[giver] = cand
            assigned_targets.add(cand)
            if backtrack(idx + 1):
                return True
            assigned_targets.remove(cand)
            del result_matches[giver]
        return False

    if backtrack(0):
        return True, result_matches

    return False, "Could not find a valid matching with the current exclusions. Please relax some exclusions."


def generate_matches(state: dict[str, Any]) -> tuple[bool, str]:
    """Execute the matching draw for all active players in the room."""
    players = state.get("players", {})
    pids = list(players.keys())

    if len(pids) < 2:
        return False, "At least 2 participants are needed to generate matches."

    exclusions = state.get("exclusions", {})
    success, result = solve_matching(pids, exclusions)

    if not success:
        return False, str(result)

    matches: dict[str, str] = result
    state["matches"] = matches
    state["phase"] = "matched"
    state["matched_at"] = time.time()

    # Assign target_id to each player
    for giver_id, receiver_id in matches.items():
        if giver_id in players:
            players[giver_id]["target_id"] = receiver_id

    theme_cfg = THEMES.get(state.get("settings", {}).get("theme", "secretsanta"), THEMES["secretsanta"])
    append_event(
        state,
        "System",
        f"🎉 {theme_cfg['icon']} {theme_cfg['name']} targets have been secretly assigned! "
        f"Touch or click your secret card to peek at your target.",
        kind="celebration",
    )
    save_game(state["code"], state)
    return True, "Matches successfully drawn."


def reset_to_lobby(state: dict[str, Any]) -> None:
    """Reset matched state back to lobby without removing players."""
    state["phase"] = "lobby"
    state["matched_at"] = None
    state["matches"] = {}
    for p in state.get("players", {}).values():
        p["target_id"] = None
    append_event(state, "System", "🔄 Room has been returned to the lobby for new match drawing.", kind="system")
    save_game(state["code"], state)


def reveal_all_admin(state: dict[str, Any], requester_id: str) -> tuple[bool, Any]:
    """Emergency host-only function to view all assignments (e.g. for organizer logistics)."""
    player = find_player_by_id(state, requester_id)
    if not is_player_admin(state, player):
        return False, "Only room organizers can request a master reveal."

    matches = state.get("matches", {})
    players = state.get("players", {})
    table = []
    for giver_id, target_id in matches.items():
        giver = players.get(giver_id, {})
        target = players.get(target_id, {})
        table.append(
            {
                "giver_id": giver_id,
                "giver_name": giver.get("name", "Unknown"),
                "target_id": target_id,
                "target_name": target.get("name", "Unknown"),
                "target_wishlist": target.get("wishlist", ""),
            }
        )

    return True, table


def get_sanitized_player_view(state: dict[str, Any], viewer_id: str | None = None) -> dict[str, Any]:
    """Strict Zero-Spoiler View Projection.

    Rules:
    - NEVER expose state["matches"]
    - NEVER expose other players' "target_id"
    - ONLY populate "my_target" with the viewer's target when phase == "matched"
    - Include couch/offline player targets ONLY if the viewer is an admin inspecting that couch card
    """
    settings = copy.deepcopy(state.get("settings", DEFAULT_SETTINGS))
    theme_key = settings.get("theme", "secretsanta")
    theme_cfg = THEMES.get(theme_key, THEMES["secretsanta"])

    view: dict[str, Any] = {
        "code": state.get("code"),
        "title": state.get("title"),
        "phase": state.get("phase", "lobby"),
        "matched_at": state.get("matched_at"),
        "settings": settings,
        "theme_info": theme_cfg,
        "chat_log": state.get("chat_log", []),
        "player_count": len(state.get("players", {})),
        "themes_available": THEMES,
    }

    # Public player roster: zero spoiler, no target_id
    players_dict = state.get("players", {})
    public_players = []
    for pid, p in players_dict.items():
        public_players.append(
            {
                "id": pid,
                "name": p.get("name"),
                "color": p.get("color"),
                "initials": p.get("initials"),
                "is_admin": p.get("is_admin", False),
                "is_offline": p.get("is_offline", False),
                "connected": p.get("connected", False),
                "has_wishlist": bool(p.get("wishlist", "").strip()),
            }
        )
    view["players"] = public_players
    view["exclusions"] = state.get("exclusions", {})

    viewer = players_dict.get(viewer_id) if viewer_id else None
    if viewer:
        view["me"] = {
            "id": viewer["id"],
            "name": viewer["name"],
            "token": viewer["token"],
            "color": viewer["color"],
            "initials": viewer["initials"],
            "is_admin": is_player_admin(state, viewer),
            "is_offline": viewer.get("is_offline", False),
            "wishlist": viewer.get("wishlist", ""),
        }

        # Zero-spoiler target projection:
        if state.get("phase") == "matched" and viewer.get("target_id"):
            target = players_dict.get(viewer["target_id"])
            if target:
                view["my_target"] = {
                    "id": target["id"],
                    "name": target["name"],
                    "color": target.get("color"),
                    "initials": target.get("initials"),
                    "wishlist": target.get("wishlist", ""),
                    "is_offline": target.get("is_offline", False),
                }
            else:
                view["my_target"] = None
        else:
            view["my_target"] = None

        # For offline / couch participants:
        # If the viewer is admin or it's couch mode, allow viewing offline cards
        offline_targets = {}
        if view["me"]["is_admin"] and state.get("phase") == "matched":
            for pid, p in players_dict.items():
                if p.get("is_offline") and p.get("target_id"):
                    t = players_dict.get(p["target_id"])
                    if t:
                        offline_targets[pid] = {
                            "player_name": p.get("name"),
                            "target_name": t.get("name"),
                            "target_color": t.get("color"),
                            "target_initials": t.get("initials"),
                            "target_wishlist": t.get("wishlist", ""),
                        }
        view["offline_targets"] = offline_targets
    else:
        view["me"] = None
        view["my_target"] = None
        view["offline_targets"] = {}

    return view

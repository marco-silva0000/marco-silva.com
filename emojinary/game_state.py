"""Game state, smart guess evaluation, and replay engine for Emojinary."""

import copy
import difflib
import json
import os
import random
import re
import time
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Optional

import emoji
import redis

_redis = None
_LEXICON_CACHE: dict[str, dict[str, Any]] | None = None
_LEXICON_PATH = Path(__file__).resolve().parent / "data" / "wiktionary_lexicon.json"

DEFAULT_LEXICON_FALLBACK: dict[str, dict[str, Any]] = {
    "sofa": {
        "pos": "noun",
        "definition": "An upholstered seat with a raised back and armrests.",
        "aliases": ["couch", "settee", "divan"],
        "translations": {"pt": ["sofá"], "el": ["καναπές"], "fi": ["sohva"], "es": ["sofá"]},
    },
    "apple": {
        "pos": "noun",
        "definition": "A common, firm, round fruit produced by a tree of the genus Malus.",
        "aliases": ["malus"],
        "translations": {"pt": ["maçã"], "el": ["μήλο"], "fi": ["omena"], "es": ["manzana"]},
    },
}


def get_word_lexicon(word: Optional[str]) -> dict[str, Any]:
    """Load Wiktionary lexical metadata (definition, aliases, translations, topics) for a word."""
    global _LEXICON_CACHE
    if _LEXICON_CACHE is None:
        if _LEXICON_PATH.exists():
            try:
                with open(_LEXICON_PATH, "r", encoding="utf-8") as f:
                    _LEXICON_CACHE = json.load(f)
            except Exception:
                _LEXICON_CACHE = {}
        else:
            _LEXICON_CACHE = {}
    if not word:
        return {}
    key = word.strip().lower()
    return _LEXICON_CACHE.get(key) or DEFAULT_LEXICON_FALLBACK.get(key, {})


def sanitize_emoji_only(text: Optional[str]) -> str:
    """Extract only valid Unicode emoji grapheme clusters, stripping all regular text/letters/numbers."""
    if not text:
        return ""
    return "".join(item["emoji"] for item in emoji.emoji_list(str(text)))


DEFAULT_SETTINGS = {
    "max_rounds": 10,
    "emoji_timer": 60,  # seconds for emoji picking / prep phase (0 = unlimited)
    "guess_timer": 60,  # seconds for guessing phase (0 = unlimited)
    "chat_mode": "public",  # "public" (everyone sees wrong guesses) or "private"
    "difficulty": 0,  # 0=all, 1=easy, 2=medium, 3=hard
    "categories": ["all"],  # ["all"] or subset of ["movie", "phrase", "song", "tvshow", "thing"]
    "end_on_first_guess": False,  # True = round ends on 1st correct guess; False = all can guess
    "allow_rerolls": 2,  # max word rerolls per turn
    "allow_custom_words": False,  # allow clue-giver to enter custom word in round_robin/collective
}

SETTINGS_PRESETS = {
    "standard": {
        "label": "🎯 Standard Party",
        "description": "Classic Round Robin with live emoji hints and public chat guesses.",
        "mode": "round_robin",
        "settings": {
            "max_rounds": 8,
            "emoji_timer": 60,
            "guess_timer": 60,
            "chat_mode": "public",
            "difficulty": 0,
            "end_on_first_guess": False,
            "allow_rerolls": 2,
            "allow_custom_words": False,
        },
    },
    "collective_fast": {
        "label": "⚡ Collective Fast-Play",
        "description": "Everyone crafts their initial emoji clue at the same time, then guess each round back-to-back with live extra hints!",
        "mode": "collective",
        "settings": {
            "max_rounds": 8,
            "emoji_timer": 60,
            "guess_timer": 60,
            "chat_mode": "public",
            "difficulty": 0,
            "end_on_first_guess": False,
            "allow_rerolls": 2,
            "allow_custom_words": False,
        },
    },
    "best_guess_party": {
        "label": "🏆 Judge's Pick (Best Emoji)",
        "description": "One player sets the prompt, everyone submits their funniest emoji combo, and the judge picks the winner.",
        "mode": "best_guess",
        "settings": {
            "max_rounds": 8,
            "emoji_timer": 60,
            "guess_timer": 60,
            "chat_mode": "public",
            "difficulty": 0,
            "end_on_first_guess": False,
            "allow_rerolls": 3,
            "allow_custom_words": True,
        },
    },
    "speed_blitz": {
        "label": "🔥 Speed Blitz (First Guess Wins)",
        "description": "Fast 30s timers where the first correct guess immediately wins the round!",
        "mode": "round_robin",
        "settings": {
            "max_rounds": 10,
            "emoji_timer": 30,
            "guess_timer": 30,
            "chat_mode": "public",
            "difficulty": 1,
            "end_on_first_guess": True,
            "allow_rerolls": 1,
            "allow_custom_words": False,
        },
    },
}


def _get_redis():
    global _redis
    if _redis is None:
        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        _redis = redis.from_url(url, decode_responses=True)
    return _redis


get_redis_client = _get_redis
_fallback_store: dict[str, str] = {}


def _key(code: str) -> str:
    return f"emojinary:game:{code.upper()}"


def create_initial_state(
    code: str,
    title: str = "Emojinary Night",
    password: str = "",
    creator_name: str = "",
    mode: str = "round_robin",
    settings: Optional[dict] = None,
) -> dict[str, Any]:
    """Create a fresh Emojinary game state dictionary."""
    merged_settings = copy.deepcopy(DEFAULT_SETTINGS)
    if settings:
        merged_settings.update(settings)

    return {
        "code": code.upper(),
        "title": title,
        "password": password,
        "admin_token": uuid.uuid4().hex[:16],
        "status": "open",  # open, running, finished
        "players": {},  # player_id -> {id, name, token, score, is_admin, is_spectator, connected, channel_name}
        "next_player_seq": 1,
        "turn_order": [],  # list of player_ids
        "current_turn": 0,
        "current_word": None,
        "current_category": None,
        "current_difficulty": 1,
        "emoji_clue": "",
        "emoji_hints": [],  # list of {"hint_num": int, "emoji": str, "elapsed_sec": float}
        "round_num": 0,
        "started": False,
        "guessed": [],  # list of player_ids who guessed correctly this round
        "current_attempts": [],  # chronological attempts in current round
        "rerolls_used": 0,
        "used_words": [],
        "creator": creator_name or None,
        "creator_id": None,
        "history": [],  # [{emoji, word, category, guesser, round, mode, emoji_hints, attempts}]
        "rounds_history": [],  # full detailed round records for interactive replay
        "chat_log": [],  # chronological activity & chat feed
        "next_chat_id": 1,
        "settings": merged_settings,
        "phase": "lobby",  # lobby, prep, emoji, guess, picking, submitting, judging, round_end, gameover
        "mode": mode if mode in ("round_robin", "collective", "best_guess") else "round_robin",
        "turn_start_time": None,
        "timer_duration": 0,
        "timer_ends_at": None,
        "timer_paused_remaining": None,
        "submissions": {},  # player_id -> emoji (for best_guess mode)
        "collective_queue": {},  # player_id -> {word, category, difficulty, emoji_clue, submitted, rerolls_used}
        "collective_order": [],  # ordered list of player_ids whose clues will be played in collective mode
        "collective_index": 0,
        "next_room_code": None,
        "created_at": time.time(),
    }


def _ensure_state_schema(code: str, state: dict[str, Any]) -> dict[str, Any]:
    """Ensure backwards compatibility with older Redis states or test fixtures."""
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
    if data:
        state = json.loads(data)
        return _ensure_state_schema(code, state)
    return create_initial_state(code=code)


def save_game(code: str, state: dict[str, Any]) -> None:
    r = _get_redis()
    payload = json.dumps(state)
    try:
        r.set(_key(code), payload, ex=86400)
    except Exception:
        _fallback_store[_key(code)] = payload


def delete_game(code: str) -> None:
    r = _get_redis()
    try:
        r.delete(_key(code))
    except Exception:
        _fallback_store.pop(_key(code), None)


def sync_room_db_status(code: str, status: str) -> None:
    """Synchronize the gamerooms.Room database status ('open', 'running', 'finished')."""
    try:
        from gamerooms.models import Room

        Room.objects.filter(code=code.upper()).update(status=status)
    except Exception:
        pass


# ============================================================================
# Chat & Activity Stream Logging
# ============================================================================


def append_chat_event(
    state: dict[str, Any],
    kind: str,
    text: str,
    player_id: Optional[str] = None,
    player_name: Optional[str] = None,
    emoji: Optional[str] = None,
    points: Optional[int] = None,
    private_to: Optional[list[str]] = None,
    masked_text: Optional[str] = None,
) -> dict[str, Any]:
    """Append an action, attempt, hint, or chat message to the unified room stream."""
    chat_id = state.get("next_chat_id", 1)
    state["next_chat_id"] = chat_id + 1
    entry = {
        "id": chat_id,
        "timestamp": round(time.time(), 2),
        "round": state.get("round_num", 0),
        "phase": state.get("phase", "lobby"),
        "kind": kind,  # system, chat, guess_wrong, guess_close, guess_correct, emoji_hint, round_start, round_end
        "player_id": player_id,
        "player_name": player_name,
        "text": text,
        "emoji": emoji,
        "points": points,
        "private_to": private_to,  # if set, only these player_ids see `text`; others see `masked_text`
        "masked_text": masked_text,
    }
    log = state.setdefault("chat_log", [])
    log.append(entry)
    if len(log) > 250:
        state["chat_log"] = log[-250:]
    return entry


# ============================================================================
# Player Identity, Reconnect, Rename & Admin Management
# ============================================================================


def find_player_by_token(state: dict[str, Any], token: Optional[str]) -> Optional[dict[str, Any]]:
    if not token:
        return None
    for pid, p in state.get("players", {}).items():
        if p.get("token") == token:
            p.setdefault("id", pid)
            return p
    return None


def find_player_by_channel(state: dict[str, Any], channel_name: Optional[str]) -> Optional[dict[str, Any]]:
    if not channel_name:
        return None
    # Direct key match (legacy tests)
    if channel_name in state.get("players", {}):
        p = state["players"][channel_name]
        p.setdefault("id", channel_name)
        return p
    for pid, p in state.get("players", {}).items():
        if p.get("channel_name") == channel_name:
            p.setdefault("id", pid)
            return p
    return None


def find_player_by_name(state: dict[str, Any], name: Optional[str]) -> Optional[dict[str, Any]]:
    if not name:
        return None
    name_clean = name.strip().lower()
    for pid, p in state.get("players", {}).items():
        if p.get("name", "").strip().lower() == name_clean:
            p.setdefault("id", pid)
            return p
    return None


def add_player(
    state: dict[str, Any],
    name: str,
    token: Optional[str] = None,
    channel_name: Optional[str] = None,
    is_admin: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """
    Register or reconnect a player in the room.
    Returns (state, player_dict, is_new_player).
    """
    clean_name = (name or "Player").strip()[:40] or "Player"

    # 1. Check by secret token first
    existing = find_player_by_token(state, token)
    if existing:
        pid = existing["id"]
        existing["connected"] = True
        if channel_name:
            existing["channel_name"] = channel_name
        if is_admin:
            existing["is_admin"] = True
        save_game(state["code"], state)
        return state, existing, False

    # 2. Legacy reconnect by name ONLY for pre-revamp player records that never had a token.
    # Token-owning players can only be reclaimed with their secret token; otherwise anyone
    # typing the same display name could hijack that seat, score, and host rights.
    by_name = find_player_by_name(state, clean_name)
    if by_name and not by_name.get("token"):
        pid = by_name["id"]
        by_name["connected"] = True
        if channel_name:
            by_name["channel_name"] = channel_name
        by_name.setdefault("token", uuid.uuid4().hex[:16])
        by_name.setdefault("is_admin", by_name["name"] == state.get("creator"))
        by_name.setdefault("is_spectator", False)
        if pid not in state["turn_order"] and not by_name.get("is_spectator"):
            state["turn_order"].append(pid)
        save_game(state["code"], state)
        return state, by_name, False

    # 3. Ensure unique display name if another distinct token already owns that name
    base_name = clean_name
    suffix = 2
    while find_player_by_name(state, clean_name) is not None:
        clean_name = f"{base_name} ({suffix})"
        suffix += 1

    seq = state.get("next_player_seq", len(state["players"]) + 1)
    while f"p_{seq}" in state["players"]:
        seq += 1
    pid = f"p_{seq}"
    state["next_player_seq"] = seq + 1

    first_player = len(state["players"]) == 0 or not state.get("creator")
    player_is_admin = bool(is_admin or first_player)

    player = {
        "id": pid,
        "name": clean_name,
        "token": token or uuid.uuid4().hex[:16],
        "score": 0,
        "is_admin": player_is_admin,
        "is_spectator": False,
        "connected": True,
        "channel_name": channel_name,
        "joined_at": time.time(),
    }
    state["players"][pid] = player
    if not player["is_spectator"] and pid not in state["turn_order"]:
        state["turn_order"].append(pid)

    if first_player:
        state["creator"] = clean_name
        state["creator_id"] = pid

    # If joining mid-game during collective prep, deal them a word too
    if state.get("started") and state.get("mode") == "collective" and state.get("phase") == "prep":
        state.setdefault("collective_queue", {})[pid] = {
            "word": "Birthday party",
            "category": "thing",
            "difficulty": 1,
            "emoji_clue": "",
            "submitted": False,
            "rerolls_used": 0,
        }
        if pid not in state.setdefault("collective_order", []):
            state["collective_order"].append(pid)

    append_chat_event(
        state,
        kind="system",
        text=f"👋 {clean_name} joined the room",
        player_id=pid,
        player_name=clean_name,
    )
    save_game(state["code"], state)
    return state, player, True


def rename_player(state: dict[str, Any], player_id: str, new_name: str) -> tuple[bool, str]:
    """Rename a player while preserving their ID, score, turn order, and admin status."""
    if player_id not in state.get("players", {}):
        return False, "Player not found."
    clean = (new_name or "").strip()[:40]
    if not clean:
        return False, "Name cannot be empty."

    player = state["players"][player_id]
    old_name = player.get("name", "Player")
    if old_name == clean:
        return True, clean

    # Check collision with another player
    existing = find_player_by_name(state, clean)
    if existing and existing.get("id") != player_id:
        return False, "That name is already taken in this room."

    player["name"] = clean
    if state.get("creator_id") == player_id or state.get("creator") == old_name:
        state["creator"] = clean
        state["creator_id"] = player_id

    append_chat_event(
        state,
        kind="system",
        text=f"✨ {old_name} changed their name to {clean}",
        player_id=player_id,
        player_name=clean,
    )
    save_game(state["code"], state)
    return True, clean


def kick_player(state: dict[str, Any], target_id: str, by_name: str = "Host") -> Optional[str]:
    """Remove a player from the room and adjust turn order cleanly."""
    if target_id not in state.get("players", {}):
        return None
    removed = state["players"].pop(target_id)
    removed_name = removed.get("name", target_id)
    if target_id in state.get("turn_order", []):
        idx = state["turn_order"].index(target_id)
        state["turn_order"].remove(target_id)
        if state["turn_order"] and idx < state.get("current_turn", 0):
            state["current_turn"] = max(0, state["current_turn"] - 1)

    if target_id in state.get("guessed", []):
        state["guessed"].remove(target_id)
    state.get("submissions", {}).pop(target_id, None)
    state.get("collective_queue", {}).pop(target_id, None)
    if target_id in state.get("collective_order", []):
        state["collective_order"].remove(target_id)

    # Ensure at least one admin remains
    if removed.get("is_admin") and state["players"]:
        next_admin = next(iter(state["players"].values()))
        next_admin["is_admin"] = True
        state["creator"] = next_admin["name"]
        state["creator_id"] = next_admin["id"]

    append_chat_event(
        state,
        kind="system",
        text=f"🚪 {removed_name} was removed by {by_name}",
    )
    save_game(state["code"], state)
    return removed_name


def transfer_admin(state: dict[str, Any], target_id: str) -> bool:
    """Grant admin/host privileges to another player."""
    if target_id not in state.get("players", {}):
        return False
    target = state["players"][target_id]
    target["is_admin"] = True
    state["creator"] = target["name"]
    state["creator_id"] = target_id
    append_chat_event(
        state,
        kind="system",
        text=f"👑 {target['name']} is now a Room Host",
        player_id=target_id,
        player_name=target["name"],
    )
    save_game(state["code"], state)
    return True


def toggle_spectator(state: dict[str, Any], player_id: str) -> bool:
    """Toggle whether a player (e.g. Host) is spectating or active in the turn rotation."""
    if player_id not in state.get("players", {}):
        return False
    p = state["players"][player_id]
    p["is_spectator"] = not p.get("is_spectator", False)
    if p["is_spectator"]:
        if player_id in state["turn_order"]:
            state["turn_order"].remove(player_id)
        append_chat_event(state, kind="system", text=f"👁️ {p['name']} switched to Spectator mode", player_id=player_id)
    else:
        if player_id not in state["turn_order"]:
            state["turn_order"].append(player_id)
        append_chat_event(
            state, kind="system", text=f"🎮 {p['name']} joined the active player rotation", player_id=player_id
        )
    save_game(state["code"], state)
    return p["is_spectator"]


def current_player_id(state: dict[str, Any]) -> Optional[str]:
    """Return the player_id of the active clue-giver / picker."""
    if state.get("mode") == "collective" and state.get("phase") == "guess":
        order = state.get("collective_order", [])
        idx = state.get("collective_index", 0)
        if order and 0 <= idx < len(order):
            return order[idx]
    if not state.get("turn_order"):
        return None
    valid_order = [pid for pid in state["turn_order"] if pid in state.get("players", {})]
    if not valid_order:
        return None
    return valid_order[state.get("current_turn", 0) % len(valid_order)]


def current_player_channel(state: dict[str, Any]) -> Optional[str]:
    """Backwards-compatible helper returning active player's key/id."""
    return current_player_id(state)


def player_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return formatted player list sorted by turn order (or score on gameover)."""
    active_pid = current_player_id(state)
    creator = state.get("creator")
    guessed_set = set(state.get("guessed", []))
    submissions = state.get("submissions", {})
    collective_q = state.get("collective_queue", {})
    phase = state.get("phase", "lobby")

    result = []
    for pid, info in state.get("players", {}).items():
        is_creator = bool(info.get("is_admin") or info.get("name") == creator or pid == state.get("creator_id"))
        has_submitted = False
        if phase == "submitting":
            has_submitted = pid in submissions
        elif phase == "prep":
            has_submitted = bool(collective_q.get(pid, {}).get("submitted"))

        result.append(
            {
                "id": pid,
                "name": info.get("name", "Player"),
                "score": info.get("score", 0),
                "is_turn": pid == active_pid and phase not in ("lobby", "prep", "gameover"),
                "is_creator": is_creator,
                "is_admin": is_creator,
                "is_spectator": bool(info.get("is_spectator", False)),
                "connected": bool(info.get("connected", True)),
                "has_guessed": pid in guessed_set,
                "has_submitted": has_submitted,
            }
        )
    return result


# ============================================================================
# Smart Word Masking, Guess Evaluation & Spoiler Guard
# ============================================================================

_ARTICLES_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def _strip_combining_marks(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _normalize_phrase(text: str, strip_article: bool = False) -> str:
    s = (text or "").strip().lower()
    # Replace hyphens/slashes with spaces first, preserve non-Latin scripts while removing punctuation
    s = s.replace("-", " ").replace("/", " ").replace("&", " and ")
    s = _strip_combining_marks(s)
    s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    if strip_article:
        s = _ARTICLES_RE.sub("", s).strip()
    return s


def build_word_mask(word: Optional[str]) -> str:
    """
    Build a visual mask preserving word breaks and punctuation, plus word lengths.
    Example: 'The Lion King' -> '_ _ _   _ _ _ _   _ _ _ _  (3, 4, 4)'
    """
    if not word:
        return ""
    parts = word.split()
    masked_words = []
    lengths = []
    for part in parts:
        chars = []
        alpha_len = 0
        for ch in part:
            if ch.isalnum():
                chars.append("_")
                alpha_len += 1
            else:
                chars.append(ch)
        masked_words.append(" ".join(chars))
        lengths.append(str(alpha_len))
    mask_str = "   ".join(masked_words)
    len_str = ", ".join(lengths)
    return f"{mask_str} ({len_str})"


def check_guess(state: dict[str, Any], guess: str) -> tuple[bool, list[str]]:
    """
    Evaluate a player's guess against state['current_word'].
    Returns (is_correct: bool, partial_or_close_matches: list[str]).
    Supports:
    - Exact case-insensitive match
    - Punctuation-insensitive match ('E.T.' == 'et', 'WALL-E' == 'wall e' or 'walle')
    - Leading article tolerance ('The Lion King' == 'Lion King')
    - Partial word matches & high-similarity typo detection ('Lion Kings')
    """
    word = state.get("current_word") or ""
    if not word or not guess or not guess.strip():
        return False, []

    norm_word = _normalize_phrase(word, strip_article=False)
    norm_guess = _normalize_phrase(guess, strip_article=False)
    if not norm_guess:
        return False, []

    # 1. Exact normalized match or collapsed match (e.g. 'walle' vs 'wall e', 'et' vs 'e t')
    if norm_guess == norm_word or norm_guess.replace(" ", "") == norm_word.replace(" ", ""):
        return True, []

    # 2. Leading article-stripped match (e.g. 'Lion King' for 'The Lion King')
    stripped_word = _normalize_phrase(word, strip_article=True)
    stripped_guess = _normalize_phrase(guess, strip_article=True)
    if (
        stripped_word
        and stripped_guess
        and (stripped_guess == stripped_word or stripped_guess.replace(" ", "") == stripped_word.replace(" ", ""))
    ):
        return True, []

    # 2b. Wiktionary synonym / alias & localized translation matches
    lex = get_word_lexicon(word)
    candidate_terms: list[str] = list(state.get("current_aliases") or []) + list(lex.get("aliases") or [])
    for tr_map in (state.get("current_translations"), lex.get("translations")):
        if isinstance(tr_map, dict):
            for lang_terms in tr_map.values():
                if isinstance(lang_terms, list):
                    candidate_terms.extend(lang_terms)

    collapsed_guess = norm_guess.replace(" ", "")
    for alt in candidate_terms:
        norm_alt = _normalize_phrase(alt, strip_article=True)
        if not norm_alt or len(norm_alt) < 2:
            continue
        if (
            stripped_guess == norm_alt
            or norm_guess == norm_alt
            or (collapsed_guess and collapsed_guess == norm_alt.replace(" ", ""))
        ):
            return True, []

    # 3. Partial significant word matches
    stop_words = {"the", "and", "for", "with", "from", "into", "out", "under", "over"}
    word_parts = [w for w in norm_word.split() if len(w) > 2 and w not in stop_words]
    guess_parts = norm_guess.split()
    matches = []
    for w in word_parts:
        if w in guess_parts and w not in matches:
            matches.append(w)
        else:
            # Check singular/plural or 1-char typo on individual word
            for g in guess_parts:
                if len(g) >= 4 and difflib.SequenceMatcher(None, w, g).ratio() >= 0.84:
                    if w not in matches:
                        matches.append(f"{g}~")
                    break

    # 4. Whole-phrase close typo check
    if not matches and len(stripped_guess) >= 4:
        ratio = difflib.SequenceMatcher(None, stripped_word, stripped_guess).ratio()
        if ratio >= 0.80:
            matches.append("very close spelling!")

    return False, matches


def censor_spoilers(text: str, secret_word: Optional[str]) -> str:
    """Mask the secret word or its key tokens if a non-guessing player types it in chat."""
    if not text or not secret_word:
        return text
    correct, _ = check_guess({"current_word": secret_word}, text)
    if correct:
        return "🔒 [spoiler blocked]"
    out = text
    norm_tokens = [w for w in _normalize_phrase(secret_word, strip_article=True).split() if len(w) >= 4]
    for token in norm_tokens:
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        out = pattern.sub("•••", out)
    return out


# ============================================================================
# Round Progression, Word Dealing & Replay Recording
# ============================================================================


def pick_unused_word(state: dict[str, Any], words: Optional[list[tuple[str, str]]] = None) -> tuple[str, str]:
    """Select a random (word, category) avoiding already used words in this session."""
    if not words:
        return ("Mystery", "thing")
    used = set(state.get("used_words", []))
    available = [pair for pair in words if pair[0] not in used]
    if not available:
        # Reset used pool if exhausted
        state["used_words"] = []
        available = list(words)
    word, cat = random.choice(available)
    state.setdefault("used_words", []).append(word)
    return word, cat


def next_round(state: dict[str, Any], words: Optional[list[tuple[str, str]]] = None) -> dict[str, Any]:
    """Advance turn and initialize a new round."""
    if state.get("round_num", 0) > 0:
        state["current_turn"] = state.get("current_turn", 0) + 1
    else:
        state["current_turn"] = 0
    state["round_num"] = state.get("round_num", 0) + 1
    state["emoji_clue"] = ""
    state["emoji_hints"] = []
    state["guessed"] = []
    state["current_attempts"] = []
    state["rerolls_used"] = 0
    word, cat = pick_unused_word(state, words)
    state["current_word"] = word
    state["current_category"] = cat
    return state


def set_phase_timer(state: dict[str, Any], seconds: int) -> None:
    """Configure server-authoritative phase timer timestamps."""
    now = time.time()
    state["turn_start_time"] = now
    secs = max(0, int(seconds or 0))
    state["timer_duration"] = secs
    state["timer_ends_at"] = (now + secs) if secs > 0 else None
    state["timer_paused_remaining"] = None


def record_round_to_history(
    state: dict[str, Any],
    outcome: str = "guessed",
    guesser_str: Optional[str] = None,
    override_emoji: Optional[str] = None,
    override_word: Optional[str] = None,
    override_giver_id: Optional[str] = None,
) -> dict[str, Any]:
    """Record a completed round into both `history` and `rounds_history` for replay."""
    giver_id = override_giver_id or current_player_id(state)
    giver_name = state.get("players", {}).get(giver_id, {}).get("name", "?") if giver_id else "?"
    word = override_word if override_word is not None else (state.get("current_word") or "")
    emoji_clue = override_emoji if override_emoji is not None else (state.get("emoji_clue") or "")
    category = state.get("current_category") or "thing"

    if guesser_str is None:
        guessed_names = [
            state["players"][pid]["name"] for pid in state.get("guessed", []) if pid in state.get("players", {})
        ]
        guesser_str = ", ".join(guessed_names) if guessed_names else None

    scores_snapshot = {pid: p.get("score", 0) for pid, p in state.get("players", {}).items()}
    lex = get_word_lexicon(word)

    round_entry = {
        "round": state.get("round_num", 1),
        "mode": state.get("mode", "round_robin"),
        "giver_id": giver_id,
        "giver_name": giver_name,
        "word": word,
        "category": category,
        "definition": lex.get("definition", ""),
        "etymology": lex.get("etymology", ""),
        "emoji": emoji_clue,
        "emoji_clue": emoji_clue,
        "emoji_hints": copy.deepcopy(state.get("emoji_hints", [])),
        "attempts": copy.deepcopy(state.get("current_attempts", [])),
        "guesser": guesser_str,
        "outcome": outcome,
        "scores_after": scores_snapshot,
        "timestamp": round(time.time(), 2),
    }

    state.setdefault("history", []).append(
        {
            "round": round_entry["round"],
            "mode": round_entry["mode"],
            "giver_name": giver_name,
            "emoji": emoji_clue,
            "word": word,
            "category": category,
            "guesser": guesser_str,
            "outcome": outcome,
            "emoji_hints": round_entry["emoji_hints"],
            "attempts": round_entry["attempts"],
        }
    )
    state.setdefault("rounds_history", []).append(round_entry)
    return round_entry


# ============================================================================
# Sanitized Client Perspective & Replay Export
# ============================================================================


def get_sanitized_player_view(state: dict[str, Any], viewer_id: Optional[str] = None) -> dict[str, Any]:
    """
    Build a sanitized, role-appropriate state snapshot for a specific player.
    Ensures guessers cannot inspect network traffic to see the secret word during active play.
    """
    phase = state.get("phase", "lobby")
    mode = state.get("mode", "round_robin")
    active_pid = current_player_id(state)
    viewer = state.get("players", {}).get(viewer_id) if viewer_id else None
    is_admin = bool(
        viewer
        and (
            viewer.get("is_admin") or viewer.get("name") == state.get("creator") or viewer_id == state.get("creator_id")
        )
    )
    is_my_turn = bool(viewer_id and viewer_id == active_pid)
    has_guessed = bool(viewer_id and viewer_id in state.get("guessed", []))

    # Determine whether this viewer is allowed to see the current word
    can_see_word = False
    my_word = None
    my_category = state.get("current_category")

    if phase in ("gameover", "round_end"):
        can_see_word = True
        my_word = state.get("current_word")
    elif mode == "collective" and phase == "prep":
        q_item = state.get("collective_queue", {}).get(viewer_id, {})
        if q_item:
            can_see_word = True
            my_word = q_item.get("word")
            my_category = q_item.get("category")
    elif mode == "best_guess":
        if phase == "picking" and is_my_turn:
            can_see_word = True
            my_word = state.get("current_word")
        elif phase in ("submitting", "judging"):
            can_see_word = True
            my_word = state.get("current_word")
    else:
        # round_robin or collective guess phase
        if is_my_turn or has_guessed:
            can_see_word = True
            my_word = state.get("current_word")

    # Sanitize chat log for private chat mode
    sanitized_chat = []
    for entry in state.get("chat_log", [])[-120:]:
        private_to = entry.get("private_to")
        if private_to and viewer_id not in private_to and phase not in ("gameover", "round_end"):
            item = dict(entry)
            item["text"] = entry.get("masked_text") or "guessed ❌"
            sanitized_chat.append(item)
        else:
            sanitized_chat.append(entry)

    # Submissions for best_guess judging
    subs_list = []
    if mode == "best_guess" and phase in ("judging", "round_end", "gameover"):
        for pid, em in state.get("submissions", {}).items():
            p_name = state.get("players", {}).get(pid, {}).get("name", "?")
            subs_list.append(
                {
                    "channel": pid,
                    "player_id": pid,
                    "name": p_name if phase != "judging" else "Mystery Artist",
                    "revealed_name": p_name,
                    "emoji": em,
                }
            )

    # Collective prep status
    my_prep = None
    if mode == "collective" and phase == "prep" and viewer_id:
        my_prep = state.get("collective_queue", {}).get(viewer_id)

    now = time.time()
    remaining_timer = 0
    if state.get("timer_paused_remaining") is not None:
        remaining_timer = max(0, int(state["timer_paused_remaining"]))
    elif state.get("timer_ends_at"):
        remaining_timer = max(0, int(round(state["timer_ends_at"] - now)))

    s = state.get("settings", DEFAULT_SETTINGS)
    max_rerolls = int(s.get("allow_rerolls", 2))
    rerolls_used = my_prep.get("rerolls_used", 0) if my_prep else state.get("rerolls_used", 0)

    visible_lex = get_word_lexicon(my_word) if (can_see_word and my_word) else {}
    current_lex = get_word_lexicon(state.get("current_word")) if state.get("current_word") else {}

    return {
        "type": "state",
        "code": state.get("code"),
        "title": state.get("title"),
        "status": state.get("status", "open"),
        "mode": mode,
        "phase": phase,
        "started": bool(state.get("started")),
        "round_num": state.get("round_num", 0),
        "max_rounds": s.get("max_rounds", 10),
        "creator": state.get("creator"),
        "creator_id": state.get("creator_id"),
        "me": {
            "id": viewer_id,
            "name": viewer.get("name") if viewer else None,
            "score": viewer.get("score", 0) if viewer else 0,
            "is_admin": is_admin,
            "is_turn": is_my_turn,
            "is_spectator": bool(viewer.get("is_spectator", False)) if viewer else False,
            "has_guessed": has_guessed,
            "token": viewer.get("token") if viewer else None,
        },
        "current_player": (state.get("players", {}).get(active_pid, {}).get("name", "?") if active_pid else None),
        "current_player_id": active_pid,
        "current_word": my_word if can_see_word else None,
        "current_category": my_category,
        "current_definition": visible_lex.get("definition", "") if can_see_word else None,
        "current_etymology": visible_lex.get("etymology", "") if can_see_word else None,
        "current_aliases": list(visible_lex.get("aliases", []))[:5] if can_see_word else [],
        "current_translations": visible_lex.get("translations", {}) if can_see_word else {},
        "topic_hint": (current_lex.get("topics") or [None])[0],
        "word_length": len(state.get("current_word") or ""),
        "word_mask": build_word_mask(state.get("current_word")),
        "emoji_clue": (
            my_prep.get("emoji_clue", "")
            if (mode == "collective" and phase == "prep" and my_prep)
            else state.get("emoji_clue", "")
        ),
        "emoji_hints": state.get("emoji_hints", []),
        "rerolls_left": max(0, max_rerolls - rerolls_used),
        "prep_submitted": bool(my_prep.get("submitted")) if my_prep else False,
        "players": player_list(state),
        "submissions": subs_list,
        "history": state.get("history", []),
        "rounds_history": state.get("rounds_history", []),
        "chat_log": sanitized_chat,
        "settings": s,
        "presets": SETTINGS_PRESETS,
        "timer": {
            "duration": state.get("timer_duration", 0),
            "remaining": remaining_timer,
            "ends_at": state.get("timer_ends_at"),
            "paused": state.get("timer_paused_remaining") is not None,
        },
        "next_room_code": state.get("next_room_code"),
    }


def export_game_replay(state: dict[str, Any]) -> dict[str, Any]:
    """Export a complete, self-contained JSON replay of the Emojinary match."""
    players_summary = sorted(
        [
            {
                "id": pid,
                "name": p.get("name"),
                "score": p.get("score", 0),
                "is_admin": bool(p.get("is_admin")),
            }
            for pid, p in state.get("players", {}).items()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )
    phase = state.get("phase", "lobby")
    sanitized_chat = []
    for e in state.get("chat_log", []):
        item = {k: v for k, v in e.items() if k not in ("private_to", "masked_text")}
        if e.get("private_to") and phase not in ("gameover", "round_end"):
            item["text"] = e.get("masked_text") or "guessed ❌"
        sanitized_chat.append(item)

    return {
        "game": "emojinary",
        "code": state.get("code"),
        "title": state.get("title"),
        "mode": state.get("mode", "round_robin"),
        "status": state.get("status", "open"),
        "phase": phase,
        "round_num": state.get("round_num", 0),
        "settings": state.get("settings", {}),
        "players": players_summary,
        "leaderboard": players_summary,
        "rounds_history": state.get("rounds_history", []),
        "chat_log": sanitized_chat,
        "exported_at": round(time.time(), 2),
    }

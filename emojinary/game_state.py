"""Game state stored in Valkey/Redis for persistence and multi-process safety."""

import json
import random

import redis

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        import os

        url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        _redis = redis.from_url(url, decode_responses=True)
    return _redis


def _key(code):
    return f"emojinary:game:{code}"


def get_game(code):
    r = _get_redis()
    data = r.get(_key(code))
    if data:
        return json.loads(data)
    return {
        "players": {},  # channel_name -> {name, score}
        "turn_order": [],
        "current_turn": 0,
        "current_word": None,
        "current_category": None,
        "emoji_clue": "",
        "round_num": 0,
        "started": False,
        "guessed": [],
        "creator": None,
        "history": [],  # [{emoji, word, category, guesser}]
    }


def save_game(code, state):
    r = _get_redis()
    r.set(_key(code), json.dumps(state), ex=86400)  # expire after 24h


def delete_game(code):
    r = _get_redis()
    r.delete(_key(code))


def player_list(state):
    current_player = current_player_channel(state)
    return [
        {"name": info["name"], "score": info["score"], "is_turn": ch == current_player}
        for ch, info in state["players"].items()
    ]


def current_player_channel(state):
    if not state["turn_order"]:
        return None
    return state["turn_order"][state["current_turn"] % len(state["turn_order"])]


def next_round(state, words=None):
    state["current_turn"] += 1
    state["round_num"] += 1
    state["emoji_clue"] = ""
    state["guessed"] = []
    if words:
        word, cat = random.choice(words)
        state["current_word"] = word
        state["current_category"] = cat
    else:
        state["current_word"] = "mystery"
        state["current_category"] = "thing"
    return state


def check_guess(state, guess):
    """Returns (correct, partial_matches)."""
    word = state.get("current_word", "")
    if not word:
        return False, []
    guess_lower = guess.strip().lower()
    word_lower = word.lower()
    if guess_lower == word_lower:
        return True, []
    word_parts = word_lower.split()
    guess_parts = guess_lower.split()
    matches = [w for w in word_parts if w in guess_parts and len(w) > 2]
    return False, matches

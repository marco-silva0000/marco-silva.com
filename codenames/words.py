"""Official Gullesnuffs/Codenames wordlist, Wikisaurus semantic graph, Wiktionary localization, and Spymaster AI clues."""

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from emojinary.game_state import get_word_lexicon
from gamerooms.language_support import get_lexicon_language_key, normalize_language_code
from impostor.word_pairs import normalize_text, text_matches_term

_sys_rng = random.SystemRandom()

_WORDLISTS_PATH = Path(__file__).resolve().parent.parent / "emojinary" / "data" / "wordlists.json"
_LEXICON_PATH = Path(__file__).resolve().parent.parent / "emojinary" / "data" / "wiktionary_lexicon.json"

WORD_PACKS = ("classic", "extended")

_IGNORED_TOPIC_TAGS = frozenset(
    {
        "proscribed",
        "historical",
        "archaic",
        "obsolete",
        "slang",
        "colloquial",
        "informal",
        "formal",
        "figurative",
        "plural",
        "singular",
        "countable",
        "uncountable",
        "british",
        "american",
        "us",
        "uk",
        "australian",
        "canadian",
        "new zealand",
        "philippine",
        "dated",
        "rare",
        "vulgar",
        "offensive",
        "derogatory",
        "humorous",
        "all topics",
    }
)


@lru_cache(maxsize=1)
def _load_wordlists_data() -> dict[str, Any]:
    if not _WORDLISTS_PATH.exists():
        return {}
    try:
        with open(_WORDLISTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _load_lexicon_data() -> dict[str, Any]:
    if not _LEXICON_PATH.exists():
        return {}
    try:
        with open(_LEXICON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@lru_cache(maxsize=1)
def get_classic_codenames_words() -> tuple[str, ...]:
    """Return the official 400-word Codenames vocabulary (from Gullesnuffs/Codenames)."""
    data = _load_wordlists_data()
    words = [str(w).strip() for w in data.get("codenames", []) if str(w).strip()]
    if words:
        return tuple(words)
    return (
        "Africa",
        "Agent",
        "Air",
        "Alien",
        "Alps",
        "Amazon",
        "Ambulance",
        "America",
        "Angel",
        "Antarctica",
        "Apple",
        "Arm",
        "Atlantis",
        "Australia",
        "Aztec",
        "Back",
        "Ball",
        "Band",
        "Bank",
        "Bar",
        "Bark",
        "Bat",
        "Battery",
        "Beach",
        "Bear",
        "Beat",
        "Bed",
        "Beijing",
        "Bell",
        "Belt",
    )


@lru_cache(maxsize=1)
def get_extended_codenames_words() -> tuple[str, ...]:
    """Return the 400 official words plus concrete Wiktionary-enriched nouns from wordlists."""
    classic = list(get_classic_codenames_words())
    seen = {w.lower() for w in classic}
    lexicon = _load_lexicon_data()
    data = _load_wordlists_data()

    extra: list[str] = []
    for item in data.get("emojinary", []):
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        raw = str(item[0]).strip()
        cat = str(item[1]).strip().lower()
        low = raw.lower()
        if cat not in ("thing", "animal", "food", "place"):
            continue
        if low in seen or " " in raw or not raw.isalpha() or not (3 <= len(raw) <= 13):
            continue
        entry = lexicon.get(low, {})
        if entry.get("pos") == "noun" and entry.get("definition") and len(entry.get("translations", {})) >= 5:
            seen.add(low)
            extra.append(raw.title())

    return tuple(classic + sorted(extra))


def get_codenames_word_pool(word_pack: str = "classic") -> list[str]:
    """Return candidate word list for the selected Codenames pack."""
    if word_pack == "extended":
        return list(get_extended_codenames_words())
    return list(get_classic_codenames_words())


def get_wikisaurus_neighbors(word: str) -> list[str]:
    """Return Wikisaurus semantic neighbors for a canonical Codenames word."""
    key = (word or "").strip().lower()
    if not key:
        return []
    data = _load_wordlists_data()
    wikisaurus = data.get("codenames_wikisaurus", {})
    neighbors = list(wikisaurus.get(key, []))
    entry = get_word_lexicon(key)
    for rel in entry.get("related", []):
        if rel not in neighbors:
            neighbors.append(rel)
    return neighbors[:30]


def localize_codenames_word(word_en: str, lang_code: str = "en") -> dict[str, Any]:
    """Build localized card metadata with Wiktionary translations, definition, aliases, and Wikisaurus edges."""
    norm_lang = normalize_language_code(lang_code)
    lex_key = get_lexicon_language_key(norm_lang)
    entry = get_word_lexicon(word_en)
    translations = entry.get("translations") or {}

    localized = word_en
    match_terms: list[str] = [word_en]
    aliases = [str(a).strip() for a in (entry.get("aliases") or []) if str(a).strip()]

    if norm_lang != "en":
        lang_vals = translations.get(lex_key) or translations.get(norm_lang) or []
        if lang_vals:
            localized = str(lang_vals[0])
            match_terms.extend(str(v) for v in lang_vals if v)

    seen: set[str] = set()
    normalized_matches: list[str] = []
    for term in match_terms:
        nt = normalize_text(term)
        if nt and nt not in seen:
            seen.add(nt)
            normalized_matches.append(nt)

    related = get_wikisaurus_neighbors(word_en)
    topics = [str(t).strip() for t in (entry.get("topics") or []) if str(t).strip()]

    return {
        "word_en": word_en,
        "word_display": localized,
        "matches": normalized_matches,
        "definition": entry.get("definition", ""),
        "pos": entry.get("pos", "noun"),
        "aliases": aliases[:8],
        "topics": topics[:5],
        "related": related[:30],
    }


def deal_codenames_board(
    lang_code: str = "en",
    word_pack: str = "classic",
    used_words: Optional[list[str]] = None,
    custom_deck: Optional[list[dict[str, Any]]] = None,
    rng: Optional[random.Random] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Deal a 25-card Codenames grid following standard 9 / 8 / 7 / 1 team distribution."""
    chooser = rng or _sys_rng
    chosen_cards: list[dict[str, Any]] = []
    seen_en: set[str] = set()
    seen_display: set[str] = set()

    def _try_add(word_en: str, author_name: Optional[str] = None) -> bool:
        low_en = word_en.strip().lower()
        if not low_en or low_en in seen_en:
            return False
        loc = localize_codenames_word(word_en.strip(), lang_code=lang_code)
        disp_norm = normalize_text(loc["word_display"])
        if not disp_norm or disp_norm in seen_display:
            return False
        seen_en.add(low_en)
        seen_display.add(disp_norm)
        loc["author_name"] = author_name
        chosen_cards.append(loc)
        return True

    # 1. Prioritize custom words submitted in this room
    if custom_deck:
        while custom_deck and len(chosen_cards) < 25:
            item = custom_deck.pop(0)
            _try_add(str(item.get("word", "")), author_name=item.get("author_name"))

    # 2. Fill remaining slots from unused words in the selected pack before recycling
    pool = get_codenames_word_pool(word_pack)
    used_set = {w.strip().lower() for w in (used_words or [])}
    unused_pool = [w for w in pool if w.lower() not in used_set]
    chooser.shuffle(unused_pool)
    for w in unused_pool:
        if len(chosen_cards) >= 25:
            break
        _try_add(w)

    if len(chosen_cards) < 25:
        recycled = list(pool)
        chooser.shuffle(recycled)
        for w in recycled:
            if len(chosen_cards) >= 25:
                break
            _try_add(w)

    # Fallback: guarantee 25 cards even in minimal custom-only environments
    while len(chosen_cards) < 25:
        idx = len(chosen_cards) + 1
        _try_add(f"Agent {idx}")

    starting_team = chooser.choice(["red", "blue"])
    other_team = "blue" if starting_team == "red" else "red"
    affiliations = [starting_team] * 9 + [other_team] * 8 + ["civilian"] * 7 + ["assassin"]
    chooser.shuffle(affiliations)

    board: list[dict[str, Any]] = []
    for idx, (card, aff) in enumerate(zip(chosen_cards, affiliations)):
        board.append(
            {
                "index": idx,
                "word_en": card["word_en"],
                "word_display": card["word_display"],
                "matches": card["matches"],
                "definition": card["definition"],
                "pos": card["pos"],
                "aliases": card["aliases"],
                "topics": card["topics"],
                "related": card["related"],
                "author_name": card.get("author_name"),
                "affiliation": aff,
                "revealed": False,
                "revealed_by": None,
                "revealed_by_team": None,
            }
        )
    return starting_team, board


def is_clue_forbidden_on_board(clue_word: str, cards: list[dict[str, Any]]) -> Optional[str]:
    """Return the offending unrevealed board word if the clue unlawfully names/contains a visible word."""
    nc = normalize_text(clue_word)
    if not nc:
        return "empty"
    for c in cards:
        if c.get("revealed"):
            continue
        matches = list(c.get("matches") or []) + [
            normalize_text(c.get("word_en")),
            normalize_text(c.get("word_display")),
        ]
        if text_matches_term(nc, matches, allow_substring_word=True):
            return c.get("word_display") or c.get("word_en")
        for m in matches:
            if m and len(nc) >= 4 and len(m) >= 4 and (nc in m or m in nc):
                return c.get("word_display") or c.get("word_en")
    return None


def suggest_spymaster_clues(
    cards: list[dict[str, Any]],
    team: str,
    max_suggestions: int = 6,
) -> list[dict[str, Any]]:
    """Suggest candidate Spymaster clues using Gullesnuffs Wikisaurus edges and Wiktionary aliases/topics."""
    other_team = "blue" if team == "red" else "red"
    unrevealed = [c for c in cards if not c.get("revealed")]
    if not unrevealed:
        return []

    candidate_links: dict[str, dict[str, Any]] = {}

    def _card_concepts(card: dict[str, Any]) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        for r in card.get("related") or []:
            nr = normalize_text(r)
            if nr and " " not in nr and len(nr) >= 3:
                out.append((nr, 1.4))
        for a in card.get("aliases") or []:
            na = normalize_text(a)
            if na and " " not in na and 3 <= len(na) <= 22:
                out.append((na, 1.25))
        for t in card.get("topics") or []:
            nt = normalize_text(t)
            if nt and " " not in nt and nt not in _IGNORED_TOPIC_TAGS and 3 <= len(nt) <= 20:
                out.append((nt, 0.9))
        return out

    for card in unrevealed:
        aff = card.get("affiliation")
        disp = card.get("word_display") or card.get("word_en") or ""
        seen_for_card: set[str] = set()
        for concept, weight in _card_concepts(card):
            if concept in seen_for_card:
                continue
            seen_for_card.add(concept)
            bucket = candidate_links.setdefault(
                concept,
                {"team_targets": [], "opp_hits": 0, "civ_hits": 0, "assassin_hit": False, "weight": 0.0},
            )
            if aff == team:
                bucket["team_targets"].append(disp)
                bucket["weight"] += weight
            elif aff == other_team:
                bucket["opp_hits"] += 1
            elif aff == "assassin":
                bucket["assassin_hit"] = True
            else:
                bucket["civ_hits"] += 1

    min_targets = 2 if sum(1 for c in unrevealed if c.get("affiliation") == team) >= 2 else 1
    ranked: list[tuple[int, float, str, list[str]]] = []
    for concept, info in candidate_links.items():
        if info["assassin_hit"]:
            continue
        targets = info["team_targets"]
        if len(targets) < min_targets:
            continue
        if is_clue_forbidden_on_board(concept, unrevealed) is not None:
            continue
        score = info["weight"] + len(targets) * 1.5 - info["opp_hits"] * 2.2 - info["civ_hits"] * 0.9
        if score <= 0:
            continue
        ranked.append((len(targets), score, concept, targets))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [
        {
            "clue": concept.title(),
            "count": count,
            "targets": targets,
            "score": round(score, 2),
        }
        for count, score, concept, targets in ranked[:max_suggestions]
    ]

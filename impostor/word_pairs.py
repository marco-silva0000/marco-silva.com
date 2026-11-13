"""Curated & Wiktionary-localized Word Impostor + Poison Word pair generator."""

import json
import random
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from emojinary.game_state import get_word_lexicon
from gamerooms.language_support import get_lexicon_language_key, normalize_language_code

# Format: (citizen_word, poison_word, lethal_taboo_word, category)
CURATED_IMPOSTOR_PAIRS: list[tuple[str, str, str, str]] = [
    # Food & Drink
    ("Coffee", "Tea", "Caffeine", "food"),
    ("Pizza", "Lasagna", "Pepperoni", "food"),
    ("Hamburger", "Hot Dog", "Ketchup", "food"),
    ("Sushi", "Ramen", "Chopsticks", "food"),
    ("Chocolate", "Caramel", "Cocoa", "food"),
    ("Apple", "Pear", "Orchard", "food"),
    ("Banana", "Pineapple", "Peel", "food"),
    ("Ice Cream", "Frozen Yogurt", "Cone", "food"),
    ("Croissant", "Bagel", "Bakery", "food"),
    ("Lemon", "Lime", "Sour", "food"),
    ("Strawberry", "Raspberry", "Jam", "food"),
    ("Pasta", "Rice", "Noodle", "food"),
    ("Wine", "Beer", "Vineyard", "food"),
    ("Milk", "Juice", "Dairy", "food"),
    ("Bread", "Toast", "Butter", "food"),
    ("Pancake", "Waffle", "Syrup", "food"),
    # Animals
    ("Lion", "Tiger", "Mane", "animal"),
    ("Cat", "Dog", "Whiskers", "animal"),
    ("Dolphin", "Whale", "Ocean", "animal"),
    ("Eagle", "Hawk", "Feathers", "animal"),
    ("Frog", "Toad", "Pond", "animal"),
    ("Bee", "Wasp", "Honey", "animal"),
    ("Butterfly", "Moth", "Cocoon", "animal"),
    ("Horse", "Zebra", "Gallop", "animal"),
    ("Wolf", "Fox", "Howl", "animal"),
    ("Shark", "Octopus", "Fin", "animal"),
    ("Penguin", "Owl", "Antarctica", "animal"),
    ("Bear", "Panda", "Hibernation", "animal"),
    ("Elephant", "Hippopotamus", "Trunk", "animal"),
    ("Turtle", "Crocodile", "Shell", "animal"),
    # Things & Objects
    ("Violin", "Cello", "Bow", "thing"),
    ("Guitar", "Ukulele", "Strings", "thing"),
    ("Piano", "Accordion", "Keys", "thing"),
    ("Sword", "Dagger", "Blade", "thing"),
    ("Watch", "Clock", "Tick", "thing"),
    ("Chair", "Sofa", "Cushion", "thing"),
    ("Telescope", "Microscope", "Lens", "thing"),
    ("Spoon", "Fork", "Soup", "thing"),
    ("Airplane", "Helicopter", "Runway", "thing"),
    ("Submarine", "Cruise Ship", "Periscope", "thing"),
    ("Bicycle", "Motorcycle", "Pedal", "thing"),
    ("Umbrella", "Raincoat", "Rain", "thing"),
    ("Camera", "Projector", "Shutter", "thing"),
    ("Candle", "Flashlight", "Flame", "thing"),
    ("Compass", "Map", "North", "thing"),
    ("Pillow", "Blanket", "Sleep", "thing"),
    ("Backpack", "Suitcase", "Zipper", "thing"),
    ("Mirror", "Window", "Reflection", "thing"),
    # Places
    ("Beach", "Swimming Pool", "Sand", "place"),
    ("Library", "Bookstore", "Shelf", "place"),
    ("Hospital", "Pharmacy", "Doctor", "place"),
    ("Cinema", "Theater", "Screen", "place"),
    ("Museum", "Art Gallery", "Statue", "place"),
    ("Airport", "Train Station", "Boarding", "place"),
    ("Desert", "Tundra", "Dune", "place"),
    ("Castle", "Palace", "Moat", "place"),
    ("Restaurant", "Cafe", "Waiter", "place"),
    ("Volcano", "Glacier", "Lava", "place"),
    ("Island", "Peninsula", "Coast", "place"),
    ("Stadium", "Gym", "Crowd", "place"),
    # People & Professions / Heroes
    ("Astronaut", "Pilot", "Orbit", "person"),
    ("Chef", "Baker", "Apron", "person"),
    ("Detective", "Spy", "Clue", "person"),
    ("Magician", "Clown", "Wand", "person"),
    ("Firefighter", "Paramedic", "Siren", "person"),
    ("Superman", "Batman", "Kryptonite", "person"),
    ("Pirate", "Viking", "Treasure", "person"),
    ("Wizard", "Witch", "Spell", "person"),
    ("Ninja", "Samurai", "Stealth", "person"),
    ("Teacher", "Professor", "Chalkboard", "person"),
    # Movies & Pop Culture
    ("Harry Potter", "Lord of the Rings", "Hogwarts", "movie"),
    ("Star Wars", "Star Trek", "Lightsaber", "movie"),
    ("Titanic", "Avatar", "Iceberg", "movie"),
    ("Spider-Man", "Iron Man", "Web", "movie"),
    ("Jurassic Park", "King Kong", "Dinosaur", "movie"),
    ("The Matrix", "Inception", "Dream", "movie"),
    ("Toy Story", "Finding Nemo", "Pixar", "movie"),
    ("James Bond", "Sherlock Holmes", "007", "movie"),
    # Sports & Activities
    ("Soccer", "Basketball", "Goal", "sport"),
    ("Tennis", "Badminton", "Racket", "sport"),
    ("Skiing", "Snowboarding", "Slope", "sport"),
    ("Chess", "Checkers", "King", "sport"),
    ("Boxing", "Wrestling", "Ring", "sport"),
    ("Golf", "Bowling", "Hole", "sport"),
    ("Surfing", "Sailing", "Wave", "sport"),
    ("Marathon", "Sprint", "Medal", "sport"),
]

CATEGORIES = ("all", "food", "animal", "thing", "place", "person", "movie", "sport")

_LEXICON_PATH = Path(__file__).resolve().parent.parent / "emojinary" / "data" / "wiktionary_lexicon.json"


@lru_cache(maxsize=1)
def _load_full_lexicon() -> dict[str, Any]:
    if not _LEXICON_PATH.exists():
        return {}
    try:
        with open(_LEXICON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def normalize_text(text: str | None) -> str:
    """Lowercase, strip accents/diacritics, and collapse whitespace/punctuation."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", str(text).strip().lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^\w\s]", " ", stripped, flags=re.UNICODE)
    return " ".join(cleaned.split())


def localize_term(term_en: str, lang_code: str = "en") -> dict[str, Any]:
    """Translate a canonical English word into `lang_code` via Wiktionary lexicon when available."""
    norm_lang = normalize_language_code(lang_code)
    lex_key = get_lexicon_language_key(norm_lang)
    entry = get_word_lexicon(term_en)
    translations = entry.get("translations") or {}

    localized = term_en
    match_terms: list[str] = [term_en]
    if entry.get("aliases"):
        match_terms.extend(str(a) for a in entry["aliases"] if a)

    if norm_lang != "en":
        lang_vals = translations.get(lex_key) or translations.get(norm_lang) or []
        if lang_vals:
            localized = str(lang_vals[0])
            match_terms.extend(str(v) for v in lang_vals if v)

    # Deduplicate normalized variants while keeping order
    seen: set[str] = set()
    normalized_matches: list[str] = []
    for t in match_terms:
        nt = normalize_text(t)
        if nt and nt not in seen:
            seen.add(nt)
            normalized_matches.append(nt)

    return {
        "en": term_en,
        "display": localized,
        "matches": normalized_matches,
        "definition": entry.get("definition", "") if norm_lang == "en" else "",
    }


def text_matches_term(candidate: str | None, matches: list[str], allow_substring_word: bool = True) -> bool:
    """Return True if candidate clue/guess matches any normalized variant (exact or whole-word inside clue)."""
    nc = normalize_text(candidate)
    if not nc:
        return False
    nc_words = set(nc.split())
    for m in matches:
        if not m:
            continue
        if nc == m:
            return True
        if allow_substring_word:
            m_words = m.split()
            if len(m_words) == 1 and m in nc_words:
                return True
            if len(m_words) > 1 and m in nc:
                return True
    return False


def localize_impostor_pair(
    citizen_en: str,
    poison_en: str,
    lethal_en: str,
    category: str = "thing",
    lang_code: str = "en",
    author_id: Optional[str] = None,
    author_name: Optional[str] = None,
) -> dict[str, Any]:
    """Build a complete localized pair payload from canonical words."""
    c_info = localize_term(citizen_en, lang_code)
    p_info = localize_term(poison_en, lang_code)
    l_info = localize_term(lethal_en, lang_code) if lethal_en else {"en": "", "display": "", "matches": []}

    return {
        "pair_key": f"{normalize_text(citizen_en)}::{normalize_text(poison_en)}",
        "category": category or "thing",
        "citizen_word": c_info["en"],
        "citizen_display": c_info["display"],
        "citizen_matches": c_info["matches"],
        "poison_word": p_info["en"],
        "poison_display": p_info["display"],
        "poison_matches": p_info["matches"],
        "lethal_word": l_info["en"],
        "lethal_display": l_info["display"],
        "lethal_matches": l_info["matches"],
        "author_id": author_id,
        "author_name": author_name,
    }


def pick_impostor_pair(
    category: str = "all",
    lang_code: str = "en",
    used_pairs: Optional[list[str]] = None,
    custom_deck: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Select the next word pair, prioritizing custom player deck before curated bank."""
    if custom_deck:
        card = custom_deck.pop(0)
        return localize_impostor_pair(
            citizen_en=str(card.get("citizen_word", "")).strip(),
            poison_en=str(card.get("poison_word", "")).strip(),
            lethal_en=str(card.get("lethal_word", "")).strip(),
            category=str(card.get("category", "custom")).strip() or "custom",
            lang_code=lang_code,
            author_id=card.get("author_id"),
            author_name=card.get("author_name"),
        )

    cat = (category or "all").strip().lower()
    used_set = set(used_pairs or [])
    pool = [p for p in CURATED_IMPOSTOR_PAIRS if cat == "all" or p[3] == cat]
    if not pool:
        pool = list(CURATED_IMPOSTOR_PAIRS)

    unused = [p for p in pool if f"{normalize_text(p[0])}::{normalize_text(p[1])}" not in used_set]
    if unused:
        chosen = random.choice(unused)
    else:
        chosen = random.choice(pool)

    return localize_impostor_pair(chosen[0], chosen[1], chosen[2], chosen[3], lang_code=lang_code)

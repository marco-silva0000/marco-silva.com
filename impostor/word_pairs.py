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
# Pairs are intentionally laterally distanced (sharing 1-2 abstract traits rather than being near-synonyms)
# so knowing one word does not immediately give away the other word without listening to the table's clues.
CURATED_IMPOSTOR_PAIRS: list[tuple[str, str, str, str]] = [
    # Cross-Domain / No-Theme Lateral Pairs (different domains sharing an indirect trait)
    ("Cactus", "Hedgehog", "Needle", "no_theme"),
    ("Submarine", "Whale", "Ocean", "no_theme"),
    ("Volcano", "Dragon", "Lava", "no_theme"),
    ("Vampire", "Mosquito", "Bite", "no_theme"),
    ("Zebra", "Piano", "Keys", "no_theme"),
    ("Kangaroo", "Backpack", "Pocket", "no_theme"),
    ("Cloud", "Pillow", "Sleep", "no_theme"),
    ("Candle", "Sun", "Flame", "no_theme"),
    ("Compass", "Lighthouse", "North", "no_theme"),
    ("Snail", "Tent", "Shell", "no_theme"),
    ("Igloo", "Refrigerator", "Ice", "no_theme"),
    ("Tree", "Umbrella", "Rain", "no_theme"),
    ("Mirror", "Lake", "Reflection", "no_theme"),
    ("Spider", "Net", "Web", "no_theme"),
    ("Owl", "Moon", "Night", "no_theme"),
    ("Crown", "Helmet", "King", "no_theme"),
    ("Popcorn", "Snow", "Butter", "no_theme"),
    ("Balloon", "Bubble", "Air", "no_theme"),
    # Food & Drink (distanced — never twin foods like Ice Cream / Frozen Yogurt or Bread / Toast)
    ("Ice Cream", "Watermelon", "Cone", "food"),
    ("Coffee", "Chocolate", "Caffeine", "food"),
    ("Pizza", "Taco", "Pepperoni", "food"),
    ("Hamburger", "Burrito", "Ketchup", "food"),
    ("Sushi", "Cheese", "Chopsticks", "food"),
    ("Apple", "Carrot", "Orchard", "food"),
    ("Banana", "Coconut", "Peel", "food"),
    ("Croissant", "Pancake", "Bakery", "food"),
    ("Lemon", "Garlic", "Sour", "food"),
    ("Strawberry", "Tomato", "Jam", "food"),
    ("Pasta", "Soup", "Noodle", "food"),
    ("Wine", "Honey", "Vineyard", "food"),
    ("Milk", "Juice", "Dairy", "food"),
    ("Bread", "Potato", "Butter", "food"),
    ("Waffle", "Pretzel", "Syrup", "food"),
    ("Popcorn", "Pineapple", "Salt", "food"),
    # Animals (distanced — never twin species like Frog / Toad, Eagle / Hawk, Bee / Wasp)
    ("Lion", "Eagle", "Mane", "animal"),
    ("Cat", "Owl", "Whiskers", "animal"),
    ("Dolphin", "Penguin", "Ocean", "animal"),
    ("Frog", "Turtle", "Pond", "animal"),
    ("Bee", "Butterfly", "Honey", "animal"),
    ("Horse", "Camel", "Gallop", "animal"),
    ("Wolf", "Bear", "Howl", "animal"),
    ("Shark", "Crocodile", "Fin", "animal"),
    ("Elephant", "Whale", "Trunk", "animal"),
    ("Octopus", "Spider", "Ocean", "animal"),
    ("Fox", "Monkey", "Tail", "animal"),
    ("Panda", "Koala", "Hibernation", "animal"),
    ("Zebra", "Giraffe", "Gallop", "animal"),
    ("Bat", "Moth", "Cave", "animal"),
    # Things & Objects (distanced — never Violin / Cello, Guitar / Ukulele, Sword / Dagger, Watch / Clock)
    ("Violin", "Piano", "Bow", "thing"),
    ("Guitar", "Drum", "Strings", "thing"),
    ("Trumpet", "Bell", "Keys", "thing"),
    ("Sword", "Arrow", "Blade", "thing"),
    ("Watch", "Compass", "Tick", "thing"),
    ("Chair", "Sled", "Cushion", "thing"),
    ("Telescope", "Camera", "Lens", "thing"),
    ("Spoon", "Straw", "Soup", "thing"),
    ("Airplane", "Rocket", "Runway", "thing"),
    ("Submarine", "Train", "Periscope", "thing"),
    ("Bicycle", "Skateboard", "Pedal", "thing"),
    ("Umbrella", "Sunglasses", "Rain", "thing"),
    ("Candle", "Lantern", "Flame", "thing"),
    ("Pillow", "Mattress", "Sleep", "thing"),
    ("Backpack", "Wallet", "Zipper", "thing"),
    ("Mirror", "Projector", "Reflection", "thing"),
    ("Key", "Map", "Lock", "thing"),
    ("Microscope", "Magnifying Glass", "Lens", "thing"),
    # Places (distanced — never Library / Bookstore, Cinema / Theater, Museum / Art Gallery)
    ("Beach", "Desert", "Sand", "place"),
    ("Library", "Museum", "Shelf", "place"),
    ("Hospital", "Hotel", "Doctor", "place"),
    ("Cinema", "Stadium", "Screen", "place"),
    ("Airport", "Train Station", "Boarding", "place"),
    ("Castle", "Prison", "Moat", "place"),
    ("Restaurant", "Bakery", "Waiter", "place"),
    ("Volcano", "Cave", "Lava", "place"),
    ("Island", "Glacier", "Coast", "place"),
    ("Gym", "Park", "Crowd", "place"),
    ("Pharmacy", "Laboratory", "Doctor", "place"),
    ("Theater", "Art Gallery", "Statue", "place"),
    # People & Professions / Heroes (distanced — never Wizard / Witch, Teacher / Professor, Chef / Baker)
    ("Astronaut", "Diver", "Orbit", "person"),
    ("Chef", "Pirate", "Apron", "person"),
    ("Detective", "Magician", "Clue", "person"),
    ("Clown", "Juggler", "Wand", "person"),
    ("Firefighter", "Pilot", "Siren", "person"),
    ("Superman", "Spider-Man", "Kryptonite", "person"),
    ("Viking", "Cowboy", "Treasure", "person"),
    ("Wizard", "Spy", "Spell", "person"),
    ("Ninja", "Ghost", "Stealth", "person"),
    ("Teacher", "Coach", "Chalkboard", "person"),
    # Movies & Pop Culture
    ("Harry Potter", "Star Wars", "Hogwarts", "movie"),
    ("Lord of the Rings", "King Kong", "Dinosaur", "movie"),
    ("Titanic", "Jurassic Park", "Iceberg", "movie"),
    ("Avatar", "The Matrix", "Dream", "movie"),
    ("Batman", "James Bond", "007", "movie"),
    ("Toy Story", "Finding Nemo", "Pixar", "movie"),
    ("Iron Man", "Sherlock Holmes", "Web", "movie"),
    ("Star Trek", "Inception", "Lightsaber", "movie"),
    # Sports & Activities (distanced — never Skiing / Snowboarding, Chess / Checkers)
    ("Soccer", "Basketball", "Goal", "sport"),
    ("Tennis", "Golf", "Racket", "sport"),
    ("Skiing", "Surfing", "Slope", "sport"),
    ("Chess", "Bowling", "King", "sport"),
    ("Boxing", "Fencing", "Ring", "sport"),
    ("Badminton", "Ping Pong", "Hole", "sport"),
    ("Sailing", "Marathon", "Wave", "sport"),
    ("Wrestling", "Sprint", "Medal", "sport"),
]

CATEGORIES = ("no_theme", "all", "food", "animal", "thing", "place", "person", "movie", "sport")

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

    cat = (category or "no_theme").strip().lower()
    used_set = set(used_pairs or [])
    if cat in ("no_theme", "all"):
        pool = list(CURATED_IMPOSTOR_PAIRS)
    else:
        pool = [p for p in CURATED_IMPOSTOR_PAIRS if p[3] == cat]
    if not pool:
        pool = list(CURATED_IMPOSTOR_PAIRS)

    unused = [p for p in pool if f"{normalize_text(p[0])}::{normalize_text(p[1])}" not in used_set]
    if unused:
        chosen = random.choice(unused)
    else:
        chosen = random.choice(pool)

    return localize_impostor_pair(chosen[0], chosen[1], chosen[2], chosen[3], lang_code=lang_code)

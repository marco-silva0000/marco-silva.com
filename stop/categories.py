"""Word-database categories, Wiktionary topic clusters, fun web party prompts, and letter picker for Stop!"""

import json
import random
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from gamerooms.language_support import get_lexicon_language_key, normalize_language_code
from impostor.word_pairs import normalize_text

_sys_rng = random.SystemRandom()

_WORDLISTS_PATH = Path(__file__).resolve().parent.parent / "emojinary" / "data" / "wordlists.json"
_LEXICON_PATH = Path(__file__).resolve().parent.parent / "emojinary" / "data" / "wiktionary_lexicon.json"

CATEGORY_PACKS = ("mix", "database", "party", "spicy", "custom")

EASY_LETTERS = tuple("ABCDEFGHIJKLMNOPRSTUVW")
ALL_LETTERS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# ---------------------------------------------------------------------------
# 1. Database-Backed Categories (from EmojinaryWord + Wiktionary Lexicon)
# ---------------------------------------------------------------------------
DB_CATEGORIES: tuple[dict[str, Any], ...] = (
    # Primary EmojinaryWord categories
    {
        "id": "db_animal",
        "title": "🐾 Animals & Wildlife",
        "source": "database",
        "pack": "database",
        "wl_category": "animal",
        "topics": ("zoology", "animals", "birds", "insects", "dogs", "cats", "fish", "mammals", "reptiles"),
    },
    {
        "id": "db_food",
        "title": "🍕 Food & Drink",
        "source": "database",
        "pack": "database",
        "wl_category": "food",
        "topics": ("foods", "cooking", "beverages", "culinary", "dairy"),
    },
    {
        "id": "db_movie",
        "title": "🎬 Movies & Cinema",
        "source": "database",
        "pack": "database",
        "wl_category": "movie",
        "topics": ("film", "cinema"),
    },
    {
        "id": "db_tvshow",
        "title": "📺 TV Shows & Series",
        "source": "database",
        "pack": "database",
        "wl_category": "tvshow",
        "topics": ("television",),
    },
    {
        "id": "db_song",
        "title": "🎵 Famous Songs & Music Hits",
        "source": "database",
        "pack": "database",
        "wl_category": "song",
        "topics": (),
    },
    {
        "id": "db_place",
        "title": "🌍 Places, Cities & Landmarks",
        "source": "database",
        "pack": "database",
        "wl_category": "place",
        "topics": ("geography", "countries", "cities"),
    },
    {
        "id": "db_person",
        "title": "🌟 Famous People, Characters & Roles",
        "source": "database",
        "pack": "database",
        "wl_category": "person",
        "topics": ("people",),
    },
    {
        "id": "db_action",
        "title": "🏃 Actions & Verbs (Things You Do)",
        "source": "database",
        "pack": "database",
        "wl_category": "action",
        "topics": (),
    },
    {
        "id": "db_thing",
        "title": "📦 Everyday Objects & Things",
        "source": "database",
        "pack": "database",
        "wl_category": "thing",
        "topics": (),
    },
    # Wiktionary Semantic Topic-Cluster Categories
    {
        "id": "db_fruits_veg",
        "title": "🍎 Fruits, Vegetables & Plants",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("fruits", "vegetables", "botany", "berries", "trees", "flowers", "herbs"),
    },
    {
        "id": "db_desserts_baking",
        "title": "🧁 Desserts, Pastries, Breads & Cheese",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("desserts", "cakes and pastries", "breads", "cheeses", "sweets", "chocolate"),
    },
    {
        "id": "db_sports_games",
        "title": "⚽ Sports, Athletics & Games",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": (
            "sports",
            "baseball",
            "cricket",
            "basketball",
            "golf",
            "american football",
            "soccer",
            "tennis",
            "card games",
            "chess",
            "video games",
            "athletics",
        ),
    },
    {
        "id": "db_music",
        "title": "🎸 Music & Musical Instruments",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("music", "musical instruments", "singing", "jazz", "opera"),
    },
    {
        "id": "db_clothing",
        "title": "👕 Clothing, Shoes & Fashion",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("clothing", "footwear", "headwear", "fashion", "textiles", "jewelry"),
    },
    {
        "id": "db_computing_tech",
        "title": "💻 Computers, Internet & Tech",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("computing", "internet", "programming", "electronics", "software", "networking"),
    },
    {
        "id": "db_anatomy_medicine",
        "title": "🫀 Body Parts, Health & Medicine",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("anatomy", "medicine", "hair", "bones", "pathology", "dentistry"),
    },
    {
        "id": "db_transport_travel",
        "title": "✈️ Vehicles, Aviation & Nautical",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("nautical", "aviation", "automotive", "rail transport", "vehicles", "sailing"),
    },
    {
        "id": "db_jobs_roles",
        "title": "👩‍🚒 Jobs, Occupations & Professions",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("occupations", "military", "law", "legal", "business", "finance", "education"),
    },
    {
        "id": "db_science_nature",
        "title": "🔬 Science, Space & Nature",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("physics", "astronomy", "chemistry", "biology", "geology", "weather", "temperature"),
    },
    {
        "id": "db_buildings_home",
        "title": "🏛️ Buildings, Architecture & Tools",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("architecture", "buildings", "construction", "furniture", "tools", "engineering"),
    },
    {
        "id": "db_emotions_traits",
        "title": "😄 Emotions, Moods & Personality Traits",
        "source": "database",
        "pack": "database",
        "wl_category": None,
        "topics": ("personality", "emotions", "sleep", "talking", "psychology"),
    },
)

# ---------------------------------------------------------------------------
# 2. Fun Party Categories from the Web (Scattergories / Stop! Classics)
# ---------------------------------------------------------------------------
WEB_PARTY_CATEGORIES: tuple[dict[str, Any], ...] = (
    # Funny & Chaotic
    {"id": "web_fired", "title": "🔥 Things that will get you fired", "source": "party", "pack": "party"},
    {"id": "web_bad_smells", "title": "🤢 Bad smells", "source": "party", "pack": "party"},
    {"id": "web_late_excuse", "title": "⏰ Excuses for being late", "source": "party", "pack": "party"},
    {"id": "web_dont_touch", "title": "⚡ Things you shouldn't touch", "source": "party", "pack": "party"},
    {"id": "web_bad_date", "title": "💔 Bad first date locations", "source": "party", "pack": "party"},
    {"id": "web_dumpster", "title": "🗑️ Things found in a dumpster", "source": "party", "pack": "party"},
    {"id": "web_fears", "title": "🕷️ Irrational fears or phobias", "source": "party", "pack": "party"},
    {"id": "web_alone", "title": "👀 Things you do when nobody is watching", "source": "party", "pack": "party"},
    {"id": "web_hide_guests", "title": "🙈 Things you hide before guests arrive", "source": "party", "pack": "party"},
    {
        "id": "web_police",
        "title": "🚓 Things you shouldn't say to a police officer",
        "source": "party",
        "pack": "party",
    },
    {"id": "web_bad_habits", "title": "😬 Bad habits", "source": "party", "pack": "party"},
    {"id": "web_elevator", "title": "🛗 Things you whisper in an elevator", "source": "party", "pack": "party"},
    {"id": "web_call_sick", "title": "🤒 Excuses to call in sick", "source": "party", "pack": "party"},
    {"id": "web_buy_2am", "title": "🛒 Things people buy online at 2 AM", "source": "party", "pack": "party"},
    # Pop Culture, Media & Trivia
    {"id": "web_villains", "title": "🦹 Fictional villains", "source": "party", "pack": "party"},
    {"id": "web_superheroes", "title": "🦸 Superhero or mutant names", "source": "party", "pack": "party"},
    {"id": "web_disney", "title": "🏰 Disney or animated characters", "source": "party", "pack": "party"},
    {"id": "web_videogames", "title": "🎮 Video game characters or titles", "source": "party", "pack": "party"},
    {"id": "web_reality_tv", "title": "📺 Reality TV shows", "source": "party", "pack": "party"},
    {"id": "web_guilty_songs", "title": "🎧 Guilty pleasure songs or bands", "source": "party", "pack": "party"},
    {
        "id": "web_fictional_places",
        "title": "🗺️ Fictional places you'd want to live",
        "source": "party",
        "pack": "party",
    },
    {"id": "web_board_games", "title": "🎲 Board games or party games", "source": "party", "pack": "party"},
    # Food, Drink & Cravings
    {"id": "web_fast_food", "title": "🍔 Fast food chains or restaurants", "source": "party", "pack": "party"},
    {"id": "web_pizza_toppings", "title": "🍕 Pizza toppings", "source": "party", "pack": "party"},
    {
        "id": "web_eat_container",
        "title": "🥄 Things you eat straight out of the container",
        "source": "party",
        "pack": "party",
    },
    {"id": "web_midnight_snacks", "title": "🌙 Midnight snacks", "source": "party", "pack": "party"},
    {"id": "web_breakfast", "title": "🥣 Breakfast foods or cereal brands", "source": "party", "pack": "party"},
    {"id": "web_cocktails", "title": "🍹 Cocktail or drink ingredients", "source": "party", "pack": "party"},
    {"id": "web_in_fridge", "title": "🧊 Things you find in a fridge", "source": "party", "pack": "party"},
    {"id": "web_messy_foods", "title": "🍝 Foods that are messy to eat", "source": "party", "pack": "party"},
    {"id": "web_bbq_grill", "title": "🍖 Things grilled at a barbecue", "source": "party", "pack": "party"},
    {"id": "web_ice_cream", "title": "🍦 Ice cream flavors", "source": "party", "pack": "party"},
    # Travel, Outdoors & Everyday Life
    {"id": "web_vacations", "title": "🏖️ Vacation destinations", "source": "party", "pack": "party"},
    {"id": "web_carry_on", "title": "🧳 Things you pack in a carry-on suitcase", "source": "party", "pack": "party"},
    {"id": "web_road_trip", "title": "🚗 Things you see on a road trip", "source": "party", "pack": "party"},
    {"id": "web_garage", "title": "🧰 Items found in a garage or toolbox", "source": "party", "pack": "party"},
    {"id": "web_batteries", "title": "🔋 Things that use batteries or plug in", "source": "party", "pack": "party"},
    {"id": "web_at_beach", "title": "🐚 Things found at the beach", "source": "party", "pack": "party"},
    {"id": "web_camping", "title": "⛺ Camping essentials", "source": "party", "pack": "party"},
    {"id": "web_has_wheels", "title": "🛞 Things that have wheels", "source": "party", "pack": "party"},
    {"id": "web_waiting_room", "title": "🩺 Things in a doctor's waiting room", "source": "party", "pack": "party"},
    {"id": "web_lost_items", "title": "🔑 Items people lose all the time", "source": "party", "pack": "party"},
    # Adult / Spicy Party Prompts (18+)
    {"id": "spicy_red_flags", "title": "🚩 Red flags in a new partner", "source": "party", "pack": "spicy"},
    {
        "id": "spicy_dating_lies",
        "title": "📱 Things people lie about on dating profiles",
        "source": "party",
        "pack": "spicy",
    },
    {"id": "spicy_coworkers", "title": "💼 Things you complain about to coworkers", "source": "party", "pack": "spicy"},
    {"id": "spicy_pharmacy", "title": "💊 Awkward things to buy at a pharmacy", "source": "party", "pack": "spicy"},
    {"id": "spicy_hungover", "title": "🤕 Things you do when you're hungover", "source": "party", "pack": "spicy"},
    {
        "id": "spicy_mute_life",
        "title": "🔇 Things you wish you could mute in real life",
        "source": "party",
        "pack": "spicy",
    },
    {"id": "spicy_inlaw_gifts", "title": "🎁 Terrible gifts to give your in-laws", "source": "party", "pack": "spicy"},
    {"id": "spicy_ruin_party", "title": "🎉 Things that instantly ruin a party", "source": "party", "pack": "spicy"},
    {
        "id": "spicy_leave_early",
        "title": "🚪 Excuses to leave a social event early",
        "source": "party",
        "pack": "spicy",
    },
    {
        "id": "spicy_never_fire",
        "title": "🔥 Things you should never throw into a fire",
        "source": "party",
        "pack": "spicy",
    },
    {"id": "spicy_text_ex", "title": "💬 Things people text their ex at midnight", "source": "party", "pack": "spicy"},
    {"id": "spicy_tax_deduct", "title": "💸 Things you wish were tax-deductible", "source": "party", "pack": "spicy"},
)

_DB_CAT_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in DB_CATEGORIES}
_ALL_PRESET_BY_ID: dict[str, dict[str, Any]] = {
    **{c["id"]: c for c in DB_CATEGORIES},
    **{c["id"]: c for c in WEB_PARTY_CATEGORIES},
}


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
def _build_english_db_category_map() -> dict[str, tuple[str, ...]]:
    """Build canonical English word lists for every DB_CATEGORIES entry from wordlists.json + wiktionary_lexicon.json."""
    wl = _load_wordlists_data()
    lex = _load_lexicon_data()

    by_wl_cat: dict[str, set[str]] = defaultdict(set)
    for item in wl.get("emojinary", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            word = str(item[0]).strip()
            cat = str(item[1]).strip().lower()
            if word:
                by_wl_cat[cat].add(word)

    result: dict[str, tuple[str, ...]] = {}
    for cdef in DB_CATEGORIES:
        cid = cdef["id"]
        words: set[str] = set()
        wl_cat = cdef.get("wl_category")
        if wl_cat and wl_cat in by_wl_cat:
            words.update(by_wl_cat[wl_cat])
        topic_tags = {t.lower() for t in cdef.get("topics", ())}
        if topic_tags:
            for w_key, entry in lex.items():
                entry_topics = {str(t).lower() for t in entry.get("topics", [])}
                if entry_topics & topic_tags:
                    words.add(w_key)
        result[cid] = tuple(sorted(words, key=lambda s: s.lower()))
    return result


@lru_cache(maxsize=64)
def get_db_category_words(cat_id: str, lang_code: str = "en") -> tuple[str, ...]:
    """Return localized + canonical words for a database category."""
    en_map = _build_english_db_category_map()
    base_words = en_map.get(cat_id, ())
    if not base_words:
        return ()

    norm_lang = normalize_language_code(lang_code)
    if norm_lang == "en":
        return base_words

    lex_key = get_lexicon_language_key(norm_lang)
    lex = _load_lexicon_data()
    localized: list[str] = []
    seen: set[str] = set()

    for w in base_words:
        entry = lex.get(w.lower(), {})
        translations = entry.get("translations") or {}
        vals = translations.get(lex_key) or translations.get(norm_lang) or []
        for v in vals:
            sv = str(v).strip()
            nv = normalize_text(sv)
            if sv and nv and nv not in seen:
                seen.add(nv)
                localized.append(sv)
        # Keep English fallback terms as well so bilingual / English answers still count
        nw = normalize_text(w)
        if nw and nw not in seen:
            seen.add(nw)
            localized.append(w)

    return tuple(localized)


def normalize_answer(text: str | None) -> str:
    """Normalize a player's submitted answer for duplicate clash comparison."""
    norm = normalize_text(text)
    if not norm:
        return ""
    # Strip leading articles ('the ', 'a ', 'an ') only if multiple words exist
    parts = norm.split()
    if len(parts) > 1 and parts[0] in ("the", "a", "an"):
        return " ".join(parts[1:])
    return norm


def starts_with_letter(text: str | None, letter: str) -> bool:
    """Return True if the submitted answer is >= 2 chars and starts with `letter` (allowing leading 'The/A/An' if main word matches)."""
    if not text or not letter:
        return False
    target = normalize_text(letter)[:1].upper()
    if not target:
        return False
    raw_norm = normalize_text(text)
    if len(raw_norm.replace(" ", "")) < 2:
        return False
    if raw_norm[0].upper() == target:
        return True
    stripped = normalize_answer(text)
    return bool(stripped and len(stripped.replace(" ", "")) >= 2 and stripped[0].upper() == target)


def get_db_words_for_letter(cat_id: str, letter: str, lang_code: str = "en") -> list[str]:
    """Return words in `cat_id` that start with `letter` in `lang_code`."""
    if cat_id not in _DB_CAT_BY_ID or not letter:
        return []
    target = letter.strip()[:1].upper()
    norm_lang = normalize_language_code(lang_code)
    lex_key = get_lexicon_language_key(norm_lang)
    lex = _load_lexicon_data()
    en_words = _build_english_db_category_map().get(cat_id, ())

    matches: list[str] = []
    seen: set[str] = set()

    # Prefer target-language terms first when room language != 'en'
    if norm_lang != "en":
        for w in en_words:
            entry = lex.get(w.lower(), {})
            translations = entry.get("translations") or {}
            vals = translations.get(lex_key) or translations.get(norm_lang) or []
            for v in vals:
                sv = str(v).strip()
                nv = normalize_text(sv)
                if nv and nv[0].upper() == target and nv not in seen:
                    seen.add(nv)
                    matches.append(sv.title() if sv.islower() else sv)

    for w in en_words:
        nv = normalize_text(w)
        if nv and nv[0].upper() == target and nv not in seen:
            seen.add(nv)
            matches.append(w.title() if w.islower() else w)
        entry = lex.get(w.lower(), {})
        for alias in entry.get("aliases") or []:
            na = normalize_text(str(alias))
            if na and na[0].upper() == target and na not in seen:
                seen.add(na)
                matches.append(str(alias))

    return matches


def get_sample_db_words(cat_id: str, letter: str, lang_code: str = "en", limit: int = 8) -> list[str]:
    """Return up to `limit` clean sample dictionary words for `cat_id` starting with `letter`."""
    words = get_db_words_for_letter(cat_id, letter, lang_code=lang_code)
    if not words:
        return []
    # Prefer concise 1-2 word examples
    clean = [w for w in words if len(w) <= 22]
    pool = clean if clean else words
    return pool[:limit]


@lru_cache(maxsize=8)
def _build_global_normalized_lexicon(lang_code: str = "en") -> frozenset[str]:
    """Return a set of all normalized words in our database + Wiktionary lexicon for fast lookup."""
    wl = _load_wordlists_data()
    lex = _load_lexicon_data()
    norm_lang = normalize_language_code(lang_code)
    lex_key = get_lexicon_language_key(norm_lang)

    terms: set[str] = set()
    for item in wl.get("emojinary", []):
        if isinstance(item, (list, tuple)) and item:
            nw = normalize_answer(str(item[0]))
            if nw:
                terms.add(nw)
                terms.add(normalize_text(str(item[0])))
    for w_key, entry in lex.items():
        nw = normalize_answer(w_key)
        if nw:
            terms.add(nw)
        for alias in entry.get("aliases") or []:
            na = normalize_answer(str(alias))
            if na:
                terms.add(na)
        if norm_lang != "en":
            translations = entry.get("translations") or {}
            for v in translations.get(lex_key) or translations.get(norm_lang) or []:
                nv = normalize_answer(str(v))
                if nv:
                    terms.add(nv)
    return frozenset(terms)


def is_word_in_db(candidate_text: str | None, cat_id: Optional[str] = None, lang_code: str = "en") -> bool:
    """Return True if `candidate_text` matches the specific DB category or our global Wiktionary/Emojinary lexicon."""
    norm_ans = normalize_answer(candidate_text)
    raw_norm = normalize_text(candidate_text)
    if not norm_ans:
        return False

    if cat_id and cat_id in _DB_CAT_BY_ID:
        cat_words = get_db_category_words(cat_id, lang_code=lang_code)
        for w in cat_words:
            if normalize_answer(w) == norm_ans or normalize_text(w) == raw_norm:
                return True

    global_set = _build_global_normalized_lexicon(lang_code)
    return norm_ans in global_set or raw_norm in global_set


def get_all_preset_categories(pack: str = "mix") -> list[dict[str, Any]]:
    """Return preset category definitions for the requested `pack`."""
    p = (pack or "mix").strip().lower()
    if p == "database":
        return [dict(c) for c in DB_CATEGORIES]
    if p == "party":
        return [dict(c) for c in WEB_PARTY_CATEGORIES if c["pack"] == "party"]
    if p == "spicy":
        return [dict(c) for c in WEB_PARTY_CATEGORIES]
    # "mix" or "custom" fallback includes DB + standard Party prompts
    return [dict(c) for c in DB_CATEGORIES] + [dict(c) for c in WEB_PARTY_CATEGORIES if c["pack"] == "party"]


def pick_letter_for_category(
    category: dict[str, Any],
    lang_code: str = "en",
    easy_letters_only: bool = True,
    last_letter: str = "",
) -> str:
    """Pick a valid starting letter, ensuring DB categories have dictionary words for that letter."""
    pool = list(EASY_LETTERS if easy_letters_only else ALL_LETTERS)
    cat_id = category.get("id", "")

    if cat_id in _DB_CAT_BY_ID:
        # Filter letters that have at least 2 words in this DB category (or at least 1)
        rich_letters = [ch for ch in pool if len(get_db_words_for_letter(cat_id, ch, lang_code=lang_code)) >= 2]
        if not rich_letters:
            rich_letters = [ch for ch in pool if len(get_db_words_for_letter(cat_id, ch, lang_code=lang_code)) >= 1]
        if rich_letters:
            pool = rich_letters

    if last_letter and len(pool) > 1 and last_letter.upper() in pool:
        pool = [ch for ch in pool if ch != last_letter.upper()]

    return _sys_rng.choice(pool)


def pick_category_and_letter(
    pack: str = "mix",
    lang_code: str = "en",
    used_categories: Optional[list[str]] = None,
    custom_categories: Optional[list[dict[str, Any]]] = None,
    easy_letters_only: bool = True,
    last_letter: str = "",
    forced_category_title: str = "",
    forced_letter: str = "",
) -> tuple[dict[str, Any], str]:
    """Select the next category and starting letter for a Stop! round."""
    used_set = set(used_categories or [])
    custom_list = custom_categories or []

    chosen_cat: Optional[dict[str, Any]] = None

    if forced_category_title and forced_category_title.strip():
        title_clean = forced_category_title.strip()[:90]
        # Check if it matches a known preset
        for preset in _ALL_PRESET_BY_ID.values():
            if preset["id"] == title_clean or preset["title"].lower() == title_clean.lower():
                chosen_cat = dict(preset)
                break
        if not chosen_cat:
            chosen_cat = {
                "id": f"custom::{normalize_text(title_clean)}",
                "title": title_clean,
                "source": "custom",
                "pack": "custom",
            }

    if not chosen_cat and custom_list:
        unused_custom = [c for c in custom_list if c.get("id") not in used_set]
        if unused_custom and (pack == "custom" or _sys_rng.random() < 0.65):
            chosen_cat = dict(_sys_rng.choice(unused_custom))

    if not chosen_cat:
        presets = get_all_preset_categories(pack)
        unused_presets = [c for c in presets if c["id"] not in used_set]
        if not unused_presets:
            unused_presets = presets
        chosen_cat = dict(_sys_rng.choice(unused_presets))

    if forced_letter and forced_letter.strip() and forced_letter.strip()[0].isalpha():
        letter = forced_letter.strip()[0].upper()
    else:
        letter = pick_letter_for_category(
            chosen_cat,
            lang_code=lang_code,
            easy_letters_only=easy_letters_only,
            last_letter=last_letter,
        )

    return chosen_cat, letter

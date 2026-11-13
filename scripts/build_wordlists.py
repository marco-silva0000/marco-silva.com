#!/usr/bin/env python3
"""Build categorized, deduplicated Emojinary and Pictionary wordlists from open-source & CC0 sources.

Sources:
1. nick-aschenbach/game-words (MIT License)
2. dariusk/corpora (CC0 Public Domain)
3. imsky/wordlists (MIT License)
4. engichang1467/word-pictionary-list (MIT License)
5. Wikidata Query Service (CC0 Public Domain)

Usage:
    uv run python scripts/build_wordlists.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "emojinary" / "data" / "wordlists.json"

YEAR_SUFFIX_RE = re.compile(r"\s*\(\d{4}\)\s*$")
DISAMBIG_SUFFIX_RE = re.compile(
    r"\s*\((?:film|TV series|song|band|album|game|character|\d{4} film)\)\s*$", re.IGNORECASE
)
VALID_TEXT_RE = re.compile(r"^[A-Za-z0-9\s\-'.,!&:?/]+$")


def fetch_url(url: str) -> str:
    """Fetch URL content via curl (avoids OS CA bundle discrepancies across environments)."""
    return subprocess.check_output(["curl", "-sL", "--max-time", "30", url], text=True)


def fetch_wikidata(sparql: str) -> list[str]:
    """Query Wikidata SPARQL endpoint and return cleaned English labels."""
    try:
        out = subprocess.check_output(
            [
                "curl",
                "-sG",
                "--max-time",
                "30",
                "https://query.wikidata.org/sparql",
                "--data-urlencode",
                "format=json",
                "--data-urlencode",
                f"query={sparql}",
                "-H",
                "User-Agent: MarcoSilvaWordlistBuilder/1.0 (https://marco-silva.com)",
            ],
            text=True,
        )
        data = json.loads(out)
        return [b["label"]["value"] for b in data.get("results", {}).get("bindings", []) if "label" in b]
    except Exception as exc:
        print(f"  ⚠️ Wikidata query failed ({exc}); skipping this slice.", file=sys.stderr)
        return []


def clean_phrase(raw: str, max_len: int = 45, strip_year: bool = False) -> str | None:
    """Normalize whitespace, remove parenthetical suffixes, and reject noisy/too-short tokens."""
    text = str(raw or "").strip()
    if strip_year:
        text = YEAR_SUFFIX_RE.sub("", text).strip()
    text = DISAMBIG_SUFFIX_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text or len(text) < 2 or len(text) > max_len:
        return None
    if not any(ch.isalpha() for ch in text):
        return None
    if not VALID_TEXT_RE.match(text):
        return None
    return text


def add_emojinary(
    bucket: dict[tuple[str, str], tuple[str, str, int]],
    raw: str,
    category: str,
    difficulty: int,
    max_len: int = 45,
    strip_year: bool = False,
) -> None:
    cleaned = clean_phrase(raw, max_len=max_len, strip_year=strip_year)
    if not cleaned:
        return
    key = (cleaned.lower(), category)
    if key not in bucket:
        bucket[key] = (cleaned, category, difficulty)


def add_pictionary(pool: dict[str, dict[str, set[str]]], pos: str, raw: str, difficulty: str | None = None) -> None:
    cleaned = clean_phrase(raw, max_len=30)
    if not cleaned or " " in cleaned and pos in ("verb", "adjective"):
        # Prefer crisp single words for verb/adjective Pictionary prompts
        return
    lower = cleaned.lower()
    if len(lower) < 3:
        return
    if difficulty is None:
        if len(lower) <= 6:
            difficulty = "easy"
        elif len(lower) <= 10:
            difficulty = "medium"
        else:
            difficulty = "hard"
    pool[pos][difficulty].add(lower)


def collect_nick_aschenbach(
    emojinary_map: dict[tuple[str, str], tuple[str, str, int]],
    pictionary_pool: dict[str, dict[str, set[str]]],
    sentence_pool: set[str],
) -> None:
    print("Fetching nick-aschenbach/game-words...")
    raw_yaml = fetch_url(
        "https://raw.githubusercontent.com/nick-aschenbach/game-words/master/assets/game_words/game_words.yaml"
    )
    data = yaml.safe_load(raw_yaml) or {}

    cp = data.get("catchphrase", {})
    for w in cp.get("easy", []):
        add_emojinary(emojinary_map, w, "thing", 1)
        add_pictionary(pictionary_pool, "noun", w, "easy")
    for w in cp.get("medium", []):
        add_emojinary(emojinary_map, w, "thing", 2)
        add_pictionary(pictionary_pool, "noun", w, "medium")
    for w in cp.get("hard", []):
        add_emojinary(emojinary_map, w, "thing", 3)
        add_pictionary(pictionary_pool, "noun", w, "hard")
    for w in cp.get("household", []):
        add_emojinary(emojinary_map, w, "thing", 1)
        add_pictionary(pictionary_pool, "noun", w, "easy")
    for w in cp.get("animals", []):
        add_emojinary(emojinary_map, w, "animal", 1)
        add_pictionary(pictionary_pool, "noun", w, "easy")
    for w in cp.get("food", []):
        add_emojinary(emojinary_map, w, "food", 1)
        add_pictionary(pictionary_pool, "noun", w, "easy")
    for w in cp.get("travel", []):
        add_emojinary(emojinary_map, w, "place", 2)
    for w in cp.get("people", []):
        add_emojinary(emojinary_map, w, "person", 2)

    hol = data.get("holidays", {})
    for key in ("halloween", "christmas", "thanksgiving", "newyears", "spring", "valentineword", "independence"):
        for w in hol.get(key, []):
            add_emojinary(emojinary_map, w, "thing", 1)
    for key in ("christmassong", "valentinesong"):
        for w in hol.get(key, []):
            add_emojinary(emojinary_map, w, "song", 1)
    for w in hol.get("valentinesaying", []):
        add_emojinary(emojinary_map, w, "phrase", 2)

    pic = data.get("pictionary", {})
    for w in pic.get("easy", []):
        add_emojinary(emojinary_map, w, "thing", 1)
        add_pictionary(pictionary_pool, "noun", w, "easy")
    for w in pic.get("medium", []):
        add_emojinary(emojinary_map, w, "thing", 2)
        add_pictionary(pictionary_pool, "noun", w, "medium")
    for w in pic.get("difficult", []) + pic.get("hard", []):
        add_emojinary(emojinary_map, w, "thing", 3)
        add_pictionary(pictionary_pool, "noun", w, "hard")
    for w in pic.get("idioms", []):
        add_emojinary(emojinary_map, w, "phrase", 2)
        cleaned = clean_phrase(w, max_len=55)
        if cleaned:
            sentence_pool.add(cleaned)
    for w in pic.get("characters", []):
        add_emojinary(emojinary_map, w, "person", 2)
    for w in pic.get("movies", []):
        add_emojinary(emojinary_map, w, "movie", 2)

    ch = data.get("charades", {})
    for w in ch.get("easy", []):
        add_emojinary(emojinary_map, w, "action", 1)
    for w in ch.get("medium", []):
        add_emojinary(emojinary_map, w, "action", 2)
    for w in ch.get("difficult", []) + ch.get("hard", []):
        add_emojinary(emojinary_map, w, "action", 3)
    for w in ch.get("actions", []):
        add_emojinary(emojinary_map, w, "action", 1)
        add_pictionary(pictionary_pool, "verb", w)


def fetch_corpora_json(rel_path: str) -> dict:
    raw = fetch_url(f"https://raw.githubusercontent.com/dariusk/corpora/master/{rel_path}")
    return json.loads(raw)


def collect_dariusk_corpora(
    emojinary_map: dict[tuple[str, str], tuple[str, str, int]],
    pictionary_pool: dict[str, dict[str, set[str]]],
    sentence_pool: set[str],
) -> None:
    print("Fetching dariusk/corpora...")
    movies = fetch_corpora_json("data/film-tv/popular-movies.json").get("popular-movies", [])
    for m in movies:
        add_emojinary(emojinary_map, m, "movie", 2, strip_year=True)

    tv_shows = fetch_corpora_json("data/film-tv/tv_shows.json").get("tv_shows", [])
    for show in tv_shows[:350]:
        add_emojinary(emojinary_map, show, "tvshow", 2, max_len=35)

    for a in fetch_corpora_json("data/animals/common.json").get("animals", []):
        add_emojinary(emojinary_map, a, "animal", 1)
        add_pictionary(pictionary_pool, "noun", a, "easy")
    for d in fetch_corpora_json("data/animals/dinosaurs.json").get("dinosaurs", [])[:80]:
        add_emojinary(emojinary_map, d, "animal", 3)

    for f_path, key, diff in (
        ("data/foods/fruits.json", "fruits", 1),
        ("data/foods/vegetables.json", "vegetables", 1),
        ("data/foods/pizzaToppings.json", "pizzaToppings", 1),
        ("data/foods/condiments.json", "condiments", 2),
    ):
        for item in fetch_corpora_json(f_path).get(key, []):
            add_emojinary(emojinary_map, item, "food", diff)
            if diff == 1:
                add_pictionary(pictionary_pool, "noun", item, "easy")

    bp = fetch_corpora_json("data/foods/breads_and_pastries.json")
    for item in bp.get("breads", []) + bp.get("pastries", []):
        add_emojinary(emojinary_map, item, "food", 2)

    for sw in fetch_corpora_json("data/foods/sandwiches.json").get("sandwiches", []):
        if isinstance(sw, dict) and sw.get("name"):
            add_emojinary(emojinary_map, sw["name"], "food", 2)

    for obj in fetch_corpora_json("data/objects/objects.json").get("objects", []):
        add_emojinary(emojinary_map, obj, "thing", 1)
        add_pictionary(pictionary_pool, "noun", obj)
    for cl in fetch_corpora_json("data/objects/clothing.json").get("clothes", []):
        add_emojinary(emojinary_map, cl, "thing", 1)
        add_pictionary(pictionary_pool, "noun", cl)
    for bg in fetch_corpora_json("data/games/board_games.json").get("games", [])[:100]:
        add_emojinary(emojinary_map, bg, "thing", 2)

    for occ in fetch_corpora_json("data/humans/occupations.json").get("occupations", [])[:200]:
        add_emojinary(emojinary_map, occ, "person", 2)
    for duo in fetch_corpora_json("data/humans/famousDuos.json").get("famousDuos", []):
        add_emojinary(emojinary_map, duo, "person", 2)
    for sci in fetch_corpora_json("data/humans/scientists.json").get("scientists", [])[:80]:
        add_emojinary(emojinary_map, sci, "person", 3)
    for g in fetch_corpora_json("data/mythology/greek_gods.json").get("greek_gods", []):
        add_emojinary(emojinary_map, g, "person", 2)
    for m in fetch_corpora_json("data/mythology/monsters.json").get("names", []):
        add_emojinary(emojinary_map, m, "person", 2)
    norse = fetch_corpora_json("data/mythology/norse_gods.json").get("norse_deities", {})
    for g in norse.get("gods", []) + norse.get("goddesses", []):
        add_emojinary(emojinary_map, g, "person", 2)

    proverbs_data = fetch_corpora_json("data/words/proverbs.json").get("proverbs", [])
    for group in proverbs_data:
        if isinstance(group, dict):
            for phrases in group.values():
                for p in phrases[:12]:
                    add_emojinary(emojinary_map, p, "phrase", 3, max_len=55)
                    cleaned = clean_phrase(p, max_len=55)
                    if cleaned:
                        sentence_pool.add(cleaned)


def collect_imsky_wordlists(
    emojinary_map: dict[tuple[str, str], tuple[str, str, int]],
    pictionary_pool: dict[str, dict[str, set[str]]],
) -> None:
    print("Fetching imsky/wordlists...")
    noun_topics = [
        ("nouns/animals.txt", "animal", 1),
        ("nouns/apex_predators.txt", "animal", 2),
        ("nouns/birds.txt", "animal", 2),
        ("nouns/cats.txt", "animal", 2),
        ("nouns/dogs.txt", "animal", 2),
        ("nouns/fish.txt", "animal", 2),
        ("nouns/fast_food.txt", "food", 1),
        ("nouns/food.txt", "food", 1),
        ("nouns/fruit.txt", "food", 1),
        ("nouns/cheese.txt", "food", 2),
        ("nouns/buildings.txt", "thing", 1),
        ("nouns/furniture.txt", "thing", 1),
        ("nouns/houses.txt", "thing", 2),
        ("nouns/music_instruments.txt", "thing", 1),
        ("nouns/plants.txt", "thing", 2),
        ("nouns/sports.txt", "thing", 1),
        ("nouns/astronomy.txt", "thing", 2),
        ("nouns/ghosts.txt", "thing", 2),
    ]
    for path, cat, diff in noun_topics:
        lines = fetch_url(f"https://raw.githubusercontent.com/imsky/wordlists/master/{path}").splitlines()
        for line in lines:
            w = line.strip()
            if w and not w.startswith("#"):
                add_emojinary(emojinary_map, w, cat, diff)
                add_pictionary(pictionary_pool, "noun", w)

    verb_topics = [
        "verbs/art.txt",
        "verbs/communication.txt",
        "verbs/cooking.txt",
        "verbs/creation.txt",
        "verbs/driving.txt",
        "verbs/fire.txt",
        "verbs/look.txt",
        "verbs/movement.txt",
        "verbs/music.txt",
        "verbs/sports.txt",
        "verbs/thought.txt",
    ]
    for path in verb_topics:
        lines = fetch_url(f"https://raw.githubusercontent.com/imsky/wordlists/master/{path}").splitlines()
        for line in lines:
            w = line.strip()
            if w and not w.startswith("#"):
                add_emojinary(emojinary_map, w, "action", 1 if len(w) <= 6 else 2)
                add_pictionary(pictionary_pool, "verb", w)

    adj_topics = [
        "adjectives/appearance.txt",
        "adjectives/character.txt",
        "adjectives/colors.txt",
        "adjectives/emotions.txt",
        "adjectives/food.txt",
        "adjectives/shape.txt",
        "adjectives/size.txt",
        "adjectives/sound.txt",
        "adjectives/speed.txt",
        "adjectives/taste.txt",
        "adjectives/temperature.txt",
        "adjectives/weather.txt",
    ]
    for path in adj_topics:
        lines = fetch_url(f"https://raw.githubusercontent.com/imsky/wordlists/master/{path}").splitlines()
        for line in lines:
            w = line.strip()
            if w and not w.startswith("#"):
                add_pictionary(pictionary_pool, "adjective", w)


def collect_engichang(
    emojinary_map: dict[tuple[str, str], tuple[str, str, int]],
    pictionary_pool: dict[str, dict[str, set[str]]],
) -> None:
    print("Fetching engichang1467/word-pictionary-list...")
    lines = fetch_url(
        "https://raw.githubusercontent.com/engichang1467/word-pictionary-list/master/myWords.txt"
    ).splitlines()
    for w in lines[:-1]:  # Last line in upstream file is truncated ("Angr")
        cleaned = w.strip()
        if cleaned and len(cleaned) >= 3:
            add_emojinary(emojinary_map, cleaned, "thing", 1)
            add_pictionary(pictionary_pool, "noun", cleaned, "easy")


def collect_wikidata(emojinary_map: dict[tuple[str, str], tuple[str, str, int]]) -> None:
    print("Fetching Wikidata Query Service (CC0)...")
    sparql_slices = [
        # Oscar Best Picture / Best Director / major award films
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P31 wd:Q11424; wdt:P166 wd:Q102427; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 150',
            "movie",
            1,
        ),
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P31 wd:Q11424; wdt:P166 wd:Q103916; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 150',
            "movie",
            2,
        ),
        # Emmy-winning TV series
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P31 wd:Q5398426; wdt:P166 wd:Q989439; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 150',
            "tvshow",
            1,
        ),
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P31 wd:Q5398426; wdt:P166 wd:Q989453; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 150',
            "tvshow",
            2,
        ),
        # Grammy Song/Record of the Year winners
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P31 wd:Q7366; wdt:P166 wd:Q1027904; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 100',
            "song",
            1,
        ),
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P31 wd:Q7366; wdt:P166 wd:Q112243; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 100',
            "song",
            2,
        ),
        # Famous UNESCO landmarks
        (
            'SELECT DISTINCT ?label WHERE { ?item wdt:P1435 wd:Q9259; rdfs:label ?label. FILTER(LANG(?label) = "en") } LIMIT 150',
            "place",
            2,
        ),
    ]
    for sparql, cat, diff in sparql_slices:
        labels = fetch_wikidata(sparql)
        for lbl in labels:
            add_emojinary(emojinary_map, lbl, cat, diff, max_len=45)


def main() -> None:
    emojinary_map: dict[tuple[str, str], tuple[str, str, int]] = {}
    pictionary_pool: dict[str, dict[str, set[str]]] = {
        "noun": {"easy": set(), "medium": set(), "hard": set()},
        "verb": {"easy": set(), "medium": set(), "hard": set()},
        "adjective": {"easy": set(), "medium": set(), "hard": set()},
    }
    sentence_pool: set[str] = set()

    collect_nick_aschenbach(emojinary_map, pictionary_pool, sentence_pool)
    collect_dariusk_corpora(emojinary_map, pictionary_pool, sentence_pool)
    collect_imsky_wordlists(emojinary_map, pictionary_pool)
    collect_engichang(emojinary_map, pictionary_pool)
    collect_wikidata(emojinary_map)

    emojinary_list = sorted(emojinary_map.values(), key=lambda x: (x[1], x[2], x[0].lower()))
    pictionary_out = {
        pos: {diff: sorted(words) for diff, words in diffs.items()} for pos, diffs in pictionary_pool.items()
    }
    pictionary_out["sentence"] = sorted(sentence_pool)

    payload = {
        "sources": [
            {"name": "nick-aschenbach/game-words", "license": "MIT"},
            {"name": "dariusk/corpora", "license": "CC0-1.0"},
            {"name": "imsky/wordlists", "license": "MIT"},
            {"name": "engichang1467/word-pictionary-list", "license": "MIT"},
            {"name": "Wikidata Query Service", "license": "CC0-1.0"},
        ],
        "emojinary": [list(item) for item in emojinary_list],
        "pictionary": pictionary_out,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    from collections import Counter

    cat_counts = Counter(cat for _, cat, _ in emojinary_list)
    print(f"\n✅ Wrote {len(emojinary_list)} Emojinary entries to {OUT_PATH.relative_to(PROJECT_ROOT)}:")
    for cat, cnt in sorted(cat_counts.items()):
        print(f"   - {cat:8s}: {cnt}")
    print(
        f"✅ Pictionary pools: noun={sum(len(v) for v in pictionary_out['noun'].values())}, "
        f"verb={sum(len(v) for v in pictionary_out['verb'].values())}, "
        f"adjective={sum(len(v) for v in pictionary_out['adjective'].values())}, "
        f"sentence={len(pictionary_out['sentence'])}"
    )


if __name__ == "__main__":
    main()

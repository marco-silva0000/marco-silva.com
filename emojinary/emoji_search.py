"""Robust emoji search engine with synonyms, 14+64 language support, flags/symbols, and typo tolerance."""

import difflib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import emoji
from django.http import JsonResponse

_DATA_DIR = Path(__file__).resolve().parent / "data"
_KEYWORDS_PATH = _DATA_DIR / "emoji_keywords.json"
_WIKTIONARY_PATH = _DATA_DIR / "wiktionary_lexicon.json"

_SKIN_TONES = ("\U0001f3fb", "\U0001f3fc", "\U0001f3fd", "\U0001f3fe", "\U0001f3ff")
_WIKT_TAG_RE = re.compile(r"<[^>]+>")
_FLAG_LABELS = [
    "flag",
    "country",
    "nation",
    "banner",
    "bandeira",
    "bandera",
    "bandiera",
    "drapeau",
    "flagge",
    "flaga",
    "lippu",
    "flagga",
    "bayraq",
    "bayrak",
    "флаг",
    "знамя",
    "σημαία",
]

# Extra high-signal synonyms and priority homelab languages (pt, el, fi, pl, sv, az, ru, es, it)
CONCEPT_BOOST_KEYWORDS: dict[str, list[str]] = {
    "🔥": ["flame", "blaze", "inferno", "lit", "hot", "burn", "φωτιά", "tuli", "ogień", "eld", "od", "ateş"],
    "❤️": [
        "love",
        "heart",
        "valentine",
        "romance",
        "καρδιά",
        "sydän",
        "serce",
        "hjärta",
        "ürək",
        "amor",
        "amore",
        "сердце",
    ],
    "👑": [
        "crown",
        "king",
        "queen",
        "royal",
        "royalty",
        "monarch",
        "tiara",
        "coroa",
        "στέμμα",
        "kruunu",
        "korona",
        "krona",
        "tac",
        "корона",
    ],
    "🚗": [
        "car",
        "auto",
        "automobile",
        "vehicle",
        "drive",
        "αυτοκίνητο",
        "samochód",
        "bil",
        "maşın",
        "carro",
        "coche",
        "машина",
    ],
    "⚡": [
        "lightning",
        "thunder",
        "thunderbolt",
        "zap",
        "bolt",
        "electric",
        "electricity",
        "fast",
        "speed",
        "shock",
        "power",
        "flash",
        "αστραπή",
        "salama",
        "błyskawica",
        "blixt",
        "ildırım",
    ],
    "😂": ["lol", "lmao", "haha", "laugh", "laughing", "funny", "hilarious", "tears", "cry", "giggle"],
    "🤣": ["rofl", "lmao", "haha", "laugh", "hilarious", "funny"],
    "😭": ["cry", "crying", "sob", "tears", "sad", "weep", "bawl", "chorar", "llorar", "плакать", "κλαίω"],
    "😢": ["sad", "cry", "tear", "unhappy", "upset", "triste", "грустный", "λυπημένος"],
    "😡": ["angry", "mad", "rage", "furious", "annoyed", "bravo", "enojado", "zły", "arg", "θυμωμένος", "злой"],
    "💀": ["skull", "dead", "death", "skeleton", "spooky", "creepy", "caveira", "calavera", "κρανίο", "череп"],
    "👻": ["ghost", "spooky", "boo", "spirit", "phantom", "halloween", "fantasma", "φάντασμα", "призрак"],
    "👽": ["alien", "ufo", "extraterrestrial", "et", "space", "et", "αλλοδαπός", "инопланетянин", "extraterrestre"],
    "🤖": ["robot", "bot", "android", "cyborg", "ai", "mech", "робот", "ρομπότ"],
    "🐶": [
        "dog",
        "puppy",
        "pup",
        "hound",
        "woof",
        "bark",
        "pet",
        "cachorro",
        "cão",
        "perro",
        "σκύλος",
        "koira",
        "pies",
        "hund",
        "it",
        "собака",
    ],
    "🐱": [
        "cat",
        "kitten",
        "kitty",
        "meow",
        "feline",
        "pet",
        "gato",
        "γάτα",
        "kissa",
        "kot",
        "katt",
        "pişik",
        "кошка",
        "кот",
    ],
    "🦁": ["lion", "king", "roar", "cat", "jungle", "leão", "león", "λιοντάρι", "leijona", "lew", "lejon", "лев"],
    "🦖": ["dinosaur", "dino", "trex", "t-rex", "jurassic", "reptile", "dinossauro", "δινόσαυρος", "динозавр"],
    "🍎": ["apple", "fruit", "malus", "maçã", "manzana", "μήλο", "omena", "jabłko", "äpple", "alma", "яблоко"],
    "🍌": ["banana", "fruit", "yellow", "peel", "μπανάνα", "banaani", "banan", "банан"],
    "🍕": ["pizza", "slice", "pepperoni", "cheese", "italian", "πίτσα", "пицца"],
    "🍺": [
        "beer",
        "pint",
        "drink",
        "alcohol",
        "pub",
        "lager",
        "ale",
        "cheers",
        "cerveja",
        "cerveza",
        "μπύρα",
        "olut",
        "piwo",
        "öl",
        "пиво",
    ],
    "☕": ["coffee", "espresso", "latte", "tea", "cafe", "café", "καφές", "kahvi", "kawa", "kaffe", "qəhvə", "кофе"],
    "🏠": ["house", "home", "building", "cottage", "casa", "σπίτι", "talo", "dom", "hus", "ev", "дом"],
    "✈️": [
        "airplane",
        "plane",
        "flight",
        "fly",
        "travel",
        "jet",
        "airport",
        "avião",
        "avión",
        "αεροπλάνο",
        "lentokone",
        "samolot",
        "flygplan",
        "təyyarə",
        "самолёт",
    ],
    "🚀": [
        "rocket",
        "space",
        "launch",
        "spaceship",
        "moon",
        "foguete",
        "cohete",
        "πύραυλος",
        "raketti",
        "rakieta",
        "raket",
        "ракета",
    ],
    "⚽": [
        "soccer",
        "football",
        "ball",
        "sport",
        "goal",
        "futebol",
        "fútbol",
        "ποδόσφαιρο",
        "jalkapallo",
        "piłka",
        "fotboll",
        "futbol",
        "футбол",
    ],
    "🏆": [
        "trophy",
        "winner",
        "win",
        "champion",
        "prize",
        "award",
        "cup",
        "troféu",
        "τρόπαιο",
        "palkinto",
        "trofeum",
        "кубок",
    ],
    "🎬": [
        "movie",
        "film",
        "cinema",
        "clapper",
        "action",
        "director",
        "filme",
        "película",
        "ταινία",
        "elokuva",
        "фильм",
    ],
    "🎵": [
        "music",
        "song",
        "note",
        "melody",
        "tune",
        "sing",
        "música",
        "μουσική",
        "musiikki",
        "muzyka",
        "musik",
        "musiqi",
        "музыка",
    ],
    "💰": [
        "money",
        "cash",
        "rich",
        "bag",
        "dollar",
        "wealth",
        "dinheiro",
        "χρήματα",
        "raha",
        "pieniądze",
        "pengar",
        "pul",
        "деньги",
    ],
    "💎": [
        "diamond",
        "gem",
        "jewel",
        "crystal",
        "precious",
        "rich",
        "diamante",
        "διαμάντι",
        "timantti",
        "diament",
        "алмаз",
    ],
    "💡": ["idea", "bulb", "light", "bright", "think", "smart", "ideia", "ιδέα", "idea", "pomysł", "idé", "идея"],
    "⏰": [
        "alarm",
        "clock",
        "time",
        "wake",
        "morning",
        "timer",
        "relógio",
        "ρολόι",
        "kello",
        "zegar",
        "klocka",
        "saat",
        "часы",
    ],
    "⏳": [
        "hourglass",
        "time",
        "wait",
        "sand",
        "timer",
        "ampulheta",
        "κλεψύδρα",
        "tiimalasi",
        "klepsydra",
        "timglas",
        "песочные",
    ],
    "⚠️": [
        "warning",
        "alert",
        "danger",
        "caution",
        "hazard",
        "attention",
        "aviso",
        "perigo",
        "προσοχή",
        "varoitus",
        "ostrzeżenie",
        "varning",
        "xəbərdarlıq",
        "внимание",
    ],
    "♻️": [
        "recycle",
        "recycling",
        "eco",
        "green",
        "reuse",
        "environment",
        "reciclagem",
        "ανακύκλωση",
        "kierrätys",
        "recykling",
        "återvinning",
    ],
    "✅": [
        "check",
        "yes",
        "done",
        "ok",
        "approve",
        "correct",
        "right",
        "success",
        "sim",
        "certo",
        "ναι",
        "kyllä",
        "tak",
        "ja",
        "bəli",
        "да",
    ],
    "❌": [
        "no",
        "wrong",
        "cross",
        "cancel",
        "delete",
        "error",
        "close",
        "false",
        "não",
        "όχι",
        "ei",
        "nie",
        "nej",
        "yox",
        "нет",
    ],
    "🚫": [
        "ban",
        "no",
        "forbidden",
        "prohibited",
        "stop",
        "block",
        "proibido",
        "απαγορεύεται",
        "kielletty",
        "zakaz",
        "förbjuden",
    ],
    "❓": [
        "question",
        "what",
        "why",
        "who",
        "ask",
        "mystery",
        "unknown",
        "pergunta",
        "pregunta",
        "ερώτηση",
        "kysymys",
        "pytanie",
        "fråga",
        "sual",
        "вопрос",
    ],
    "❗": ["exclamation", "important", "alert", "wow", "bang", "surprised"],
    "➕": ["plus", "add", "math", "positive", "cross", "mais", "συν", "plus", "плюс"],
    "➖": ["minus", "subtract", "math", "negative", "menos", "μείον", "minus", "минус"],
    "⬆️": ["up", "north", "arrow", "above", "top", "cima", "arriba", "πάνω", "ylös", "góra", "upp", "вверх"],
    "⬇️": ["down", "south", "arrow", "below", "bottom", "baixo", "abajo", "κάτω", "alas", "dół", "ner", "вниз"],
    "⬅️": ["left", "west", "arrow", "back", "esquerda", "izquierda", "αριστερά", "vasen", "lewo", "vänster", "налево"],
    "➡️": [
        "right",
        "east",
        "arrow",
        "next",
        "forward",
        "direita",
        "derecha",
        "δεξιά",
        "oikea",
        "prawo",
        "höger",
        "направо",
    ],
    "🏳️": ["flag", "white", "surrender", "peace", "bandeira", "σημαία", "lippu", "flaga", "flagga", "флаг"],
    "🏴‍☠️": ["pirate", "flag", "skull", "jolly", "roger", "pirata", "πειρατής", "пират"],
    "🏳️‍🌈": ["pride", "rainbow", "lgbt", "lgbtq", "flag", "orgulho", "arco"],
    "🇵🇹": ["portugal", "pt", "portuguese", "lisbon", "porto", "tuga"],
    "🇬🇷": ["greece", "gr", "greek", "athens", "hellas", "ελλάδα", "ελληνικά"],
    "🇬🇧": ["uk", "britain", "british", "england", "united", "kingdom", "gb", "london"],
    "🇺🇸": ["usa", "us", "america", "american", "united", "states"],
}

_INDEX: dict[str, Any] | None = None


def _strip_marks(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _norm_text(text: str) -> str:
    s = _WIKT_TAG_RE.sub("", text or "").lower()
    s = s.replace(":", " ").replace("_", " ").replace("-", " ").replace("/", " ")
    s = _strip_marks(s)
    s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    return re.sub(r"\s+", " ", s).strip()


def _split_tokens(text: str) -> list[str]:
    normed = _norm_text(text)
    if not normed:
        return []
    return [tok for tok in normed.split() if len(tok) >= 2 or any(ord(c) > 127 for c in tok)]


def _iso_code_for_flag(em_char: str) -> str | None:
    cps = [ord(ch) for ch in em_char]
    if len(cps) == 2 and all(0x1F1E6 <= cp <= 0x1F1FF for cp in cps):
        return "".join(chr(ord("a") + (cp - 0x1F1E6)) for cp in cps)
    return None


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_index() -> dict[str, Any]:
    """Build a multi-language, synonym-rich, typo-searchable in-memory emoji index."""
    emoji.config.load_language()
    emojilib = _load_json_dict(_KEYWORDS_PATH)
    wiktionary = _load_json_dict(_WIKTIONARY_PATH)

    # Precompute Wiktionary word -> (aliases, translation_tokens) for quick single-word expansion
    wikt_tokens_by_word: dict[str, list[str]] = {}
    for word_key, payload in wiktionary.items():
        if " " in word_key or not isinstance(payload, dict):
            continue
        extra: list[str] = []
        for alias in payload.get("aliases") or []:
            extra.extend(_split_tokens(str(alias)))
        tr_map = payload.get("translations") or {}
        if isinstance(tr_map, dict):
            for lang_terms in tr_map.values():
                if isinstance(lang_terms, list):
                    for term in lang_terms[:3]:
                        extra.extend(_split_tokens(str(term)))
        if extra:
            wikt_tokens_by_word[word_key.strip().lower()] = list(dict.fromkeys(extra))[:40]

    entries: list[dict[str, Any]] = []
    # token -> {entry_idx: max_weight}
    token_buckets: dict[str, dict[int, int]] = {}

    def _add_token(idx: int, tok: str, weight: int) -> None:
        if not tok:
            return
        bucket = token_buckets.setdefault(tok, {})
        prev = bucket.get(idx, 0)
        if weight > prev:
            bucket[idx] = weight

    for em_char, meta in emoji.EMOJI_DATA.items():
        if meta.get("status") != 2:
            continue
        if any(tone in em_char for tone in _SKIN_TONES):
            continue

        en_raw = meta.get("en", "")
        if not en_raw:
            continue
        en_name = en_raw.replace(":", "").replace("_", " ").strip().lower()
        norm_name = _norm_text(en_name)
        if not norm_name:
            continue

        entry_idx = len(entries)
        primary_phrases: set[str] = {norm_name}
        keyword_phrases: set[str] = set()

        # 1. Primary English name tokens & aliases (weight 3)
        en_tokens = _split_tokens(en_name)
        for tok in en_tokens:
            _add_token(entry_idx, tok, 3)

        for alias in meta.get("alias") or []:
            norm_alias = _norm_text(str(alias))
            if norm_alias:
                primary_phrases.add(norm_alias)
            for tok in _split_tokens(norm_alias):
                _add_token(entry_idx, tok, 3)

        # 2. All 14 built-in CLDR languages in `emoji` package (weight 3)
        for lang_code in emoji.LANGUAGES:
            if lang_code == "en":
                continue
            loc_val = meta.get(lang_code)
            if not loc_val:
                continue
            norm_loc = _norm_text(str(loc_val))
            if norm_loc:
                primary_phrases.add(norm_loc)
            for tok in _split_tokens(norm_loc):
                _add_token(entry_idx, tok, 3)

        # 3. Curated concept boosts + regional indicator flags (weight 3)
        boost_terms = CONCEPT_BOOST_KEYWORDS.get(em_char) or CONCEPT_BOOST_KEYWORDS.get(em_char.replace("\ufe0f", ""))
        if boost_terms:
            for term in boost_terms:
                norm_term = _norm_text(term)
                if norm_term:
                    keyword_phrases.add(norm_term)
                for tok in _split_tokens(term):
                    _add_token(entry_idx, tok, 3)

        iso_code = _iso_code_for_flag(em_char)
        if iso_code:
            primary_phrases.add(iso_code)
            _add_token(entry_idx, iso_code, 3)
            for fl in _FLAG_LABELS:
                norm_fl = _norm_text(fl)
                if norm_fl:
                    _add_token(entry_idx, norm_fl, 2)

        # 4. muan/emojilib English keyword synonyms (weight 2)
        lib_terms = emojilib.get(em_char) or emojilib.get(em_char.replace("\ufe0f", "")) or []
        for term in lib_terms:
            norm_term = _norm_text(str(term))
            if norm_term:
                keyword_phrases.add(norm_term)
            for tok in _split_tokens(norm_term):
                _add_token(entry_idx, tok, 2)

        # 5. Wiktionary 64-language expansion for primary English headword(s) (weight 1)
        head_candidates = [norm_name] + [t for t in en_tokens[:2] if len(t) >= 3]
        for head in head_candidates:
            for wtok in wikt_tokens_by_word.get(head, []):
                _add_token(entry_idx, wtok, 1)

        entries.append(
            {
                "emoji": em_char,
                "name": en_name,
                "norm_name": norm_name,
                "primary_phrases": primary_phrases,
                "keyword_phrases": keyword_phrases,
                "version": float(meta.get("E", 99.0)),
            }
        )

    token_index: dict[str, list[tuple[int, int]]] = {tok: list(bucket.items()) for tok, bucket in token_buckets.items()}
    return {
        "entries": entries,
        "token_index": token_index,
        "all_tokens": list(token_index.keys()),
    }


def get_search_index() -> dict[str, Any]:
    """Return the cached emoji search index, building it lazily once."""
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def _fuzzy_match_tokens(qt: str, all_tokens: list[str]) -> list[tuple[str, float]]:
    """Find close misspellings for an ASCII/Latin or Unicode token."""
    if len(qt) < 3:
        return []
    q_len = len(qt)
    q_first, q_last = qt[0], qt[-1]
    q_bi1, q_bi2 = qt[:2], qt[-2:]
    q_sorted = sorted(qt)
    matches: list[tuple[str, float]] = []
    for tok in all_tokens:
        t_len = len(tok)
        if t_len < 3 or abs(t_len - q_len) > 2:
            continue
        if tok[0] != q_first and tok[-1] != q_last and q_bi1 not in tok and q_bi2 not in tok:
            continue
        ratio = difflib.SequenceMatcher(None, qt, tok).ratio()
        if ratio >= 0.74:
            bonus = 0.0
            if tok[0] == q_first:
                bonus += 0.08
            if t_len == q_len and sorted(tok) == q_sorted:
                bonus += 0.14
            matches.append((tok, min(1.0, ratio + bonus)))
    matches.sort(key=lambda x: -x[1])
    return matches[:20]


def _add_best_score(bucket: dict[int, float], entry_idx: int, score: float) -> None:
    if score > bucket.get(entry_idx, 0.0):
        bucket[entry_idx] = score


def search_emojis(raw_query: str, limit: int = 50) -> list[dict[str, str]]:
    """Search emojis by exact name, synonyms, 64+ languages, country codes, or misspellings."""
    raw = (raw_query or "").strip()
    if not raw:
        return []
    q_norm = _norm_text(raw)
    has_non_ascii = any(ord(c) > 127 for c in q_norm)
    if not q_norm or (len(q_norm) < 2 and not has_non_ascii):
        return []

    idx_data = get_search_index()
    entries = idx_data["entries"]
    token_index = idx_data["token_index"]
    all_tokens = idx_data["all_tokens"]

    scores: dict[int, float] = {}
    q_tokens = _split_tokens(q_norm) or [q_norm]

    # Exact phrase bonuses
    for i, entry in enumerate(entries):
        if entry["norm_name"] == q_norm:
            scores[i] = scores.get(i, 0.0) + 180.0
        elif q_norm in entry["primary_phrases"]:
            scores[i] = scores.get(i, 0.0) + 120.0
        elif q_norm in entry["keyword_phrases"]:
            scores[i] = scores.get(i, 0.0) + 95.0

    # Token exact + prefix + substring + misspelling scoring (capped per query token to avoid 14-lang inflation)
    for qt in q_tokens:
        qt_best: dict[int, float] = {}
        exact_hits = token_index.get(qt)
        if exact_hits:
            for e_idx, weight in exact_hits:
                _add_best_score(qt_best, e_idx, 40.0 * weight)

        qt_len = len(qt)
        if qt_len >= 2:
            for tok in all_tokens:
                if tok == qt:
                    continue
                if tok.startswith(qt):
                    for e_idx, weight in token_index[tok]:
                        _add_best_score(qt_best, e_idx, 18.0 * weight)
                elif qt_len >= 3 and qt in tok:
                    for e_idx, weight in token_index[tok]:
                        _add_best_score(qt_best, e_idx, 11.0 * weight)

        # Trigger fuzzy misspelling matching when exact matches are sparse or zero
        if qt_len >= 3 and (not exact_hits or len(qt_best) < 5):
            for tok, ratio in _fuzzy_match_tokens(qt, all_tokens):
                for e_idx, weight in token_index[tok]:
                    _add_best_score(qt_best, e_idx, 26.0 * ratio * weight)

        for e_idx, val in qt_best.items():
            scores[e_idx] = scores.get(e_idx, 0.0) + val

    ranked = sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            len(entries[item[0]]["name"]),
            entries[item[0]]["version"],
            entries[item[0]]["name"],
        ),
    )
    return [{"emoji": entries[i]["emoji"], "name": entries[i]["name"]} for i, _ in ranked[:limit]]


def emoji_search(request):
    """Search emojis by name, synonym, typo, or language. Returns JSON list of {emoji, name}."""
    q = request.GET.get("q", "")
    results = search_emojis(q, limit=50)
    return JsonResponse(results, safe=False)

"""Language capability registry for game rooms (game content localization vs UI-only)."""

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils.translation import gettext as _

_LEXICON_PATH = Path(__file__).resolve().parent.parent / "emojinary" / "data" / "wiktionary_lexicon.json"

_LANG_ALIAS_TO_LEXICON = {
    "he": "iw",
    "nb": "no",
    "fil": "tl",
    "zh-hans": "zh-cn",
    "zh-hant": "zh-tw",
}

# Lupus has handcrafted multi-paragraph role descriptions & phase cards in these locales,
# plus broader interface translations across site locales.
LUPUS_CONTENT_LANGUAGES = frozenset({"en", "pt", "it", "es", "fr", "el", "ru", "hi", "kn"})

GAME_TYPES = (
    ("emojinary", "🎨 Emojinary"),
    ("impostor", "🕵️ Word Impostor (Poison Word)"),
    ("codenames", "🧩 Codenames"),
)


@lru_cache(maxsize=1)
def _load_lexicon_counts() -> tuple[int, dict[str, int]]:
    """Return total lexicon entries and per-language translation counts."""
    if not _LEXICON_PATH.exists():
        return 0, {"en": 0}
    try:
        with open(_LEXICON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0, {"en": 0}

    counts: Counter[str] = Counter()
    total = len(data)
    counts["en"] = total
    for entry in data.values():
        translations = entry.get("translations") or {}
        if isinstance(translations, dict):
            for lang_code, vals in translations.items():
                if vals:
                    counts[lang_code.lower()] += 1
    return total, dict(counts)


def normalize_language_code(lang_code: str | None) -> str:
    """Normalize a Django language code against settings.LANGUAGES."""
    if not lang_code:
        return "en"
    raw = str(lang_code).strip().lower().replace("_", "-")
    valid_codes = {code.lower(): code for code, _ in getattr(settings, "LANGUAGES", [("en", "English")])}
    if raw in valid_codes:
        return valid_codes[raw]
    # Map common aliases (he -> iw, nb -> no, fil -> tl)
    aliased = _LANG_ALIAS_TO_LEXICON.get(raw)
    if aliased and aliased in valid_codes:
        return valid_codes[aliased]
    base = raw.split("-")[0]
    if base in valid_codes:
        return valid_codes[base]
    return "en"


def get_lexicon_language_key(lang_code: str | None) -> str:
    """Map a room language code to the corresponding key inside wiktionary_lexicon.json."""
    norm = normalize_language_code(lang_code)
    return _LANG_ALIAS_TO_LEXICON.get(norm, norm)


def get_language_display(lang_code: str | None) -> str:
    """Return human-readable flag + language label from settings.LANGUAGES."""
    norm = normalize_language_code(lang_code)
    for code, label in getattr(settings, "LANGUAGES", [("en", "English")]):
        if code.lower() == norm.lower():
            return label
    return norm.upper()


def get_game_language_support(game_type: str, lang_code: str | None) -> dict[str, Any]:
    """Classify whether (game_type, lang_code) supports full localized game content or UI-only."""
    norm = normalize_language_code(lang_code)
    lex_key = get_lexicon_language_key(norm)
    game = (game_type or "emojinary").strip().lower()
    valid_ui_langs = {code.lower() for code, _ in getattr(settings, "LANGUAGES", [("en", "English")])}
    ui_supported = norm.lower() in valid_ui_langs

    total_entries, counts = _load_lexicon_counts()
    entry_count = total_entries if norm == "en" else counts.get(lex_key, 0)

    if game == "lupus":
        content_supported = norm in LUPUS_CONTENT_LANGUAGES
    elif game in ("emojinary", "impostor", "codenames"):
        # Full content if English OR substantial Wiktionary translations exist (>= 100 entries)
        content_supported = norm == "en" or entry_count >= 100
    else:
        content_supported = norm == "en"

    mode = "full_content" if content_supported else "ui_only"
    if content_supported:
        badge_label = _("✅ Full Content + UI")
        detail = (
            _("Game words, clues, and interface are supported in %(lang)s.") % {"lang": get_language_display(norm)}
            if game in ("emojinary", "impostor", "codenames")
            else _("Roles, phases, and interface are localized in %(lang)s.") % {"lang": get_language_display(norm)}
        )
    else:
        badge_label = _("🌐 UI Only (English Words)")
        detail = _(
            "The interface uses %(lang)s, while game content falls back to English because full vocabulary data is unavailable."
        ) % {"lang": get_language_display(norm)}

    return {
        "game_type": game,
        "language": norm,
        "language_display": get_language_display(norm),
        "lexicon_key": lex_key,
        "content_supported": content_supported,
        "ui_supported": ui_supported,
        "mode": mode,
        "badge_label": badge_label,
        "detail": detail,
        "entry_count": entry_count,
    }


def get_language_support_matrix() -> dict[str, dict[str, dict[str, Any]]]:
    """Return full capability map keyed by game_type -> lang_code for client-side room creation hints."""
    langs = [code for code, _ in getattr(settings, "LANGUAGES", [("en", "English")])]
    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for gtype in ("emojinary", "impostor", "codenames", "lupus"):
        matrix[gtype] = {}
        for code in langs:
            info = get_game_language_support(gtype, code)
            matrix[gtype][code] = {
                "content_supported": info["content_supported"],
                "mode": info["mode"],
                "badge_label": info["badge_label"],
                "detail": info["detail"],
                "entry_count": info["entry_count"],
            }
    return matrix

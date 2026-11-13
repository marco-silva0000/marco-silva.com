import json
import random
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.html import escape
from wonderwords import RandomSentence, RandomWord

rw = RandomWord()
rs = RandomSentence()

_WORDLIST_CACHE: dict | None = None
_LEXICON_CACHE: dict | None = None


def _load_wordlists() -> dict:
    global _WORDLIST_CACHE
    if _WORDLIST_CACHE is None:
        path = Path(settings.BASE_DIR) / "emojinary" / "data" / "wordlists.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _WORDLIST_CACHE = json.load(f).get("pictionary", {})
        else:
            _WORDLIST_CACHE = {}
    return _WORDLIST_CACHE


def _load_lexicon() -> dict:
    global _LEXICON_CACHE
    if _LEXICON_CACHE is None:
        path = Path(settings.BASE_DIR) / "emojinary" / "data" / "wiktionary_lexicon.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _LEXICON_CACHE = json.load(f)
        else:
            _LEXICON_CACHE = {}
    return _LEXICON_CACHE


HARD_WORDS = [
    "democracy",
    "nostalgia",
    "sarcasm",
    "evolution",
    "gravity",
    "photosynthesis",
    "procrastination",
    "claustrophobia",
    "déjà vu",
    "paradox",
    "entropy",
    "karma",
    "inception",
    "metamorphosis",
    "serendipity",
    "zeitgeist",
    "epiphany",
    "allegory",
    "cognitive dissonance",
    "existentialism",
    "bureaucracy",
    "philosophy",
    "ambiguity",
    "irony",
    "hypocrisy",
    "superstition",
    "conspiracy",
    "imagination",
    "perspective",
]

CATEGORY_MAP = {
    "noun": ["noun"],
    "verb": ["verb"],
    "adjective": ["adjective"],
    "any": ["noun", "adjective", "verb"],
}


def pictionary(request):
    return render(request, "tools/pictionary.html")


def pictionary_word(request):
    difficulty = request.GET.get("d", "medium")
    category = request.GET.get("cat", "noun")
    mode = request.GET.get("mode", "word")

    pools = _load_wordlists()
    word = None

    if mode == "sentence":
        sentences = pools.get("sentence") or []
        word = random.choice(sentences) if sentences and random.random() < 0.7 else rs.sentence()
    else:
        pos = random.choice(["noun", "verb", "adjective"]) if category == "any" else category
        if pos not in ("noun", "verb", "adjective"):
            pos = "noun"
        diff_pool = pools.get(pos, {}).get(difficulty, [])
        if diff_pool:
            word = random.choice(diff_pool)

    if not word:
        if difficulty == "hard":
            cats = CATEGORY_MAP.get(category, ["noun"])
            try:
                word = rw.word(include_categories=cats, word_min_length=8, word_max_length=20)
            except Exception:
                word = random.choice(HARD_WORDS)
        else:
            cats = CATEGORY_MAP.get(category, ["noun"])
            if difficulty == "easy":
                word = rw.word(include_categories=cats, word_min_length=3, word_max_length=6)
            else:
                word = rw.word(include_categories=cats, word_min_length=5, word_max_length=12)

    if request.headers.get("HX-Request"):
        lex = _load_lexicon().get(word.lower(), {})
        lang = (getattr(request, "LANGUAGE_CODE", "en") or "en").lower()
        tr_list = lex.get("translations", {}).get(lang, []) if lang != "en" else []
        title_html = escape(word)
        if tr_list:
            title_html = (
                f'{escape(tr_list[0])} <span style="font-size:1rem;color:#666;font-weight:400;">({escape(word)})</span>'
            )
        def_html = ""
        if lex.get("definition"):
            def_html = (
                f'<div style="font-size:0.85rem;color:#666;margin-top:0.25rem;">📖 {escape(lex["definition"])}</div>'
            )
        return HttpResponse(f'<span style="font-size: 1.5rem; font-weight: 600;">{title_html}</span>{def_html}')
    return HttpResponse(word)

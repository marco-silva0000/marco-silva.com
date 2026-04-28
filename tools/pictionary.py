import random

from django.http import HttpResponse
from django.shortcuts import render
from wonderwords import RandomSentence, RandomWord

rw = RandomWord()
rs = RandomSentence()

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

    if mode == "sentence":
        word = rs.sentence()
    elif difficulty == "hard":
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
        return HttpResponse(f'<span style="font-size: 1.5rem; font-weight: 600;">{word}</span>')
    return HttpResponse(word)

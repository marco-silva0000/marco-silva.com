import random

from django.http import HttpResponse
from django.shortcuts import render
from wonderwords import RandomWord

rw = RandomWord()

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


def pictionary(request):
    return render(request, "tools/pictionary.html")


def pictionary_word(request):
    difficulty = request.GET.get("d", "medium")

    if difficulty == "easy":
        word = rw.word(include_categories=["noun"], word_min_length=3, word_max_length=6)
    elif difficulty == "hard":
        word = random.choice(HARD_WORDS)
    else:
        word = rw.word(include_categories=["noun", "adjective"], word_min_length=5, word_max_length=12)

    if request.headers.get("HX-Request"):
        return HttpResponse(f'<span style="font-size: 1.5rem; font-weight: 600;">{word}</span>')
    return HttpResponse(word)

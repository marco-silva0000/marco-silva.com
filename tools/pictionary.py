import json
import random

from django.http import HttpResponse
from django.shortcuts import render

WORDS = {
    "easy": [
        "cat",
        "dog",
        "house",
        "tree",
        "sun",
        "moon",
        "car",
        "fish",
        "bird",
        "flower",
        "book",
        "chair",
        "phone",
        "hat",
        "shoe",
        "ball",
        "clock",
        "door",
        "key",
        "star",
        "rain",
        "snow",
        "fire",
        "boat",
        "train",
        "apple",
        "banana",
        "pizza",
        "cake",
        "egg",
        "baby",
        "smile",
        "heart",
        "cloud",
        "bridge",
        "guitar",
        "drum",
        "candle",
        "ladder",
        "robot",
    ],
    "medium": [
        "astronaut",
        "volcano",
        "dinosaur",
        "pirate",
        "mermaid",
        "tornado",
        "lighthouse",
        "parachute",
        "telescope",
        "submarine",
        "skateboard",
        "trampoline",
        "waterfall",
        "campfire",
        "snowflake",
        "treasure",
        "compass",
        "hammock",
        "igloo",
        "scarecrow",
        "windmill",
        "quicksand",
        "avalanche",
        "fireworks",
        "jigsaw",
        "labyrinth",
        "origami",
        "slingshot",
        "tightrope",
        "whirlpool",
    ],
    "hard": [
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
    ],
}


def pictionary(request):
    return render(request, "tools/pictionary.html")


def pictionary_word(request):
    difficulty = request.GET.get("d", "medium")
    word_list = WORDS.get(difficulty, WORDS["medium"])
    word = random.choice(word_list)
    if request.headers.get("HX-Request"):
        return HttpResponse(f'<span style="font-size: 1.5rem; font-weight: 600;">{word}</span>')
    return HttpResponse(json.dumps({"word": word, "difficulty": difficulty}), content_type="application/json")

from django.urls import path

from .pictionary import pictionary, pictionary_word

urlpatterns = [
    path("", pictionary, name="pictionary"),
    path("word/", pictionary_word, name="pictionary-word"),
]

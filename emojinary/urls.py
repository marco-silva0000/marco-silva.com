from django.urls import path

from . import views
from .emoji_search import emoji_search

app_name = "emojinary"

urlpatterns = [
    path("", views.emojinary_index, name="index"),
    path("emoji-search/", emoji_search, name="emoji-search"),
    path("<str:code>/<str:name>/", views.game, name="game"),
]

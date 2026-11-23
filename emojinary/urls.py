from django.urls import path

from . import views
from .emoji_search import emoji_search

app_name = "emojinary"

urlpatterns = [
    path("", views.emojinary_index, name="index"),
    path("emoji-search/", emoji_search, name="emoji-search"),
    path("<str:code>/play/", views.game_play, name="play"),
    path("<str:code>/play/", views.game_play, name="game-play"),
    path("<str:code>/replay.json", views.export_replay, name="replay"),
    path("<str:code>/reconnect/<str:token>/", views.player_reconnect, name="reconnect"),
    path("<str:code>/qr/<str:token>/", views.player_qr, name="player-qr"),
    path("<str:code>/<str:name>/", views.game_with_name_redirect, name="game"),
    path("<str:code>/", views.game_play, name="join"),
    path("<str:code>/", views.game_play, name="room-root"),
]

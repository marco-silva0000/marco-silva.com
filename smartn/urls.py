from django.urls import path

from . import views

app_name = "smartn"

urlpatterns = [
    path("<str:code>/play/", views.game_play, name="play"),
    path("<str:code>/play/", views.game_play, name="game-play"),
    path("<str:code>/qr/<str:token>/", views.player_qr, name="player-qr"),
    path("<str:code>/reconnect/<str:token>/", views.player_reconnect, name="reconnect"),
    path("<str:code>/<str:name>/", views.game_with_name_redirect, name="game"),
    path("<str:code>/", views.game_play, name="room-root"),
]

from django.urls import path

from . import views

app_name = "dontsay"

urlpatterns = [
    path("<str:code>/reconnect/<str:token>/", views.reconnect, name="reconnect"),
    path("<str:code>/qr/<str:token>/", views.player_qr, name="player-qr"),
    path("<str:code>/api/state/", views.api_game_state, name="api-state"),
    path("<str:code>/<str:name>/", views.game, name="game"),
    path("<str:code>/", views.room_join_redirect, name="join-redirect"),
]

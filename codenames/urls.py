from django.urls import path

from . import views

app_name = "codenames"

urlpatterns = [
    path("<str:code>/qr/<str:token>/", views.player_qr, name="player-qr"),
    path("<str:code>/replay.json", views.export_replay, name="replay"),
    path("<str:code>/reconnect/<str:token>/", views.player_reconnect, name="reconnect"),
    path("<str:code>/<str:name>/", views.game, name="game"),
    path("<str:code>/", views.room_join_redirect, name="join"),
]

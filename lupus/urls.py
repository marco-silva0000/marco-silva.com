"""URL patterns for Lupus game."""

from django.urls import path

from . import views

app_name = "lupus"

urlpatterns = [
    path("", views.lupus_hub, name="hub"),
    path("", views.lupus_hub, name="index"),
    path("create/", views.create_room, name="create"),
    path("<str:code>/gm/", views.gm_dashboard, name="gm"),
    path("<str:code>/export-replay/", views.export_replay, name="export-replay"),
    path("<str:code>/join/", views.room_join, name="join"),
    path("<str:code>/play/", views.player_view, name="play"),
    path("<str:code>/reconnect/<str:token>/", views.player_reconnect, name="reconnect"),
    path("<str:code>/qr/<str:token>/", views.player_qr, name="player-qr"),
    path("<str:code>/", views.room_join, name="room-root"),
]

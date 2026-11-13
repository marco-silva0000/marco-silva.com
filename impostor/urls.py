from django.urls import path

from . import views

app_name = "impostor"

urlpatterns = [
    path("<str:code>/reconnect/<str:token>/", views.player_reconnect, name="reconnect"),
    path("<str:code>/<str:name>/", views.game, name="game"),
    path("<str:code>/", views.room_join_redirect, name="join-redirect"),
]

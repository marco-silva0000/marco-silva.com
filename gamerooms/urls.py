from django.urls import path

from . import views

app_name = "gamerooms"

urlpatterns = [
    path("", views.room_list, name="room-list"),
    path("create/", views.room_create, name="room-create"),
    path("<str:code>/", views.room_join, name="room-join"),
]

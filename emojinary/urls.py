from django.urls import path

from . import views

app_name = "emojinary"

urlpatterns = [
    path("", views.emojinary_index, name="index"),
    path("<str:code>/<str:name>/", views.game, name="game"),
]

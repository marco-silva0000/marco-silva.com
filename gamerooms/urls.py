from django.urls import include, path

from . import views

app_name = "gamerooms"

urlpatterns = [
    path("", views.room_list, name="room-list"),
    path("create/", views.room_create, name="room-create"),
    path("emojinary/", include(("emojinary.urls", "emojinary"))),
    path("impostor/", include(("impostor.urls", "impostor"))),
    path("codenames/", include(("codenames.urls", "codenames"))),
    path("stop/", include(("stop.urls", "stop"))),
    path("dontsay/", include(("dontsay.urls", "dontsay"))),
    path("rankit/", include(("rankit.urls", "rankit"))),
    path("smartn/", include(("smartn.urls", "smartn"))),
    path("secretsanta/", include(("secretsanta.urls", "secretsanta"))),
    path("lupus/", include(("lupus.urls", "lupus"))),
    path("pictionary/", include("tools.pictionary_urls")),
    path("prompts/suggest/", views.suggest_prompt, name="suggest-prompt"),
    path("<str:code>/", views.room_join, name="room-join"),
]

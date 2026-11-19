from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/rankit/<str:code>/", consumers.RankitConsumer.as_asgi()),
    path("ws/games/rankit/<str:code>/", consumers.RankitConsumer.as_asgi()),
]

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/secretsanta/<str:code>/", consumers.SecretSantaConsumer.as_asgi()),
    path("ws/games/secretsanta/<str:code>/", consumers.SecretSantaConsumer.as_asgi()),
]

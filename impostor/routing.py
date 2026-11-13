from django.urls import path

from .consumers import ImpostorConsumer

websocket_urlpatterns = [
    path("ws/impostor/<str:code>/", ImpostorConsumer.as_asgi()),
]

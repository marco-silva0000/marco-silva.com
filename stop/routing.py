from django.urls import path

from .consumers import StopConsumer

websocket_urlpatterns = [
    path("ws/stop/<str:code>/", StopConsumer.as_asgi()),
]

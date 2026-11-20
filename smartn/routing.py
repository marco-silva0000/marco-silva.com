from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/smartn/<str:code>/", consumers.SmartNConsumer.as_asgi()),
    path("ws/games/smartn/<str:code>/", consumers.SmartNConsumer.as_asgi()),
]

"""WebSocket URL routing for the Lupus game."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/lupus/(?P<code>\w+)/$", consumers.LupusConsumer.as_asgi()),
]

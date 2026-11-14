from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/codenames/(?P<code>[^/]+)/$", consumers.CodenamesConsumer.as_asgi()),
]

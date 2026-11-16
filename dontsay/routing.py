from django.urls import path

from .consumers import DontSayConsumer

websocket_urlpatterns = [
    path("ws/dontsay/<str:code>/", DontSayConsumer.as_asgi()),
]

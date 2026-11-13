import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django_asgi_app = get_asgi_application()

from emojinary.routing import websocket_urlpatterns as emojinary_ws_urlpatterns  # noqa: E402
from impostor.routing import websocket_urlpatterns as impostor_ws_urlpatterns  # noqa: E402
from lupus.routing import websocket_urlpatterns as lupus_ws_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(emojinary_ws_urlpatterns + impostor_ws_urlpatterns + lupus_ws_urlpatterns),
    }
)

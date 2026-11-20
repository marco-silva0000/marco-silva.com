import os
from urllib.parse import urlparse

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.core.asgi import get_asgi_application
from django.http.request import validate_host

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django_asgi_app = get_asgi_application()

from codenames.routing import websocket_urlpatterns as codenames_ws_urlpatterns  # noqa: E402
from dontsay.routing import websocket_urlpatterns as dontsay_ws_urlpatterns  # noqa: E402
from emojinary.routing import websocket_urlpatterns as emojinary_ws_urlpatterns  # noqa: E402
from impostor.routing import websocket_urlpatterns as impostor_ws_urlpatterns  # noqa: E402
from lupus.routing import websocket_urlpatterns as lupus_ws_urlpatterns  # noqa: E402
from rankit.routing import websocket_urlpatterns as rankit_ws_urlpatterns  # noqa: E402
from smartn.routing import websocket_urlpatterns as smartn_ws_urlpatterns  # noqa: E402
from stop.routing import websocket_urlpatterns as stop_ws_urlpatterns  # noqa: E402


class WebSocketOriginValidator:
    """
    Validate the WebSocket Origin header against ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS
    when an Origin header is supplied by the client (browsers always send Origin on
    WebSocket handshakes), while still allowing in-process WebsocketCommunicator tests
    that omit the Origin header.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "websocket":
            headers = dict(scope.get("headers") or [])
            raw_origin = headers.get(b"origin")
            if raw_origin is not None:
                origin_str = raw_origin.decode("latin1", errors="ignore").strip()
                parsed = urlparse(origin_str)
                origin_host = parsed.hostname or ""
                allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
                if settings.DEBUG and not allowed_hosts:
                    allowed_hosts = ["*"]
                trusted_origins = [
                    urlparse(o).hostname for o in (getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or []) if o
                ]
                all_allowed = allowed_hosts + [h for h in trusted_origins if h]
                if not origin_host or not validate_host(origin_host, all_allowed):
                    await send({"type": "websocket.close", "code": 4403})
                    return
        return await self.app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": WebSocketOriginValidator(
            URLRouter(
                emojinary_ws_urlpatterns
                + impostor_ws_urlpatterns
                + codenames_ws_urlpatterns
                + stop_ws_urlpatterns
                + dontsay_ws_urlpatterns
                + rankit_ws_urlpatterns
                + smartn_ws_urlpatterns
                + lupus_ws_urlpatterns
            )
        ),
    }
)

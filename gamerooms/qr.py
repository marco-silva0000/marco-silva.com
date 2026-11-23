"""Shared QR code generation helpers for room join and private player reconnect across party games."""

import base64
import io
import urllib.parse


def generate_qr_data_uri(content: str) -> str:
    """Generate a data URI (PNG base64) representation of a QR code with API fallback."""
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"
    except Exception:
        encoded = urllib.parse.quote(content)
        return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded}"


def build_public_url(request, path: str, query_params: dict | None = None) -> str:
    """Build a canonical absolute URL (forcing HTTPS on public domains/proxies)."""
    host = request.get_host()
    is_public = any(d in host for d in ["marco-silva.com", "dev.marco-silva.com"])
    scheme = (
        "https"
        if (is_public or request.is_secure() or request.headers.get("x-forwarded-proto") == "https")
        else request.scheme
    )
    query_str = f"?{urllib.parse.urlencode(query_params)}" if query_params else ""
    return f"{scheme}://{host}{path}{query_str}"


def get_room_share_urls(request, room, game_type: str, player_token: str | None = None) -> dict:
    """Build shared join and reconnect URLs and QR code URIs for game views."""
    from django.urls import reverse

    join_path = reverse("gamerooms:room-join", kwargs={"code": room.code})
    join_params = {"pwd": room.password} if room.has_password and room.password else None
    join_url = build_public_url(request, join_path, join_params)
    join_qr = generate_qr_data_uri(join_url)

    reconnect_url = ""
    reconnect_qr = ""
    if player_token:
        try:
            reconnect_path = reverse(
                f"gamerooms:{game_type}:reconnect",
                kwargs={"code": room.code, "token": player_token},
            )
            reconnect_url = build_public_url(request, reconnect_path)
            reconnect_qr = generate_qr_data_uri(reconnect_url)
        except Exception:
            pass

    return {
        "join_url": join_url,
        "join_qr": join_qr,
        "reconnect_url": reconnect_url,
        "reconnect_qr": reconnect_qr,
        "player_qr": reconnect_qr,
    }

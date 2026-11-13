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

"""QR code generation helpers for room join and private player reconnect."""

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

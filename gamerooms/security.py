"""
Security utilities for safe JSON script embedding, rate limiting, and header/ICS sanitization.
"""

import json
import re
from typing import Any

from django.core.cache import cache
from django.http import HttpRequest

_JSON_SCRIPT_ESCAPES = {
    ord(">"): "\\u003e",
    ord("<"): "\\u003c",
    ord("&"): "\\u0026",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


def safe_json_dumps(data: Any) -> str:
    """
    Serialize data to JSON with HTML-sensitive characters (<, >, &, U+2028, U+2029)
    escaped as Unicode sequences so it can be safely embedded inside <script> blocks
    without allowing </script> breakout XSS.
    """
    return json.dumps(data).translate(_JSON_SCRIPT_ESCAPES)


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP address from request META."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1") or "127.0.0.1"


def is_rate_limited(request: HttpRequest, scope: str, limit: int = 20, window_seconds: int = 60) -> bool:
    """
    Increment and check a per-IP rate limit counter in Django's cache.
    Returns True if the caller has exceeded `limit` requests within `window_seconds`.
    """
    ip = get_client_ip(request)
    key = f"rl:{scope}:{ip}"
    try:
        current = cache.get(key, 0)
        if current >= limit:
            return True
        cache.set(key, current + 1, timeout=window_seconds)
    except Exception:
        return False
    return False


def sanitize_ics_field(value: Any, default: str = "") -> str:
    """
    Strip CR/LF, C0/C1 control characters, and Unicode line separators from
    iCalendar single-line property values to prevent property / header injection.
    """
    if value is None:
        return default
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+", " ", str(value)).strip()
    return cleaned if cleaned else default


def sanitize_header_filename(value: Any, default: str = "Event") -> str:
    """
    Sanitize a filename used in Content-Disposition headers by keeping only safe
    printable ASCII characters (avoiding CR/LF, quotes, control chars, and MIME
    multi-line header folding).
    """
    if value is None:
        return default
    cleaned = re.sub(r"[^A-Za-z0-9 _.()-]+", "", str(value)).strip()
    return cleaned[:80] if cleaned else default

"""
Security & Property-Based Fuzzing Test Suite (Hypothesis)
---------------------------------------------------------
Fuzzes JSON script serialization (<script> breakout XSS prevention),
iCalendar / Content-Disposition CRLF injection protection, WebSocket Origin
validation (CSWSH prevention), rate limiting, and game room view rendering.
"""

import json

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.urls import reverse
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gamerooms.models import Room
from gamerooms.security import (
    is_rate_limited,
    safe_json_dumps,
    sanitize_header_filename,
    sanitize_ics_field,
)
from tools.ics_maker import ics_download
from tools.views import planz, planz_ics
from website.asgi import application

XSS_PAYLOADS = [
    "</script><script>alert(1)</script>",
    "'><img src=x onerror=alert(1)>",
    "\";alert('xss');//",
    "\u2028\u2029</script>",
    "a\r\nSUMMARY:INJECTED\r\nDESCRIPTION:evil",
]


class TestSafeJsonDumpsFuzz:
    @settings(max_examples=100)
    @given(
        payload=st.recursive(
            st.none() | st.booleans() | st.integers() | st.text(),
            lambda children: (
                st.lists(children, max_size=5) | st.dictionaries(st.text(max_size=20), children, max_size=5)
            ),
            max_leaves=15,
        )
    )
    def test_safe_json_dumps_never_emits_raw_html_chars_and_roundtrips(self, payload):
        encoded = safe_json_dumps(payload)
        assert "<" not in encoded
        assert ">" not in encoded
        assert "&" not in encoded
        assert "\u2028" not in encoded
        assert "\u2029" not in encoded
        assert json.loads(encoded) == payload

    @pytest.mark.parametrize("xss", XSS_PAYLOADS)
    def test_explicit_script_breakout_payloads_escaped(self, xss):
        encoded = safe_json_dumps({"player_name": xss, "nested": [xss]})
        assert "</script>" not in encoded.lower()
        assert "<script>" not in encoded.lower()
        assert json.loads(encoded)["player_name"] == xss


class TestIcsAndHeaderCrlfFuzz:
    @settings(max_examples=80, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        title=st.text(max_size=150),
        location=st.text(max_size=150),
        description=st.text(max_size=200),
        start=st.text(max_size=40),
        end=st.text(max_size=40),
    )
    def test_planz_ics_fuzz_never_injects_crlf_or_crashes(self, title, location, description, start, end):
        factory = RequestFactory()
        req = factory.get(
            "/tools/planz/event.ics",
            {"title": title, "location": location, "description": description, "start": start, "end": end},
        )
        resp = planz_ics(req)
        assert resp.status_code == 200
        disp = resp["Content-Disposition"]
        assert "\r" not in disp and "\n" not in disp
        body = resp.content.decode("utf-8")
        lines = body.split("\r\n")
        summary_lines = [line for line in lines if line.startswith("SUMMARY:")]
        assert len(summary_lines) == 1

    @settings(max_examples=80)
    @given(raw_body=st.binary(max_size=300) | st.text(max_size=300).map(lambda s: s.encode("utf-8", errors="ignore")))
    def test_ics_download_arbitrary_body_fuzz_never_500s(self, raw_body):
        factory = RequestFactory()
        req = factory.post("/tools/ics/download/", data=raw_body, content_type="application/json")
        resp = ics_download(req)
        assert resp.status_code in (200, 400)

    def test_sanitize_helpers_strip_crlf_and_quotes(self):
        assert "\r" not in sanitize_ics_field("Lunch\r\nATTENDEE:evil@example.com")
        assert "\n" not in sanitize_ics_field("Lunch\r\nATTENDEE:evil@example.com")
        fname = sanitize_header_filename('evil"\r\nX-Injected: 1')
        assert '"' not in fname and "\r" not in fname and "\n" not in fname


@pytest.mark.django_db
class TestPlanzGetParamAndRateLimit:
    def test_planz_get_param_works_immediately_for_shareable_links(self):
        cache.clear()
        factory = RequestFactory()
        req = factory.get("/tools/planz/", {"passwd": "planzzz"})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("tools.views._fetch_events", lambda: [])
            resp = planz(req)
        assert resp.status_code == 200

    def test_rate_limiter_blocks_after_threshold(self):
        cache.clear()
        factory = RequestFactory()
        req = factory.post("/tools/planz/auth/", REMOTE_ADDR="198.51.100.77")
        for _ in range(5):
            assert is_rate_limited(req, scope="test_rl", limit=5, window_seconds=60) is False
        assert is_rate_limited(req, scope="test_rl", limit=5, window_seconds=60) is True


@pytest.mark.django_db(transaction=True)
class TestWebSocketOriginValidationAndXssViews:
    def test_websocket_rejects_cross_origin_hijack_and_allows_trusted_origin(self):
        Room.objects.create(title="SecTest", code="SECWS01", game_type="codenames", language="en")

        async def _run():
            # 1. Untrusted cross-site origin must be rejected (CSWSH protection)
            evil_comm = WebsocketCommunicator(
                application,
                "/ws/codenames/SECWS01/",
                headers=[(b"origin", b"https://evil-attacker.example.com")],
            )
            connected, close_code = await evil_comm.connect()
            assert connected is False
            assert close_code == 4403

            # 2. Trusted origin (testserver / localhost) must succeed
            good_comm = WebsocketCommunicator(
                application,
                "/ws/codenames/SECWS01/",
                headers=[(b"origin", b"http://testserver")],
            )
            connected_good, _ = await good_comm.connect()
            assert connected_good is True
            await good_comm.disconnect()

        async_to_sync(_run)()

    @pytest.mark.parametrize("game_type", ["codenames", "stop", "dontsay", "impostor", "rankit", "emojinary"])
    def test_game_views_escape_script_breakout_in_room_title(self, game_type):
        code = f"X{game_type[:4].upper()}1"
        Room.objects.create(
            title="</script><script>alert('xss')</script>",
            code=code,
            game_type=game_type,
            language="en",
        )
        client = Client()
        url = reverse(f"gamerooms:{game_type}:game", kwargs={"code": code, "name": "Alice"})
        resp = client.get(url, follow=True)
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")
        assert "</script><script>alert('xss')</script>" not in html

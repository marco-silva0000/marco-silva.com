import json
from unittest.mock import patch

from django.test import RequestFactory

from tools.ai_extract import EventSchema, _fallback
from tools.ics_maker import _parse_dt, ics_download, ics_extract, ics_maker

MOCK_EVENT = {
    "title": "Team Standup",
    "start": "2026-05-20T10:00:00",
    "end": "2026-05-20T10:30:00",
    "location": "Office",
    "description": "Daily standup",
}


class TestIcsMakerPage:
    def test_returns_200(self, settings):
        settings.TEMPLATES[0]["OPTIONS"]["context_processors"] = [
            "django.template.context_processors.request",
        ]
        factory = RequestFactory()
        request = factory.get("/tools/ics/")
        resp = ics_maker(request)
        assert resp.status_code == 200
        assert "ics maker" in resp.content.decode()


class TestIcsExtract:
    @patch("tools.ai_extract.extract_event", return_value=MOCK_EVENT)
    def test_returns_event_json(self, mock_ai):
        factory = RequestFactory()
        request = factory.post("/tools/ics/extract/", {"text": "Meeting tomorrow at 6pm", "url": ""})
        resp = ics_extract(request)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["title"] == "Team Standup"
        mock_ai.assert_called_once()

    @patch("tools.ai_extract.extract_event", return_value=MOCK_EVENT)
    def test_with_url_only(self, mock_ai):
        factory = RequestFactory()
        request = factory.post("/tools/ics/extract/", {"text": "", "url": "https://example.com/event"})
        resp = ics_extract(request)
        assert resp.status_code == 200
        assert "title" in json.loads(resp.content)

    def test_empty_input_returns_400(self):
        factory = RequestFactory()
        request = factory.post("/tools/ics/extract/", {"text": "", "url": ""})
        resp = ics_extract(request)
        assert resp.status_code == 400
        assert "error" in json.loads(resp.content)

    def test_rejects_get(self):
        factory = RequestFactory()
        request = factory.get("/tools/ics/extract/")
        resp = ics_extract(request)
        assert resp.status_code == 405


class TestIcsDownload:
    def test_returns_ics_file(self):
        factory = RequestFactory()
        payload = {
            "title": "Lunch",
            "start": "2026-05-20T12:00",
            "end": "2026-05-20T13:00",
            "location": "Cafe",
            "description": "Team lunch",
        }
        request = factory.post("/tools/ics/download/", json.dumps(payload), content_type="application/json")
        resp = ics_download(request)
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/calendar"
        assert resp["Content-Disposition"] == 'attachment; filename="Lunch.ics"'
        body = resp.content.decode()
        assert "BEGIN:VCALENDAR" in body
        assert "SUMMARY:Lunch" in body
        assert "LOCATION:Cafe" in body

    def test_missing_fields_uses_defaults(self):
        factory = RequestFactory()
        request = factory.post("/tools/ics/download/", json.dumps({}), content_type="application/json")
        resp = ics_download(request)
        assert resp.status_code == 200
        assert "SUMMARY:Event" in resp.content.decode()

    def test_rejects_get(self):
        factory = RequestFactory()
        request = factory.get("/tools/ics/download/")
        resp = ics_download(request)
        assert resp.status_code == 405


class TestAiExtract:
    @patch("tools.ai_extract._ollama_extract", return_value=MOCK_EVENT)
    def test_ollama_success(self, mock_ollama):
        from tools.ai_extract import extract_event

        result = extract_event("Meeting at 10am")
        assert result["title"] == "Team Standup"
        mock_ollama.assert_called_once_with("Meeting at 10am")

    @patch("tools.ai_extract._gemini_extract", side_effect=RuntimeError("no key"))
    @patch("tools.ai_extract._ollama_extract", side_effect=Exception("timeout"))
    def test_ollama_failure_falls_back(self, mock_ollama, mock_gemini):
        from tools.ai_extract import extract_event

        result = extract_event("Meeting at 10am")
        assert result["title"] == "Event"
        assert "Could not extract" in result["description"]

    def test_fallback_returns_valid_schema(self):
        result = _fallback("some text")
        assert result["title"] == "Event"
        assert "start" in result

    def test_event_schema_defaults(self):
        schema = EventSchema(start="2026-05-20T10:00:00")
        assert schema.title == "Event"
        assert schema.end is None
        assert schema.location == ""


class TestParseDt:
    def test_valid_iso(self):
        dt = _parse_dt("2026-05-20T12:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.hour == 12

    def test_none_input(self):
        assert _parse_dt(None) is None

    def test_empty_string(self):
        assert _parse_dt("") is None

    def test_invalid_string(self):
        assert _parse_dt("not a date") is None

import json

from django.test import RequestFactory

from tools.ics_maker import _mock_extract, _parse_dt, ics_download, ics_extract, ics_maker


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
    def test_returns_event_json(self):
        factory = RequestFactory()
        request = factory.post("/tools/ics/extract/", {"text": "Meeting tomorrow at 6pm", "url": ""})
        resp = ics_extract(request)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "title" in data
        assert "start" in data
        assert "end" in data

    def test_with_url_only(self):
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


class TestMockExtract:
    def test_returns_expected_fields(self):
        result = _mock_extract("Team standup at 10am in the office")
        assert "title" in result
        assert "start" in result
        assert "end" in result
        assert "location" in result
        assert "description" in result

    def test_description_contains_source(self):
        result = _mock_extract("Dinner at 7pm")
        assert "Dinner at 7pm" in result["description"]


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

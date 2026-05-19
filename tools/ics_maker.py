import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

TZ = ZoneInfo("Europe/Helsinki")


def ics_maker(request):
    return render(request, "tools/ics_maker.html")


@require_POST
def ics_extract(request):
    """Mock AI extraction — returns parsed event details as JSON."""
    text = request.POST.get("text", "").strip()
    url = request.POST.get("url", "").strip()

    if not text and not url:
        return JsonResponse({"error": "Provide text or a URL."}, status=400)

    # Mock extraction: pretend AI parsed the input
    source = text or f"Content from {url}"
    event = _mock_extract(source)
    return JsonResponse(event)


@require_POST
def ics_download(request):
    """Generate and return an .ics file from the extracted event data."""
    data = json.loads(request.body)
    title = data.get("title", "Event")
    dtstart = _parse_dt(data.get("start")) or datetime.now(TZ)
    dtend = _parse_dt(data.get("end")) or dtstart + timedelta(hours=1)
    location = data.get("location", "")
    description = data.get("description", "")

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//marco-silva.com//ics-maker//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}\r\n"
        f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}\r\n"
        f"SUMMARY:{title}\r\n"
    )
    if location:
        ics += f"LOCATION:{location}\r\n"
    if description:
        ics += f"DESCRIPTION:{description}\r\n"
    ics += "END:VEVENT\r\nEND:VCALENDAR\r\n"

    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{title}.ics"'
    return response


def _mock_extract(source):
    """Simulate AI extraction. Replace with real AI call later."""
    now = datetime.now(TZ)
    start = now.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return {
        "title": "Meeting (mock)",
        "start": start.isoformat(),
        "end": (start + timedelta(hours=1)).isoformat(),
        "location": "Helsinki",
        "description": f"Extracted from: {source[:100]}",
    }


def _parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt
    except (ValueError, TypeError):
        return None

import os
from datetime import datetime, timedelta

import requests
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from icalendar import Calendar

PLANZ_PASSWORD = os.environ.get("PLANZ_PASSWORD", "planz")
GOOGLE_CALENDAR_ICAL_URL = os.environ.get("GOOGLE_CALENDAR_ICAL_URL", "")


def planz(request):
    passwd = request.GET.get("passwd") or request.POST.get("passwd")
    if passwd == PLANZ_PASSWORD:
        return _render_calendar(request)
    return render(request, "tools/planz.html", {"error": bool(request.POST)})


@csrf_exempt
def planz_auth(request):
    passwd = request.POST.get("passwd", "")
    if passwd == PLANZ_PASSWORD:
        return _render_calendar(request)
    return HttpResponse('<p style="color: red; font-size: 0.85rem;">wrong password</p>', status=200)


def _render_calendar(request):
    events = _fetch_events()
    view = request.GET.get("view", "week")
    return render(request, "tools/partials/calendar.html", {"events": events, "view": view})


def _fetch_events():
    if not GOOGLE_CALENDAR_ICAL_URL:
        return []
    try:
        resp = requests.get(GOOGLE_CALENDAR_ICAL_URL, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    cal = Calendar.from_ical(resp.text)
    now = datetime.now().astimezone()
    cutoff = now + timedelta(days=90)
    events = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        if not dtstart:
            continue
        dt = dtstart.dt
        if hasattr(dt, "hour"):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
        else:
            dt = datetime.combine(dt, datetime.min.time()).replace(tzinfo=now.tzinfo)

        if dt < now - timedelta(days=7) or dt > cutoff:
            continue

        dtend = component.get("dtend")
        end = None
        if dtend:
            end = dtend.dt
            if not hasattr(end, "hour"):
                end = datetime.combine(end, datetime.min.time()).replace(tzinfo=now.tzinfo)
            elif end.tzinfo is None:
                end = end.replace(tzinfo=now.tzinfo)

        events.append(
            {
                "title": str(component.get("summary", "Untitled")),
                "start": dt,
                "end": end,
                "location": str(component.get("location", "")),
                "description": str(component.get("description", "")),
                "all_day": not hasattr(dtstart.dt, "hour"),
            }
        )

    events.sort(key=lambda e: e["start"])
    return events

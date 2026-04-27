import os
from datetime import date as date_type
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from icalendar import Calendar

PLANZ_PASSWORD = os.environ.get("PLANZ_PASSWORD", "planz")
GOOGLE_CALENDAR_ICAL_URL = os.environ.get("GOOGLE_CALENDAR_ICAL_URL", "")
PLANZ_TZ = ZoneInfo("Europe/Helsinki")
CACHE_KEY = "planz_events"
CACHE_TTL = 300


def planz(request):
    passwd = request.GET.get("passwd") or request.POST.get("passwd")
    if passwd == PLANZ_PASSWORD:
        ctx = _calendar_context(request)
        ctx["passwd"] = passwd
        return render(request, "tools/planz_full.html", ctx)
    return render(request, "tools/planz.html", {"error": bool(request.POST)})


@csrf_exempt
def planz_auth(request):
    passwd = request.POST.get("passwd", "")
    if passwd == PLANZ_PASSWORD:
        ctx = _calendar_context(request)
        ctx["passwd"] = passwd
        return render(request, "tools/partials/calendar_wrapper.html", ctx)
    return HttpResponse('<p style="color: red; font-size: 0.85rem;">wrong password</p>', status=200)


def planz_navigate(request):
    """HTMX partial or full page render for calendar navigation."""
    passwd = request.GET.get("passwd", "")
    if passwd != PLANZ_PASSWORD:
        return render(request, "tools/planz.html", {"error": False})
    ctx = _calendar_context(request)
    ctx["passwd"] = passwd
    if request.headers.get("HX-Request"):
        return render(request, "tools/partials/calendar.html", ctx)
    return render(request, "tools/planz_full.html", ctx)


def _calendar_context(request):
    all_events = _fetch_events()
    now = datetime.now(PLANZ_TZ)
    today = now.date()

    try:
        days = int(request.GET.get("days", "3"))
    except ValueError:
        days = 3
    if days not in (1, 3, 7):
        days = 3

    start_str = request.GET.get("start")
    if start_str:
        try:
            start_date = date_type.fromisoformat(start_str)
        except ValueError:
            start_date = today
    else:
        start_date = today

    end_date = start_date + timedelta(days=days)

    events = [e for e in all_events if start_date <= e["start"].date() < end_date]

    # Build day slots (including empty days)
    day_slots = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        day_events = [e for e in events if e["start"].date() == d]
        day_slots.append({"date": d, "events": day_events, "is_today": d == today})

    prev_date = start_date - timedelta(days=1)
    next_date = start_date + timedelta(days=1)

    passwd = request.GET.get("passwd") or request.POST.get("passwd", "")

    return {
        "events": events,
        "day_slots": day_slots,
        "today": today,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "prev_date": prev_date.isoformat(),
        "next_date": next_date.isoformat(),
        "passwd": passwd,
    }


def planz_ics(request):
    title = request.GET.get("title", "Event")
    start_str = request.GET.get("start", "")
    end_str = request.GET.get("end", "")
    location = request.GET.get("location", "")
    description = request.GET.get("description", "")

    try:
        dtstart = datetime.fromisoformat(start_str).replace(tzinfo=PLANZ_TZ)
    except (ValueError, TypeError):
        dtstart = datetime.now(PLANZ_TZ)

    dtend = None
    if end_str:
        try:
            dtend = datetime.fromisoformat(end_str).replace(tzinfo=PLANZ_TZ)
        except (ValueError, TypeError):
            pass
    if not dtend:
        dtend = dtstart + timedelta(hours=1)

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//marco-silva.com//planz//EN\r\n"
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


def _fetch_events():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    if not GOOGLE_CALENDAR_ICAL_URL:
        return []
    try:
        resp = requests.get(GOOGLE_CALENDAR_ICAL_URL, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    cal = Calendar.from_ical(resp.text)
    now = datetime.now(PLANZ_TZ)
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
                dt = dt.replace(tzinfo=PLANZ_TZ)
            dt = dt.astimezone(PLANZ_TZ)
        else:
            dt = datetime.combine(dt, datetime.min.time()).replace(tzinfo=PLANZ_TZ)

        if dt < now - timedelta(days=7) or dt > cutoff:
            continue

        dtend = component.get("dtend")
        end = None
        if dtend:
            end = dtend.dt
            if not hasattr(end, "hour"):
                end = datetime.combine(end, datetime.min.time()).replace(tzinfo=PLANZ_TZ)
            else:
                if end.tzinfo is None:
                    end = end.replace(tzinfo=PLANZ_TZ)
                end = end.astimezone(PLANZ_TZ)

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
    cache.set(CACHE_KEY, events, CACHE_TTL)
    return events

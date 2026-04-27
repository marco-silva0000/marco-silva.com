import os

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

PLANZ_PASSWORD = os.environ.get("PLANZ_PASSWORD", "planz")
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "")


def planz(request):
    passwd = request.GET.get("passwd") or request.POST.get("passwd")
    if passwd == PLANZ_PASSWORD:
        return _render_calendar(request)
    return render(request, "tools/planz.html", {"error": bool(request.POST)})


@csrf_exempt
def planz_auth(request):
    """HTMX endpoint for password check."""
    passwd = request.POST.get("passwd", "")
    if passwd == PLANZ_PASSWORD:
        return _render_calendar(request)
    return HttpResponse('<p style="color: red; font-size: 0.85rem;">wrong password</p>', status=200)


def _render_calendar(request):
    return render(request, "tools/partials/calendar.html", {"calendar_id": GOOGLE_CALENDAR_ID})

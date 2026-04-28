import random

from django.shortcuts import get_object_or_404, redirect, render

from .models import Room


def _make_captcha():
    a, b = random.randint(1, 20), random.randint(1, 20)
    return a, b, a + b


def room_list(request):
    rooms = Room.objects.filter(is_active=True)
    return render(request, "gamerooms/room_list.html", {"rooms": rooms})


def room_create(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        password = request.POST.get("password", "").strip()
        captcha_answer = request.POST.get("captcha_answer", "")
        captcha_expected = request.POST.get("captcha_expected", "")

        if not title:
            return _render_create(request, error="title is required")
        try:
            if int(captcha_answer) != int(captcha_expected):
                return _render_create(request, error="wrong captcha")
        except (ValueError, TypeError):
            return _render_create(request, error="wrong captcha")

        room = Room.objects.create(title=title, password=password)
        return redirect("gamerooms:room-join", code=room.code)

    return _render_create(request)


def _render_create(request, error=None):
    a, b, answer = _make_captcha()
    return render(request, "gamerooms/room_create.html", {"a": a, "b": b, "answer": answer, "error": error})


def room_join(request, code):
    room = get_object_or_404(Room, code=code, is_active=True)

    # Password check
    if room.has_password:
        pw = request.GET.get("pw") or request.POST.get("password")
        if not pw:
            return render(request, "gamerooms/room_password.html", {"room": room})
        if pw != room.password:
            return render(request, "gamerooms/room_password.html", {"room": room, "error": "wrong password"})
        # Password correct — continue with pw in context for next step
        name = request.POST.get("name", "").strip()
        if not name:
            return render(request, "gamerooms/room_name.html", {"room": room, "pw": pw})
        return redirect(f"/games/emojinary/{room.code}/{name}/?pw={pw}")

    # No password — just need name
    name = request.POST.get("name", "").strip() or request.GET.get("name", "").strip()
    if not name:
        return render(request, "gamerooms/room_name.html", {"room": room})
    return redirect("emojinary:game", code=room.code, name=name)

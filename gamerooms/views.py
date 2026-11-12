import random

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .models import Room


def _make_captcha():
    a, b = random.randint(1, 20), random.randint(1, 20)
    return a, b, a + b


def room_list(request):
    error = None
    code_input = (request.POST.get("code") or request.GET.get("code") or "").strip().upper()
    if code_input:
        if Room.objects.filter(code=code_input, is_active=True).exists():
            return redirect("gamerooms:room-join", code=code_input)
        error = _("Room code '%(code)s' was not found or is no longer active.") % {"code": code_input}
    elif request.method == "POST":
        error = _("Please enter a valid room code.")

    rooms = list(Room.objects.filter(is_active=True).order_by("-created_at"))
    for r in rooms:
        r.player_count = None
        r.phase_badge = None
        if r.game_type == "lupus":
            try:
                from lupus.game_state import get_game

                state = get_game(r.code)
                if state:
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round", 1)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase in ("day", "voting"):
                        r.phase_badge = f"🌅 {_('Day')} {rnd}"
                    elif phase == "night":
                        r.phase_badge = f"🌙 {_('Night')} {rnd}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
                    else:
                        r.phase_badge = f"🎮 {_('Active')}"
            except Exception:
                pass

    return render(request, "gamerooms/room_list.html", {"rooms": rooms, "error": error})


def room_create(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        password = request.POST.get("password", "").strip()
        captcha_answer = request.POST.get("captcha_answer", "")
        captcha_expected = request.POST.get("captcha_expected", "")

        if not title:
            return _render_create(request, error=_("title is required"))
        try:
            if int(captcha_answer) != int(captcha_expected):
                return _render_create(request, error=_("wrong captcha"))
        except (ValueError, TypeError):
            return _render_create(request, error=_("wrong captcha"))

        room = Room.objects.create(title=title, password=password)
        request.session[f"room_{room.code}"] = True
        return redirect("gamerooms:room-join", code=room.code)

    return _render_create(request)


def _render_create(request, error=None):
    a, b, answer = _make_captcha()
    return render(request, "gamerooms/room_create.html", {"a": a, "b": b, "answer": answer, "error": error})


def room_join(request, code):
    room = get_object_or_404(Room, code=code, is_active=True)
    if room.game_type == "lupus":
        target = reverse("gamerooms:lupus:join", kwargs={"code": room.code})
        qs = request.META.get("QUERY_STRING", "")
        if qs:
            target = f"{target}?{qs}"
        return redirect(target)

    session_key = f"room_{room.code}"

    # Step 1: password (if needed and not already authed)
    if room.has_password and not request.session.get(session_key):
        if request.method == "POST" and "password" in request.POST:
            if request.POST["password"] == room.password:
                request.session[session_key] = True
            else:
                return render(request, "gamerooms/room_password.html", {"room": room, "error": _("wrong password")})
        else:
            return render(request, "gamerooms/room_password.html", {"room": room})

    # Step 2: name
    if request.method == "POST" and "name" in request.POST:
        name = request.POST["name"].strip()
        if name:
            return redirect("gamerooms:emojinary:game", code=room.code, name=name)

    return render(request, "gamerooms/room_name.html", {"room": room})

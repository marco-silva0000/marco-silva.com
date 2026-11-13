import json
import random

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .language_support import (
    GAME_TYPES,
    get_game_language_support,
    get_language_support_matrix,
    normalize_language_code,
)
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
        r.language_support = get_game_language_support(r.game_type, getattr(r, "language", "en"))
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
        elif r.game_type == "emojinary":
            try:
                from emojinary.game_state import get_game as get_emojinary_game

                state = get_emojinary_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round_num", 0)
                    max_rnd = state.get("settings", {}).get("max_rounds", 10)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
                    else:
                        r.phase_badge = f"🎨 {_('Round')} {rnd}/{max_rnd}"
            except Exception:
                pass
        elif r.game_type == "impostor":
            try:
                from impostor.game_state import get_game as get_impostor_game

                state = get_impostor_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round_num", 0)
                    max_rnd = state.get("settings", {}).get("max_rounds", 5)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase == "clue":
                        r.phase_badge = f"🕵️ {_('Clues')} {rnd}/{max_rnd}"
                    elif phase == "voting":
                        r.phase_badge = f"🗳️ {_('Voting')} {rnd}/{max_rnd}"
                    elif phase == "last_chance":
                        r.phase_badge = f"⚡ {_('Steal Guess')}"
                    elif phase == "reveal":
                        r.phase_badge = f"🎭 {_('Reveal')} {rnd}/{max_rnd}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
            except Exception:
                pass

    return render(request, "gamerooms/room_list.html", {"rooms": rooms, "error": error})


def _resolve_game_type(raw_game_type: str | None) -> str:
    allowed = {g for g, _ in GAME_TYPES}
    gt = (raw_game_type or "").strip().lower()
    return gt if gt in allowed else "emojinary"


def room_create(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        password = request.POST.get("password", "").strip()
        game_type = _resolve_game_type(request.POST.get("game_type"))
        language = normalize_language_code(request.POST.get("language") or getattr(request, "LANGUAGE_CODE", "en"))
        captcha_answer = request.POST.get("captcha_answer", "")
        captcha_expected = request.POST.get("captcha_expected", "")

        if not title:
            return _render_create(request, error=_("title is required"), game_type=game_type, language=language)
        try:
            if int(captcha_answer) != int(captcha_expected):
                return _render_create(request, error=_("wrong captcha"), game_type=game_type, language=language)
        except (ValueError, TypeError):
            return _render_create(request, error=_("wrong captcha"), game_type=game_type, language=language)

        room = Room.objects.create(title=title, password=password, game_type=game_type, language=language)
        request.session[f"room_{room.code}"] = True
        request.session[f"emojinary_admin_{room.code}"] = True
        request.session[f"impostor_admin_{room.code}"] = True
        return redirect("gamerooms:room-join", code=room.code)

    game_type = _resolve_game_type(request.GET.get("game"))
    language = normalize_language_code(request.GET.get("lang") or getattr(request, "LANGUAGE_CODE", "en"))
    return _render_create(request, game_type=game_type, language=language)


def _render_create(request, error=None, game_type="emojinary", language=None):
    a, b, answer = _make_captcha()
    selected_game = _resolve_game_type(game_type)
    selected_lang = normalize_language_code(language or getattr(request, "LANGUAGE_CODE", "en"))
    initial_support = get_game_language_support(selected_game, selected_lang)
    return render(
        request,
        "gamerooms/room_create.html",
        {
            "a": a,
            "b": b,
            "answer": answer,
            "error": error,
            "game_types": GAME_TYPES,
            "selected_game": selected_game,
            "selected_language": selected_lang,
            "languages": settings.LANGUAGES,
            "initial_support": initial_support,
            "support_matrix_json": json.dumps(get_language_support_matrix()),
        },
    )


def room_join(request, code):
    code = code.upper()
    room = get_object_or_404(Room, code=code, is_active=True)
    if room.game_type == "lupus":
        target = reverse("gamerooms:lupus:join", kwargs={"code": room.code})
        qs = request.META.get("QUERY_STRING", "")
        if qs:
            target = f"{target}?{qs}"
        return redirect(target)

    session_key = f"room_{room.code}"

    # Support QR code auto-authentication via ?pwd=...
    param_pwd = request.GET.get("pwd") or request.POST.get("pwd")
    if param_pwd and room.has_password and param_pwd == room.password:
        request.session[session_key] = True

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
            if not room.creator:
                room.creator = name
                room.save(update_fields=["creator"])
            if room.game_type == "impostor":
                return redirect("gamerooms:impostor:game", code=room.code, name=name)
            return redirect("gamerooms:emojinary:game", code=room.code, name=name)

    return render(
        request,
        "gamerooms/room_name.html",
        {
            "room": room,
            "language_support": get_game_language_support(room.game_type, getattr(room, "language", "en")),
        },
    )

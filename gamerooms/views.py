import json
import random
import urllib.parse
from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .language_support import (
    GAME_TYPES,
    get_game_language_support,
    get_language_support_matrix,
    normalize_language_code,
)
from .models import Room, create_user_prompt_suggestion
from .security import is_rate_limited, safe_json_dumps


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
        elif r.game_type == "codenames":
            try:
                from codenames.game_state import get_game as get_codenames_game

                state = get_codenames_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round_num", 0)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase == "playing":
                        r.phase_badge = f"🧩 {_('Board')} #{rnd}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
            except Exception:
                pass
        elif r.game_type == "stop":
            try:
                from stop.game_state import get_game as get_stop_game

                state = get_stop_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round_num", 0)
                    max_rnd = state.get("settings", {}).get("max_rounds", 8)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase in ("playing", "reveal"):
                        r.phase_badge = f"🛑 {_('Round')} {rnd}/{max_rnd}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
            except Exception:
                pass
        elif r.game_type == "dontsay":
            try:
                from dontsay.game_state import get_game as get_dontsay_game

                state = get_dontsay_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round_num", 0)
                    max_rnd = state.get("settings", {}).get("max_rounds", 6)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase in ("answering", "reveal", "recap"):
                        r.phase_badge = f"🤐 {_('Round')} {rnd}/{max_rnd}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
            except Exception:
                pass
        elif r.game_type == "rankit":
            try:
                from rankit.game_state import get_game as get_rankit_game

                state = get_rankit_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    lvl = state.get("level", 1)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase in ("playing", "staging"):
                        r.phase_badge = f"🔢 {_('Level')} {lvl}"
                    elif phase == "level_success":
                        r.phase_badge = f"🎉 {_('Cleared')}"
                    elif phase == "victory":
                        r.phase_badge = f"🏆 {_('Victory')}"
                    elif phase == "gameover":
                        r.phase_badge = f"💀 {_('Game Over')}"
            except Exception:
                pass
        elif r.game_type == "smartn":
            try:
                from smartn.game_state import get_game as get_smartn_game

                state = get_smartn_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", []))
                    phase = state.get("phase", "lobby")
                    rnd = state.get("round_num", 0)
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase == "playing":
                        r.phase_badge = f"💡 {_('Card')} {rnd}"
                    elif phase == "round_summary":
                        r.phase_badge = f"🏁 {_('Summary')}"
                    elif phase == "gameover":
                        r.phase_badge = f"🏆 {_('Finished')}"
            except Exception:
                pass
        elif r.game_type == "secretsanta":
            try:
                from secretsanta.game_state import get_game as get_secretsanta_game

                state = get_secretsanta_game(r.code)
                if state and state.get("players"):
                    r.player_count = len(state.get("players", {}))
                    phase = state.get("phase", "lobby")
                    if phase == "lobby":
                        r.phase_badge = f"⏳ {_('Lobby')}"
                    elif phase == "matched":
                        r.phase_badge = f"🎁 {_('Matched')}"
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
        request.session[f"{room.game_type}_admin_{room.code}"] = True
        request.session[f"admin_{room.code}"] = True
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
            "support_matrix_json": safe_json_dumps(get_language_support_matrix()),
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

            # Check if this session already has a player token for this game and pass it in the redirect
            game_token_key = f"{room.game_type}_player_{room.code}"
            existing_token = request.session.get(game_token_key)
            params = {"name": name}
            if existing_token:
                params["token"] = existing_token
            query_suffix = f"?{urlencode(params)}"

            try:
                play_url = reverse(f"gamerooms:{room.game_type}:play", kwargs={"code": room.code})
            except Exception:
                play_url = reverse(f"gamerooms:{room.game_type}:game-play", kwargs={"code": room.code})
            return redirect(f"{play_url}{query_suffix}")

    return render(
        request,
        "gamerooms/room_name.html",
        {
            "room": room,
            "language_support": get_game_language_support(room.game_type, getattr(room, "language", "en")),
        },
    )


@require_POST
def suggest_prompt(request):
    """API endpoint for players to submit questions/categories for the prompt deck."""
    if is_rate_limited(request, scope="suggest_prompt", limit=15, window_seconds=60):
        return JsonResponse({"success": False, "message": _("Too many requests. Please slow down.")}, status=429)

    data = {}
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"success": False, "message": _("Invalid JSON payload.")}, status=400)
    else:
        data = request.POST

    text = data.get("text", "")
    domain = data.get("domain", "mix")
    game_type = data.get("game_type", "dontsay")
    sample_answers = data.get("sample_answers", [])
    submitter_name = data.get("submitter_name", "")
    room_code = data.get("room_code", "")

    ok, msg, prompt_obj = create_user_prompt_suggestion(
        text=text,
        domain=domain,
        game_type=game_type,
        sample_answers=sample_answers,
        submitter_name=submitter_name,
        submitter_room=room_code,
    )

    if not ok:
        return JsonResponse({"success": False, "message": msg}, status=400)

    return JsonResponse(
        {
            "success": True,
            "message": _(
                "Thank you! Your question has been submitted and queued for review. "
                "Once approved by the Game Master, it will appear in active game rotations!"
            ),
            "prompt_id": prompt_obj.prompt_id if prompt_obj else None,
        }
    )


def legacy_game_redirect(request, code: str, name: str, game_type: str):
    """302 redirect legacy /games/<game>/<CODE>/<name>/ paths to clean /play/?name=... URLs."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    try:
        play_url = reverse(f"gamerooms:{game_type}:play", kwargs={"code": code})
    except Exception:
        play_url = reverse(f"gamerooms:{game_type}:game-play", kwargs={"code": code})
    qs = request.META.get("QUERY_STRING", "")
    params = f"?name={urllib.parse.quote(name)}&{qs}" if qs else f"?name={urllib.parse.quote(name)}"
    return redirect(f"{play_url}{params}")

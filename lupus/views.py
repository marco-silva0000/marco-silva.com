"""Views for Lupus game room creation, GM management, QR join, and player interface."""

from urllib.parse import urlencode

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from gamerooms.models import Room

from .game_state import (
    add_player,
    create_initial_state,
    export_game_replay,
    get_game,
    get_gm_view,
    get_sanitized_player_view,
    setup_demo_room,
    should_autofill_demo,
)
from .qr import generate_qr_data_uri
from .roles import DEFAULT_PRESETS, ROLE_REGISTRY, get_all_roles_by_category, get_all_roles_catalogue


@never_cache
def lupus_hub(request):
    """Active rooms and landing hub for Lupus / Werewolf game."""
    error = None
    # Support code join via GET (?code=ABC) or POST
    code_input = (request.POST.get("code") or request.GET.get("code") or "").strip().upper()
    if code_input:
        if Room.objects.filter(code=code_input, is_active=True).exists():
            return redirect("gamerooms:lupus:join", code=code_input)
        error = _("Room code '%(code)s' was not found or is no longer active.") % {"code": code_input}
    elif request.method == "POST":
        error = _("Please enter a valid room code.")

    # Query active lupus rooms
    rooms_qs = Room.objects.filter(game_type="lupus", is_active=True).order_by("-created_at")
    all_rooms = []
    for r in rooms_qs:
        state = None
        try:
            state = get_game(r.code)
        except Exception:
            state = None

        room_info = {
            "room": r,
            "code": r.code,
            "title": (state.get("title") if state else None) or r.title,
            "created_at": r.created_at,
            "has_password": r.has_password,
            "gm_name": (state.get("gm_name") if state else None) or r.creator or "Game Master",
            "player_count": len(state.get("players", {})) if state else 0,
            "living_count": (
                sum(1 for p in state.get("players", {}).values() if p.get("status") == "alive")
                if state
                else 0
            ),
            "phase": state.get("phase", "lobby") if state else "active",
            "round": state.get("round_number", 0) if state else 0,
            "theme": state.get("theme", "werewolf") if state else "werewolf",
            "is_gm": bool(state and request.session.get(f"lupus_gm_{r.code}") == state.get("gm_token")),
            "joined_player": None,
        }

        # Lifecycle status (open, running, finished)
        status = getattr(r, "status", None) or (state.get("status") if state else Room.STATUS_OPEN)
        room_info["status"] = status
        if status == Room.STATUS_FINISHED or room_info["phase"] == "gameover":
            room_info["status_label"] = _("Finished")
            room_info["status_badge"] = f"🏁 {_('Finished')}"
            room_info["status_color"] = "#64748b"
        elif status == Room.STATUS_RUNNING or room_info["phase"] in ("night", "day_discussion", "day_defense", "day_voting", "limbo"):
            room_info["status_label"] = _("Running")
            room_info["status_badge"] = f"⚡ {_('Running')}"
            room_info["status_color"] = "#2563eb"
        else:
            room_info["status_label"] = _("Open")
            room_info["status_badge"] = f"🟢 {_('Open (Lobby)')}"
            room_info["status_color"] = "#16a34a"

        # Check if current visitor has a joined player session in this room
        if state:
            p_token = request.session.get(f"lupus_player_{r.code}")
            if p_token:
                for p in state.get("players", {}).values():
                    if p.get("token") == p_token:
                        room_info["joined_player"] = p
                        break

        # Friendly phase display
        phase = room_info["phase"]
        rnd = room_info["round"]
        if phase == "lobby":
            room_info["phase_label"] = _("Lobby (Waiting for Players)")
            room_info["phase_badge"] = f"⏳ {_('Lobby')}"
            room_info["phase_color"] = "#64748b"
        elif phase == "day_discussion":
            room_info["phase_label"] = f"{_('Day')} {rnd} - {_('Discussion')}"
            room_info["phase_badge"] = f"🌅 {_('Day')} {rnd}"
            room_info["phase_color"] = "#d97706"
        elif phase in ("day_voting", "day_defense"):
            room_info["phase_label"] = f"{_('Day')} {rnd} - {_('Town Voting')}"
            room_info["phase_badge"] = f"⚖️ {_('Voting')} {rnd}"
            room_info["phase_color"] = "#b45309"
        elif phase == "night":
            room_info["phase_label"] = f"{_('Night')} {rnd} - {_('Silent Phase')}"
            room_info["phase_badge"] = f"🌙 {_('Night')} {rnd}"
            room_info["phase_color"] = "#4338ca"
        elif phase == "limbo":
            room_info["phase_label"] = _("Limbo Resolution")
            room_info["phase_badge"] = f"👻 {_('Limbo')}"
            room_info["phase_color"] = "#7c3aed"
        elif phase == "gameover":
            room_info["phase_label"] = _("Game Over")
            room_info["phase_badge"] = f"🏆 {_('Finished')}"
            room_info["phase_color"] = "#059669"
        else:
            room_info["phase_label"] = _("In Progress")
            room_info["phase_badge"] = f"🎮 {_('Active')}"
            room_info["phase_color"] = "#2563eb"

        all_rooms.append(room_info)

    active_rooms = [r for r in all_rooms if r["status"] != Room.STATUS_FINISHED]
    finished_rooms = [r for r in all_rooms if r["status"] == Room.STATUS_FINISHED]

    return render(
        request,
        "lupus/hub.html",
        {
            "rooms": active_rooms,
            "active_rooms": active_rooms,
            "finished_rooms": finished_rooms,
            "error": error,
        },
    )


@never_cache
def create_room(request):
    """Create a new Lupus game room and initialize the GM dashboard."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip() or "Lupus Night"
        password = request.POST.get("password", "").strip()
        theme = request.POST.get("theme", "werewolf")
        discussion_timer = int(request.POST.get("discussion_timer", 300))
        defense_timer = int(request.POST.get("defense_timer", 30))
        staggering_doc = request.POST.get("staggering_doctor") == "1"
        save_from_sniper = request.POST.get("doctor_saves_from_sniper") == "1"
        sniper_bullet = request.POST.get("sniper_bullet_type", "danger")
        limbo_on = request.POST.get("limbo_enabled") == "1"

        # Create gamerooms.Room
        gm_name = request.POST.get("gm_name", "Game Master").strip() or "Game Master"
        room = Room.objects.create(
            title=title,
            password=password,
            game_type="lupus",
            creator=gm_name,
            status=Room.STATUS_OPEN,
        )

        reveal_raw = request.POST.get("reveal_roles_on_death", "0")
        try:
            reveal_level = int(reveal_raw)
        except (ValueError, TypeError):
            reveal_level = 1 if reveal_raw in ("1", "true", "True") else 0

        try:
            danger_bullets = int(request.POST.get("sniper_danger_bullets", 1) or 1)
        except (ValueError, TypeError):
            danger_bullets = 1

        try:
            silver_bullets = int(request.POST.get("sniper_silver_bullets", 0) or 0)
        except (ValueError, TypeError):
            silver_bullets = 0

        settings = {
            "discussion_timer": discussion_timer,
            "defense_timer": defense_timer,
            "staggering_doctor": staggering_doc,
            "doctor_saves_from_sniper": save_from_sniper,
            "sniper_bullet_type": sniper_bullet,
            "sniper_danger_bullets": danger_bullets,
            "sniper_silver_bullets": silver_bullets,
            "limbo_enabled": limbo_on,
            "reveal_roles_on_death": reveal_level,
            "mayor_type": request.POST.get("mayor_type", "public"),
            "public_mayor": request.POST.get("mayor_type", "public") == "public",
            "martyrdom_type": request.POST.get("martyrdom_type", "public"),
            "public_martyrdom": request.POST.get("martyrdom_type", "public") == "public",
        }

        gm_name = request.POST.get("gm_name", "Game Master").strip() or "Game Master"

        state = create_initial_state(
            code=room.code,
            title=title,
            password=password,
            gm_name=gm_name,
            theme=theme,
            settings=settings,
        )

        # Set default deck
        preset = request.POST.get("preset", "balanced_8")
        state["deck"] = list(DEFAULT_PRESETS.get(preset, DEFAULT_PRESETS["balanced_8"]))

        # Demo trigger: if password is like 'test' and narrator is 'marco', autofill 10 test players
        if should_autofill_demo(password, gm_name):
            setup_demo_room(state)

        from .game_state import save_game

        save_game(room.code, state)

        # Authorize GM in session
        request.session[f"lupus_gm_{room.code}"] = state["gm_token"]
        return redirect(f"{reverse('gamerooms:lupus:gm', kwargs={'code': room.code})}?gm_token={state['gm_token']}")

    return render(
        request,
        "lupus/create.html",
        {
            "roles": ROLE_REGISTRY,
            "presets": DEFAULT_PRESETS,
        },
    )


@never_cache
def gm_dashboard(request, code):
    """Cockpit for the Game Master."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404(_("Game not found."))

    if state.get("next_room_code") and not request.GET.get("stay"):
        next_code = state["next_room_code"]
        gm_token = request.GET.get("gm_token") or request.session.get(f"lupus_gm_{code}")
        next_url = reverse("gamerooms:lupus:gm", kwargs={"code": next_code})
        params = {}
        if gm_token:
            params["gm_token"] = gm_token
            request.session[f"lupus_gm_{next_code}"] = gm_token
        qs = f"?{urlencode(params)}" if params else ""
        return redirect(f"{next_url}{qs}")

    gm_token = request.GET.get("gm_token") or request.session.get(f"lupus_gm_{code}")
    if gm_token != state.get("gm_token"):
        return render(
            request,
            "lupus/unauthorized.html",
            {"message": _("Invalid Game Master secret key."), "code": code},
            status=403,
        )

    # Cache in session
    request.session[f"lupus_gm_{code}"] = gm_token

    # Build join URL with embedded password if set (strictly HTTPS for public domains/proxies)
    join_path = reverse("gamerooms:lupus:join", kwargs={"code": code})
    query_params = {}
    if state.get("password"):
        query_params["pwd"] = state["password"]

    host = request.get_host()
    is_public = any(d in host for d in ["marco-silva.com", "dev.marco-silva.com"])
    scheme = (
        "https"
        if (is_public or request.is_secure() or request.headers.get("x-forwarded-proto") == "https")
        else request.scheme
    )
    query_str = f"?{urlencode(query_params)}" if query_params else ""
    join_url = f"{scheme}://{host}{join_path}{query_str}"

    join_qr_b64 = generate_qr_data_uri(join_url)

    return render(
        request,
        "lupus/gm_dashboard.html",
        {
            "code": code,
            "gm_token": gm_token,
            "state": get_gm_view(state),
            "join_url": join_url,
            "join_qr": join_qr_b64,
            "roles": ROLE_REGISTRY,
            "roles_catalogue": get_all_roles_catalogue(state.get("theme", "werewolf")),
            "roles_by_category": get_all_roles_by_category(state.get("theme", "werewolf")),
            "presets": DEFAULT_PRESETS,
        },
    )


@never_cache
def export_replay(request, code):
    """Export complete reproducible replay JSON of the room's game state."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404("Game not found.")
    replay_data = export_game_replay(state)
    response = JsonResponse(replay_data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="lupus_replay_{code.lower()}.json"'
    return response


@never_cache
def room_join(request, code):
    """Player join screen. Automatically validates password from QR code query param."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404(_("Game room does not exist."))

    if state.get("next_room_code"):
        next_code = state["next_room_code"]
        next_url = reverse("gamerooms:lupus:join", kwargs={"code": next_code})
        params = {}
        param_pwd = request.GET.get("pwd") or request.POST.get("pwd")
        if param_pwd:
            params["pwd"] = param_pwd
        qs = f"?{urlencode(params)}" if params else ""
        return redirect(f"{next_url}{qs}")

    # If player already joined from this device, redirect back to their active play view
    existing_token = request.session.get(f"lupus_player_{code}")
    if existing_token and not request.GET.get("new") and request.method != "POST":
        for p in state.get("players", {}).values():
            if p["token"] == existing_token:
                play_url = reverse("gamerooms:lupus:play", kwargs={"code": code})
                return redirect(f"{play_url}?token={p['token']}&pid={p['id']}")

    session_pw_key = f"lupus_pwd_ok_{code}"
    room_password = state.get("password", "")

    # Auto-authenticate if password is provided in query params (?pwd=...) or POST
    param_pwd = request.GET.get("pwd") or request.POST.get("pwd")
    if param_pwd and param_pwd == room_password:
        request.session[session_pw_key] = True

    # Check password requirement
    if room_password and not request.session.get(session_pw_key):
        if request.method == "POST" and "password" in request.POST:
            if request.POST["password"] == room_password:
                request.session[session_pw_key] = True
            else:
                return render(
                    request,
                    "lupus/join.html",
                    {"code": code, "error": _("Incorrect room password."), "need_password": True},
                )
        else:
            return render(
                request,
                "lupus/join.html",
                {"code": code, "need_password": True},
            )

    # Handle player name registration
    if request.method == "POST" and "name" in request.POST:
        name = request.POST["name"].strip()
        if not name:
            return render(
                request,
                "lupus/join.html",
                {"code": code, "error": _("Please enter a player name.")},
            )

        state, player = add_player(state, name, is_offline=False)
        request.session[f"lupus_player_{code}"] = player["token"]

        # Instantly sync GM dashboard and existing connected clients
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"lupus_{code}",
                    {"type": "game.state.sync"},
                )
        except Exception:
            pass

        return redirect(
            f"{reverse('gamerooms:lupus:play', kwargs={'code': code})}?token={player['token']}&pid={player['id']}"
        )

    return render(
        request,
        "lupus/join.html",
        {"code": code, "state": state, "need_password": False, "param_pwd": param_pwd or ""},
    )


@never_cache
def player_view(request, code):
    """Player's responsive personal card and action interface."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404("Game room not found.")

    if state.get("next_room_code"):
        next_code = state["next_room_code"]
        token = request.GET.get("token") or request.session.get(f"lupus_player_{code}")
        player_id = request.GET.get("pid")
        next_url = reverse("gamerooms:lupus:play", kwargs={"code": next_code})
        params = {}
        if token:
            params["token"] = token
            request.session[f"lupus_player_{next_code}"] = token
        if player_id:
            params["pid"] = player_id
        qs = f"?{urlencode(params)}" if params else ""
        return redirect(f"{next_url}{qs}")

    token = request.GET.get("token") or request.session.get(f"lupus_player_{code}")
    player_id = request.GET.get("pid")

    # Locate player by token or ID
    matched_player = None
    if token:
        for p in state["players"].values():
            if p["token"] == token:
                matched_player = p
                break
    elif player_id and player_id in state["players"]:
        matched_player = state["players"][player_id]

    if not matched_player:
        return redirect("gamerooms:lupus:join", code=code)

    request.session[f"lupus_player_{code}"] = matched_player["token"]

    return render(
        request,
        "lupus/player.html",
        {
            "code": code,
            "player": matched_player,
            "state": get_sanitized_player_view(state, matched_player["id"]),
            "roles_catalogue": get_all_roles_catalogue(state.get("theme", "werewolf")),
            "roles_by_category": get_all_roles_by_category(state.get("theme", "werewolf")),
        },
    )


@never_cache
def player_reconnect(request, code, token):
    """Direct URL or scanned QR code for a player to seamlessly reconnect."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404("Room not found.")

    matched_player = None
    for p in state["players"].values():
        if p["token"] == token:
            matched_player = p
            break

    if not matched_player:
        return render(
            request,
            "lupus/unauthorized.html",
            {"message": "Invalid player reconnect token.", "code": code},
            status=404,
        )

    request.session[f"lupus_player_{code}"] = token
    play_url = reverse("gamerooms:lupus:play", kwargs={"code": code})
    return redirect(f"{play_url}?token={token}&pid={matched_player['id']}")


@never_cache
def player_qr(request, code, token):
    """Generate a QR code image for a player's secret reconnect URL."""
    code = code.upper()
    reconnect_path = reverse("gamerooms:lupus:reconnect", kwargs={"code": code, "token": token})
    host = request.get_host()
    is_public = any(d in host for d in ["marco-silva.com", "dev.marco-silva.com"])
    scheme = (
        "https"
        if (is_public or request.is_secure() or request.headers.get("x-forwarded-proto") == "https")
        else request.scheme
    )
    reconnect_url = f"{scheme}://{host}{reconnect_path}"
    qr_data_uri = generate_qr_data_uri(reconnect_url)
    return JsonResponse({"qr": qr_data_uri, "url": reconnect_url})

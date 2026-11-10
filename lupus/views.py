"""Views for Lupus game room creation, GM management, QR join, and player interface."""

from urllib.parse import urlencode

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.models import Room

from .game_state import (
    add_player,
    create_initial_state,
    get_game,
    get_gm_view,
    get_sanitized_player_view,
    setup_demo_room,
    should_autofill_demo,
)
from .qr import generate_qr_data_uri
from .roles import DEFAULT_PRESETS, ROLE_REGISTRY, get_all_roles_catalogue


@never_cache
def lupus_hub(request):
    """Active rooms and landing hub for Lupus / Werewolf game."""
    error = None
    # Support code join via GET (?code=ABC) or POST
    code_input = (request.POST.get("code") or request.GET.get("code") or "").strip().upper()
    if code_input:
        if Room.objects.filter(code=code_input, is_active=True).exists():
            return redirect("gamerooms:lupus:join", code=code_input)
        error = f"Room code '{code_input}' was not found or is no longer active."
    elif request.method == "POST":
        error = "Please enter a valid room code."

    # Query active lupus rooms
    rooms_qs = Room.objects.filter(game_type="lupus", is_active=True).order_by("-created_at")
    active_rooms = []
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
            "round": state.get("round", 1) if state else 1,
            "theme": state.get("theme", "werewolf") if state else "werewolf",
            "is_gm": bool(state and request.session.get(f"lupus_gm_{r.code}") == state.get("gm_token")),
            "joined_player": None,
        }

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
            room_info["phase_label"] = "Lobby (Waiting for Players)"
            room_info["phase_badge"] = "⏳ Lobby"
            room_info["phase_color"] = "#64748b"
        elif phase == "day":
            room_info["phase_label"] = f"Day {rnd} - Discussion"
            room_info["phase_badge"] = f"🌅 Day {rnd}"
            room_info["phase_color"] = "#d97706"
        elif phase == "voting":
            room_info["phase_label"] = f"Day {rnd} - Town Voting"
            room_info["phase_badge"] = f"⚖️ Voting {rnd}"
            room_info["phase_color"] = "#b45309"
        elif phase == "night":
            room_info["phase_label"] = f"Night {rnd} - Silent Phase"
            room_info["phase_badge"] = f"🌙 Night {rnd}"
            room_info["phase_color"] = "#4338ca"
        elif phase == "limbo":
            room_info["phase_label"] = "Limbo Resolution"
            room_info["phase_badge"] = "👻 Limbo"
            room_info["phase_color"] = "#7c3aed"
        elif phase == "gameover":
            room_info["phase_label"] = "Game Over"
            room_info["phase_badge"] = "🏆 Finished"
            room_info["phase_color"] = "#059669"
        else:
            room_info["phase_label"] = "In Progress"
            room_info["phase_badge"] = "🎮 Active"
            room_info["phase_color"] = "#2563eb"

        active_rooms.append(room_info)

    return render(
        request,
        "lupus/hub.html",
        {
            "rooms": active_rooms,
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
        room = Room.objects.create(
            title=title,
            password=password,
            game_type="lupus",
        )

        settings = {
            "discussion_timer": discussion_timer,
            "defense_timer": defense_timer,
            "staggering_doctor": staggering_doc,
            "doctor_saves_from_sniper": save_from_sniper,
            "sniper_bullet_type": sniper_bullet,
            "limbo_enabled": limbo_on,
            "reveal_roles_on_death": request.POST.get("reveal_roles_on_death") == "1",
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
        raise Http404("Game not found.")

    gm_token = request.GET.get("gm_token") or request.session.get(f"lupus_gm_{code}")
    if gm_token != state.get("gm_token"):
        return render(
            request,
            "lupus/unauthorized.html",
            {"message": "Invalid Game Master secret key.", "code": code},
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
            "presets": DEFAULT_PRESETS,
        },
    )


@never_cache
def room_join(request, code):
    """Player join screen. Automatically validates password from QR code query param."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404("Game room does not exist.")

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
                    {"code": code, "error": "Incorrect room password.", "need_password": True},
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
                {"code": code, "error": "Please enter a player name."},
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

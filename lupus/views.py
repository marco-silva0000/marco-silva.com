"""Views for Lupus game room creation, GM management, QR join, and player interface."""

from urllib.parse import urlencode

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

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
    scheme = "https" if (is_public or request.is_secure() or request.headers.get("x-forwarded-proto") == "https") else request.scheme
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


def player_qr(request, code, token):
    """Generate a QR code image for a player's secret reconnect URL."""
    code = code.upper()
    reconnect_path = reverse("gamerooms:lupus:reconnect", kwargs={"code": code, "token": token})
    host = request.get_host()
    is_public = any(d in host for d in ["marco-silva.com", "dev.marco-silva.com"])
    scheme = "https" if (is_public or request.is_secure() or request.headers.get("x-forwarded-proto") == "https") else request.scheme
    reconnect_url = f"{scheme}://{host}{reconnect_path}"
    qr_data_uri = generate_qr_data_uri(reconnect_url)
    return JsonResponse({"qr": qr_data_uri, "url": reconnect_url})

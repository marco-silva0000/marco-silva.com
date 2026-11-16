"""Views for 'Don't Say the Same Thing as Me' gameplay, QR codes, and seat reconnection."""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.qr import build_public_url, generate_qr_data_uri

from .game_state import (
    COLLISION_MODES,
    add_player,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)


@never_cache
def room_join_redirect(request, code):
    """Redirect short /games/dontsay/<code>/ links to existing player session or room join."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    token = request.GET.get("token") or request.session.get(f"dontsay_player_{code}")
    existing = find_player_by_token(state, token)
    if existing and not request.GET.get("new"):
        return redirect("gamerooms:dontsay:game", code=code, name=existing["name"])
    join_url = reverse("gamerooms:room-join", kwargs={"code": code})
    pwd = request.GET.get("pwd")
    if pwd:
        return redirect(f"{join_url}?pwd={pwd}")
    return redirect(join_url)


@never_cache
def game(request, code, name):
    code = code.upper()
    room = get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    state["title"] = room.title
    state["password"] = room.password
    state["language"] = getattr(room, "language", "en") or "en"

    query_token = request.GET.get("token")
    session_token = request.session.get(f"dontsay_player_{code}")
    token = query_token or session_token
    session_admin = bool(request.session.get(f"dontsay_admin_{code}"))

    existing = find_player_by_token(state, token)
    if existing:
        player = existing
        if session_admin and (not state.get("creator_id") or player.get("id") == state.get("creator_id")):
            player["is_admin"] = True
        save_game(code, state)
    else:
        by_name = find_player_by_name(state, name)
        if by_name and (
            session_admin
            or not query_token
            or by_name.get("id") == state.get("creator_id")
            or state.get("phase") in ("lobby", "waiting", None)
        ):
            player = by_name
            if session_admin:
                player["is_admin"] = True
            player["connected"] = True
            save_game(code, state)
        else:
            grant_admin = session_admin and not query_token and not state.get("creator_id")
            state, player, _ = add_player(
                state,
                name=name,
                token=token,
                is_admin=grant_admin,
            )

    request.session[f"dontsay_player_{code}"] = player["token"]
    if player.get("is_admin") and (not query_token or player.get("id") == state.get("creator_id")):
        request.session[f"dontsay_admin_{code}"] = True

    join_path = reverse("gamerooms:room-join", kwargs={"code": code})
    join_params = {"pwd": room.password} if room.has_password else None
    join_url = build_public_url(request, join_path, join_params)
    join_qr = generate_qr_data_uri(join_url)

    reconnect_path = reverse("gamerooms:dontsay:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    reconnect_qr = generate_qr_data_uri(reconnect_url)

    admin_token = None
    if player.get("is_admin"):
        admin_token = state.get("admin_token")
        if not admin_token:
            import uuid

            admin_token = uuid.uuid4().hex[:16]
            state["admin_token"] = admin_token
            save_game(code, state)

    sanitized = get_sanitized_player_view(state, player["token"])
    lang_support = get_game_language_support("dontsay", state.get("language", "en"))

    context = {
        "room": room,
        "player": player,
        "player_id": player["id"],
        "player_name": player["name"],
        "player_token": player["token"],
        "admin_token": admin_token or "",
        "join_url": join_url,
        "join_qr": join_qr,
        "reconnect_url": reconnect_url,
        "reconnect_qr": reconnect_qr,
        "initial_state_json": json.dumps(sanitized),
        "language_support": lang_support,
        "collision_modes": COLLISION_MODES,
    }
    return render(request, "dontsay/game.html", context)


@never_cache
def reconnect(request, code, token):
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    player = find_player_by_token(state, token)
    if not player:
        raise Http404("Player token not found for this room")

    request.session[f"dontsay_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"dontsay_admin_{code}"] = True

    game_url = reverse("gamerooms:dontsay:game", kwargs={"code": code, "name": player["name"]})
    return redirect(f"{game_url}?token={player['token']}")


def api_game_state(request, code):
    code = code.upper()
    state = get_game(code)
    token = request.GET.get("token") or request.session.get(f"dontsay_player_{code}")
    sanitized = get_sanitized_player_view(state, token)
    return JsonResponse(sanitized)

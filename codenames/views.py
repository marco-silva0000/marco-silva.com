"""Views for Codenames Multiplayer gameplay, personal player QR reconnects, and JSON replay export."""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.qr import build_public_url, generate_qr_data_uri

from .game_state import (
    DEFAULT_SETTINGS,
    add_player,
    export_game_replay,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)
from .words import WORD_PACKS


@never_cache
def room_join_redirect(request, code):
    """Redirect short /games/codenames/<code>/ links to existing player session or room join."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    token = request.GET.get("token") or request.session.get(f"codenames_player_{code}")
    existing = find_player_by_token(state, token)
    if existing and not request.GET.get("new"):
        return redirect("gamerooms:codenames:game", code=code, name=existing["name"])
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
    session_token = request.session.get(f"codenames_player_{code}")
    token = query_token or session_token
    session_admin = bool(request.session.get(f"codenames_admin_{code}"))

    existing = find_player_by_token(state, token)
    if existing:
        player = existing
        # Only promote to admin if this browser session owns the room creator
        if session_admin and (not state.get("creator_id") or player.get("id") == state.get("creator_id")):
            player["is_admin"] = True
        save_game(code, state)
    else:
        grant_admin = session_admin and not query_token and not state.get("creator_id")
        state, player, _ = add_player(
            state,
            name=name,
            token=token,
            is_admin=grant_admin,
        )

    if not query_token or not session_token:
        request.session[f"codenames_player_{code}"] = player["token"]
    if player.get("is_admin") and (not query_token or player.get("id") == state.get("creator_id")):
        request.session[f"codenames_admin_{code}"] = True

    join_path = reverse("gamerooms:room-join", kwargs={"code": code})
    join_params = {"pwd": room.password} if room.has_password else None
    join_url = build_public_url(request, join_path, join_params)
    join_qr = generate_qr_data_uri(join_url)

    reconnect_path = reverse("gamerooms:codenames:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    player_qr_uri = generate_qr_data_uri(reconnect_url)

    initial_state = get_sanitized_player_view(state, player["id"])
    language_support = get_game_language_support("codenames", state.get("language", "en"))

    return render(
        request,
        "codenames/game.html",
        {
            "room": room,
            "player": player,
            "player_name": player["name"],
            "player_id": player["id"],
            "player_token": player["token"],
            "admin_token": state.get("admin_token", "") if player.get("is_admin") else "",
            "join_url": join_url,
            "join_qr": join_qr,
            "reconnect_url": reconnect_url,
            "player_qr": player_qr_uri,
            "word_packs": WORD_PACKS,
            "default_settings": DEFAULT_SETTINGS,
            "language_support": language_support,
            "initial_state_json": json.dumps(initial_state),
        },
    )


@never_cache
def player_reconnect(request, code, token):
    """Reconnect link for switching devices mid-match with multi-tab admin isolation."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    matched = find_player_by_token(state, token)
    if not matched:
        raise Http404("Invalid player reconnect token.")

    request.session[f"room_{code}"] = True
    existing_session_token = request.session.get(f"codenames_player_{code}")
    existing_session_admin = bool(request.session.get(f"codenames_admin_{code}"))
    if not existing_session_token or (matched.get("is_admin") and not existing_session_admin):
        request.session[f"codenames_player_{code}"] = token
    if matched.get("is_admin"):
        request.session[f"codenames_admin_{code}"] = True

    game_url = reverse("gamerooms:codenames:game", kwargs={"code": code, "name": matched["name"]})
    return redirect(f"{game_url}?token={token}")


@never_cache
def player_qr(request, code, token):
    """Generate an individual QR code image and URL for a player's private reconnect link."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    matched = state.get("players", {}).get(token) or find_player_by_token(state, token)
    if not matched:
        raise Http404("Player not found in this room.")

    reconnect_path = reverse(
        "gamerooms:codenames:reconnect",
        kwargs={"code": code, "token": matched["token"]},
    )
    reconnect_url = build_public_url(request, reconnect_path)
    qr_data_uri = generate_qr_data_uri(reconnect_url)
    return JsonResponse(
        {
            "qr": qr_data_uri,
            "url": reconnect_url,
            "player_id": matched["id"],
            "player_name": matched["name"],
        }
    )


@never_cache
def export_replay(request, code):
    """Download complete reproducible JSON replay of the Codenames match."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    replay_data = export_game_replay(state)
    response = JsonResponse(replay_data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="codenames_replay_{code.lower()}.json"'
    return response

"""Views for Emojinary gameplay, QR code join, personal player reconnect, and replay export."""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.models import Room
from gamerooms.qr import build_public_url, generate_qr_data_uri

from .game_state import (
    SETTINGS_PRESETS,
    add_player,
    export_game_replay,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)


def emojinary_index(request):
    return redirect("gamerooms:room-list")


@never_cache
def room_join_redirect(request, code):
    """Redirect short /games/emojinary/<code>/ links to the room join page or active player session."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    token = request.GET.get("token") or request.session.get(f"emojinary_player_{code}")
    existing = find_player_by_token(state, token)
    if existing and not request.GET.get("new"):
        return redirect("gamerooms:emojinary:game", code=code, name=existing["name"])
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

    token = request.GET.get("token") or request.session.get(f"emojinary_player_{code}")
    is_admin = bool(request.session.get(f"emojinary_admin_{code}"))

    # If the user already has a valid player token in this room, keep their identity
    # (and if the URL name differs from their current stored name, prefer their stored name unless ?rename=1)
    existing = find_player_by_token(state, token)
    if existing:
        player = existing
        if is_admin:
            player["is_admin"] = True
            save_game(code, state)
    else:
        state, player, _ = add_player(
            state,
            name=name,
            token=token,
            is_admin=is_admin,
        )

    request.session[f"emojinary_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"emojinary_admin_{code}"] = True

    # Build Room Invite QR URL (with embedded ?pwd= if room has password)
    join_path = reverse("gamerooms:room-join", kwargs={"code": code})
    join_params = {"pwd": room.password} if room.has_password else None
    join_url = build_public_url(request, join_path, join_params)
    join_qr = generate_qr_data_uri(join_url)

    # Build Personal Player Reconnect QR URL
    reconnect_path = reverse("gamerooms:emojinary:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    player_qr_uri = generate_qr_data_uri(reconnect_url)

    initial_state = get_sanitized_player_view(state, player["id"])

    return render(
        request,
        "emojinary/game.html",
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
            "presets": SETTINGS_PRESETS,
            "initial_state_json": json.dumps(initial_state),
        },
    )


@never_cache
def player_reconnect(request, code, token):
    """Direct URL or scanned QR code for a player to seamlessly reconnect on any device."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    matched = find_player_by_token(state, token)
    if not matched:
        raise Http404("Invalid player reconnect token.")

    request.session[f"room_{code}"] = True
    request.session[f"emojinary_player_{code}"] = token
    if matched.get("is_admin"):
        request.session[f"emojinary_admin_{code}"] = True

    game_url = reverse("gamerooms:emojinary:game", kwargs={"code": code, "name": matched["name"]})
    return redirect(f"{game_url}?token={token}")


@never_cache
def player_qr(request, code, token):
    """Return JSON with data-URI QR code and reconnect URL for a player."""
    code = code.upper()
    reconnect_path = reverse("gamerooms:emojinary:reconnect", kwargs={"code": code, "token": token})
    reconnect_url = build_public_url(request, reconnect_path)
    qr_data_uri = generate_qr_data_uri(reconnect_url)
    return JsonResponse({"qr": qr_data_uri, "url": reconnect_url})


@never_cache
def export_replay(request, code):
    """Download complete reproducible JSON replay of the Emojinary match."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404("Game not found.")
    replay_data = export_game_replay(state)
    response = JsonResponse(replay_data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="emojinary_replay_{code.lower()}.json"'
    return response

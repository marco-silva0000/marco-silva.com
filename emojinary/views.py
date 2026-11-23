"""Views for Emojinary gameplay, QR code join, personal player reconnect, and replay export."""

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.qr import build_public_url, generate_qr_data_uri, get_room_share_urls
from gamerooms.security import safe_json_dumps
from gamerooms.views import legacy_game_redirect

from .game_state import (
    SETTINGS_PRESETS,
    add_player,
    export_game_replay,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)


def emojinary_index(request):
    return redirect("gamerooms:room-list")


@never_cache
def game_play(request, code):
    """Modern clean-URL game view (/games/emojinary/<CODE>/play/ or /games/emojinary/<CODE>/)."""
    code = code.upper()
    room = get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    state["title"] = room.title
    state["password"] = room.password
    state["language"] = getattr(room, "language", "en") or "en"

    token = request.GET.get("token") or request.session.get(f"emojinary_player_{code}")
    is_admin = bool(request.session.get(f"emojinary_admin_{code}") or request.session.get(f"admin_{code}"))

    player = None
    if token:
        existing = find_player_by_token(state, token)
        if existing:
            player = existing
            if is_admin:
                player["is_admin"] = True
                save_game(code, state)

    name = request.GET.get("name")
    if not player and name:
        by_name = find_player_by_name(state, name)
        if by_name and (is_admin or by_name.get("name") == room.creator or not by_name.get("connected", False)):
            player = by_name
            if is_admin:
                player["is_admin"] = True
            player["connected"] = True
            save_game(code, state)
        else:
            state, player, _ = add_player(
                state,
                name=name,
                token=token,
                is_admin=is_admin,
            )

    if not player:
        join_url = reverse("gamerooms:room-join", kwargs={"code": code})
        pwd = request.GET.get("pwd")
        if pwd:
            return redirect(f"{join_url}?pwd={pwd}")
        return redirect(join_url)

    request.session[f"emojinary_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"emojinary_admin_{code}"] = True

    share_urls = get_room_share_urls(request, room, "emojinary", player["token"])
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
            "presets": SETTINGS_PRESETS,
            "language_support": get_game_language_support("emojinary", state.get("language", "en")),
            "initial_state_json": safe_json_dumps(initial_state),
            **share_urls,
        },
    )


@never_cache
def game_with_name_redirect(request, code: str, name: str):
    """Backwards-compatible redirect for legacy /games/emojinary/<CODE>/<name>/ paths."""
    return legacy_game_redirect(request, code, name, "emojinary")


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

    play_url = reverse("gamerooms:emojinary:play", kwargs={"code": code})
    return redirect(f"{play_url}?token={token}")


@never_cache
def player_qr(request, code, token):
    """Return JSON with data-URI QR code and reconnect URL for a player."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    matched = state.get("players", {}).get(token) or find_player_by_token(state, token)
    if not matched:
        raise Http404("Player not found in this room.")
    reconnect_path = reverse(
        "gamerooms:emojinary:reconnect",
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
    """Download complete reproducible JSON replay of the Emojinary match."""
    code = code.upper()
    state = get_game(code)
    if not state:
        raise Http404("Game not found.")
    replay_data = export_game_replay(state)
    response = JsonResponse(replay_data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="emojinary_replay_{code.lower()}.json"'
    return response

"""Views for SmartN gameplay, QR codes, and seat reconnects."""

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.player_colors import PLAYER_PALETTE
from gamerooms.qr import build_public_url, generate_qr_data_uri, get_room_share_urls
from gamerooms.security import safe_json_dumps
from gamerooms.views import legacy_game_redirect

from .game_state import (
    DEFAULT_SETTINGS,
    PACK_CHOICES,
    add_player,
    find_player_by_id,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)


@never_cache
def game_play(request, code):
    """Modern clean-URL game view (/games/smartn/<CODE>/play/ or /games/smartn/<CODE>/)."""
    code = code.upper()
    room = get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)

    query_token = request.GET.get("token")
    session_token = request.session.get(f"smartn_player_{code}")
    token = query_token or session_token
    session_admin = bool(request.session.get(f"smartn_admin_{code}") or request.session.get(f"admin_{code}"))

    player = None
    if token:
        existing = find_player_by_token(state, token) if state else None
        if existing:
            player = existing
            if session_admin:
                player["is_admin"] = True
            save_game(code, state)

    name = request.GET.get("name")
    if not player and name:
        by_name = find_player_by_name(state, name) if state else None
        grant_admin = session_admin or (not state or not state.get("players"))
        if by_name and (session_admin or not by_name.get("connected", False)):
            player = by_name
            if grant_admin:
                player["is_admin"] = True
            save_game(code, state)
        else:
            state, player, _ = add_player(
                code_or_state=state or code,
                name=name,
                token=token,
                is_admin=grant_admin,
            )

    if not player:
        join_url = reverse("gamerooms:room-join", kwargs={"code": code})
        pwd = request.GET.get("pwd")
        if pwd:
            return redirect(f"{join_url}?pwd={pwd}")
        return redirect(join_url)

    request.session[f"smartn_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"smartn_admin_{code}"] = True

    share_urls = get_room_share_urls(request, room, "smartn", player["token"])
    sanitized_state = get_sanitized_player_view(state, viewer_id=player["id"])
    lang_support = get_game_language_support("smartn", getattr(room, "language", "en"))

    context = {
        "room": room,
        "player": player,
        "initial_state_json": safe_json_dumps(sanitized_state),
        "pack_choices": PACK_CHOICES,
        "player_palette": PLAYER_PALETTE,
        "default_settings": DEFAULT_SETTINGS,
        "language_support": lang_support,
        **share_urls,
    }
    return render(request, "smartn/game.html", context)


@never_cache
def game_with_name_redirect(request, code: str, name: str):
    """Backwards-compatible redirect for legacy /games/smartn/<CODE>/<name>/ paths."""
    return legacy_game_redirect(request, code, name, "smartn")


@never_cache
def player_qr(request, code, token):
    """Serve a personalized QR code for a player to seamlessly reconnect."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    player = find_player_by_token(state, token) if state else None
    if not player and state:
        player = find_player_by_id(state, token)

    if not player:
        raise Http404("Player seat not found.")

    reconnect_path = reverse("gamerooms:smartn:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    qr_data_uri = generate_qr_data_uri(reconnect_url)

    return JsonResponse(
        {
            "player_id": player["id"],
            "player_name": player["name"],
            "player_color": player.get("color", "#3b82f6"),
            "url": reconnect_url,
            "qr": qr_data_uri,
        }
    )


@never_cache
def player_reconnect(request, code, token):
    """Resume an existing player's seat via personalized token."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    player = find_player_by_token(state, token) if state else None
    if not player and state:
        player = find_player_by_id(state, token)

    if not player:
        return redirect("gamerooms:room-join", code=code)

    request.session[f"smartn_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"smartn_admin_{code}"] = True

    play_url = reverse("gamerooms:smartn:play", kwargs={"code": code})
    return redirect(f"{play_url}?token={player['token']}")

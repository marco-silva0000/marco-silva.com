"""Views for Secret Santa & Target Matcher room orchestration, clean URLs, and QR codes."""

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.player_colors import PLAYER_PALETTE
from gamerooms.qr import build_public_url, generate_qr_data_uri
from gamerooms.security import safe_json_dumps

from .game_state import (
    DEFAULT_SETTINGS,
    THEMES,
    add_player,
    create_game,
    find_player_by_id,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)


@never_cache
def game_play(request, code: str):
    """Clean-URL game view (/games/secretsanta/<CODE>/play/ or /games/secretsanta/<CODE>/)."""
    code = code.upper()
    room = get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    if not state:
        state = create_game(code, title=room.title)

    query_token = request.GET.get("token")
    session_token = request.session.get(f"secretsanta_player_{code}")
    token = query_token or session_token
    session_admin = bool(request.session.get(f"secretsanta_admin_{code}"))

    player = None
    if token:
        player = find_player_by_token(state, token)
        if player:
            player["connected"] = True
            if session_admin:
                player["is_admin"] = True
            save_game(code, state)

    name = request.GET.get("name") or request.session.get(f"pending_secretsanta_name_{code}")
    if not player and name:
        by_name = find_player_by_name(state, name)
        grant_admin = session_admin or (not state.get("players"))
        if by_name and (session_admin or not by_name.get("connected", False)):
            player = by_name
            player["connected"] = True
            if grant_admin:
                player["is_admin"] = True
            save_game(code, state)
        else:
            state, player, _ = add_player(
                state=state,
                name=name,
                token=token,
                is_admin=grant_admin,
                is_offline=False,
            )

    if not player:
        join_url = reverse("gamerooms:room-join", kwargs={"code": code})
        pwd = request.GET.get("pwd")
        if pwd:
            return redirect(f"{join_url}?pwd={pwd}")
        return redirect(join_url)

    request.session[f"secretsanta_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"secretsanta_admin_{code}"] = True

    # Room Join link & QR code for inviting friends
    join_path = reverse("gamerooms:room-join", kwargs={"code": room.code})
    join_url = build_public_url(request, join_path)
    if room.has_password and room.password:
        join_url = f"{join_url}?pwd={room.password}"
    join_qr = generate_qr_data_uri(join_url)

    # Personal seat reconnect URL (for bookmarking only)
    reconnect_path = reverse("gamerooms:secretsanta:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    reconnect_qr = generate_qr_data_uri(reconnect_url)

    sanitized_state = get_sanitized_player_view(state, viewer_id=player["id"])
    lang_support = get_game_language_support("secretsanta", getattr(room, "language", "en"))

    context = {
        "room": room,
        "player": player,
        "initial_state_json": safe_json_dumps(sanitized_state),
        "player_palette": PLAYER_PALETTE,
        "themes": THEMES,
        "default_settings": DEFAULT_SETTINGS,
        "language_support": lang_support,
        "join_url": join_url,
        "join_qr": join_qr,
        "reconnect_url": reconnect_url,
        "reconnect_qr": reconnect_qr,
    }
    return render(request, "secretsanta/game.html", context)


@never_cache
def game_with_name_redirect(request, code: str, name: str):
    """Legacy alias redirecting /games/secretsanta/<CODE>/<name>/ to clean /games/secretsanta/<CODE>/play/."""
    code = code.upper()
    query_token = request.GET.get("token")
    query_str = f"?token={query_token}&name={name}" if query_token else f"?name={name}"
    return redirect(f"{reverse('gamerooms:secretsanta:game-play', kwargs={'code': code})}{query_str}")


@never_cache
def player_qr(request, code: str, token: str):
    """Serve a personalized QR code for a participant to bookmark or reconnect."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    player = find_player_by_token(state, token) if state else None
    if not player and state:
        player = find_player_by_id(state, token)

    if not player:
        raise Http404("Player seat not found.")

    reconnect_path = reverse("gamerooms:secretsanta:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    qr_data_uri = generate_qr_data_uri(reconnect_url)

    return JsonResponse(
        {
            "player_id": player["id"],
            "player_name": player["name"],
            "player_color": player.get("color", "#ef4444"),
            "url": reconnect_url,
            "qr": qr_data_uri,
        }
    )


@never_cache
def player_reconnect(request, code: str, token: str):
    """Resume an existing player's seat via personalized token."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    player = find_player_by_token(state, token) if state else None
    if not player and state:
        player = find_player_by_id(state, token)

    if not player:
        return redirect("gamerooms:room-join", code=code)

    request.session[f"secretsanta_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"secretsanta_admin_{code}"] = True

    return redirect(f"{reverse('gamerooms:secretsanta:game-play', kwargs={'code': code})}?token={player['token']}")

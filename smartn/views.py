"""Views for SmartN gameplay, QR codes, and seat reconnects."""

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
def room_join_redirect(request, code):
    """Redirect short /games/smartn/<code>/ links to existing player session or room join."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    token = request.GET.get("token") or request.session.get(f"smartn_player_{code}")
    existing = find_player_by_token(state, token) if state else None
    if existing and not request.GET.get("new"):
        return redirect("gamerooms:smartn:game", code=code, name=existing["name"])
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

    query_token = request.GET.get("token")
    session_token = request.session.get(f"smartn_player_{code}")
    token = query_token or session_token
    session_admin = bool(request.session.get(f"smartn_admin_{code}"))

    existing = find_player_by_token(state, token) if state else None
    if existing:
        player = existing
        if session_admin:
            player["is_admin"] = True
        save_game(code, state)
    else:
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

    request.session[f"smartn_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"smartn_admin_{code}"] = True

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
    }
    return render(request, "smartn/game.html", context)


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

    return redirect("gamerooms:smartn:game", code=code, name=player["name"])

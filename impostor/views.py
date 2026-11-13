"""Views for Advanced Word Impostor gameplay and personal player reconnects."""

import json

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.qr import build_public_url, generate_qr_data_uri

from .game_state import (
    DEFAULT_SETTINGS,
    POISON_MODES,
    add_player,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)
from .word_pairs import CATEGORIES


@never_cache
def room_join_redirect(request, code):
    """Redirect short /games/impostor/<code>/ links to existing player session or room join."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    token = request.GET.get("token") or request.session.get(f"impostor_player_{code}")
    existing = find_player_by_token(state, token)
    if existing and not request.GET.get("new"):
        return redirect("gamerooms:impostor:game", code=code, name=existing["name"])
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

    token = request.GET.get("token") or request.session.get(f"impostor_player_{code}")
    is_admin = bool(request.session.get(f"impostor_admin_{code}"))

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

    request.session[f"impostor_player_{code}"] = player["token"]
    if player.get("is_admin"):
        request.session[f"impostor_admin_{code}"] = True

    join_path = reverse("gamerooms:room-join", kwargs={"code": code})
    join_params = {"pwd": room.password} if room.has_password else None
    join_url = build_public_url(request, join_path, join_params)
    join_qr = generate_qr_data_uri(join_url)

    reconnect_path = reverse("gamerooms:impostor:reconnect", kwargs={"code": code, "token": player["token"]})
    reconnect_url = build_public_url(request, reconnect_path)
    player_qr_uri = generate_qr_data_uri(reconnect_url)

    initial_state = get_sanitized_player_view(state, player["id"])
    language_support = get_game_language_support("impostor", state.get("language", "en"))

    return render(
        request,
        "impostor/game.html",
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
            "poison_modes": POISON_MODES,
            "categories": CATEGORIES,
            "default_settings": DEFAULT_SETTINGS,
            "language_support": language_support,
            "initial_state_json": json.dumps(initial_state),
        },
    )


@never_cache
def player_reconnect(request, code, token):
    """Reconnect link for switching devices mid-match."""
    code = code.upper()
    get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    matched = find_player_by_token(state, token)
    if not matched:
        raise Http404("Invalid player reconnect token.")

    request.session[f"room_{code}"] = True
    request.session[f"impostor_player_{code}"] = token
    if matched.get("is_admin"):
        request.session[f"impostor_admin_{code}"] = True

    game_url = reverse("gamerooms:impostor:game", kwargs={"code": code, "name": matched["name"]})
    return redirect(f"{game_url}?token={token}")

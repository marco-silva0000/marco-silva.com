"""Views for Stop! gameplay, QR codes, and personal player reconnects."""

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from gamerooms.qr import build_public_url, generate_qr_data_uri, get_room_share_urls
from gamerooms.security import safe_json_dumps
from gamerooms.views import legacy_game_redirect

from .categories import CATEGORY_PACKS, DB_CATEGORIES, WEB_PARTY_CATEGORIES
from .game_state import (
    CLASH_RULES,
    DEFAULT_SETTINGS,
    STOP_MODES,
    add_player,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    save_game,
)


@never_cache
def game_play(request, code):
    """Modern clean-URL game view (/games/stop/<CODE>/play/ or /games/stop/<CODE>/)."""
    code = code.upper()
    room = get_object_or_404(Room, code=code, is_active=True)
    state = get_game(code)
    state["title"] = room.title
    state["password"] = room.password
    state["language"] = getattr(room, "language", "en") or "en"

    query_token = request.GET.get("token")
    session_token = request.session.get(f"stop_player_{code}")
    token = query_token or session_token
    session_admin = bool(request.session.get(f"stop_admin_{code}") or request.session.get(f"admin_{code}"))

    player = None
    if token:
        existing = find_player_by_token(state, token)
        if existing:
            player = existing
            if session_admin and (not state.get("creator_id") or player.get("id") == state.get("creator_id")):
                player["is_admin"] = True
            save_game(code, state)

    name = request.GET.get("name")
    if not player and name:
        by_name = find_player_by_name(state, name)
        if by_name and (session_admin or not query_token or by_name.get("id") == state.get("creator_id")):
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

    if not player:
        join_url = reverse("gamerooms:room-join", kwargs={"code": code})
        pwd = request.GET.get("pwd")
        if pwd:
            return redirect(f"{join_url}?pwd={pwd}")
        return redirect(join_url)

    request.session[f"stop_player_{code}"] = player["token"]
    if player.get("is_admin") and (not query_token or player.get("id") == state.get("creator_id")):
        request.session[f"stop_admin_{code}"] = True

    share_urls = get_room_share_urls(request, room, "stop", player["token"])
    initial_state = get_sanitized_player_view(state, player["id"])
    language_support = get_game_language_support("stop", state.get("language", "en"))

    return render(
        request,
        "stop/game.html",
        {
            "room": room,
            "player": player,
            "player_name": player["name"],
            "player_id": player["id"],
            "player_token": player["token"],
            "admin_token": state.get("admin_token", "") if player.get("is_admin") else "",
            "category_packs": CATEGORY_PACKS,
            "stop_modes": STOP_MODES,
            "clash_rules": CLASH_RULES,
            "db_categories_count": len(DB_CATEGORIES),
            "web_categories_count": len(WEB_PARTY_CATEGORIES),
            "default_settings": DEFAULT_SETTINGS,
            "language_support": language_support,
            "initial_state_json": safe_json_dumps(initial_state),
            **share_urls,
        },
    )


@never_cache
def game_with_name_redirect(request, code: str, name: str):
    """Backwards-compatible redirect for legacy /games/stop/<CODE>/<name>/ paths."""
    return legacy_game_redirect(request, code, name, "stop")


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
    existing_session_token = request.session.get(f"stop_player_{code}")
    existing_session_admin = bool(request.session.get(f"stop_admin_{code}"))
    if not existing_session_token or (matched.get("is_admin") and not existing_session_admin):
        request.session[f"stop_player_{code}"] = token
    if matched.get("is_admin"):
        request.session[f"stop_admin_{code}"] = True

    play_url = reverse("gamerooms:stop:play", kwargs={"code": code})
    return redirect(f"{play_url}?token={token}")


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
        "gamerooms:stop:reconnect",
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

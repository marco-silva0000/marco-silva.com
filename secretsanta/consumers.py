"""WebSocket consumer for real-time Secret Santa & Target Matcher."""

import logging
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    add_offline_player,
    add_player,
    append_event,
    change_player_color,
    create_game,
    find_player_by_id,
    find_player_by_name,
    find_player_by_token,
    generate_matches,
    get_game,
    get_sanitized_player_view,
    is_player_admin,
    remove_player,
    reset_to_lobby,
    reveal_all_admin,
    save_game,
    set_player_exclusions,
    update_settings,
    update_wishlist,
)

logger = logging.getLogger(__name__)


class SecretSantaConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler consumer for Secret Santa & Target Matcher."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: str | None = None
        self.player_name: str | None = None
        self.player_token: str | None = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"secretsanta_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        state = get_game(self.code)
        if state and self.player_id:
            player = find_player_by_id(state, self.player_id)
            if player:
                player["connected"] = False
                save_game(self.code, state)
                await self.broadcast_sync()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _is_admin(self, state: dict[str, Any] | None) -> bool:
        if not state or not self.player_id:
            return False
        p = find_player_by_id(state, self.player_id)
        return is_player_admin(state, p)

    async def receive_json(self, content: dict[str, Any]):
        action = content.get("action")
        state = get_game(self.code)

        if action == "join":
            await self._handle_join(state, content)
            return

        if not self.player_id and state:
            token = content.get("token")
            existing = find_player_by_token(state, token) if token else None
            if not existing and content.get("name"):
                existing = find_player_by_name(state, content.get("name"))
            if existing:
                self.player_id = existing["id"]
                self.player_name = existing["name"]
                self.player_token = existing.get("token")

        if not state:
            return

        is_admin = self._is_admin(state)

        if action == "chat":
            text = (content.get("text") or "").strip()[:300]
            if text:
                sender = self.player_name or "Guest"
                p = find_player_by_id(state, self.player_id)
                color = p.get("color") if p else None
                initials = p.get("initials") if p else None
                append_event(
                    state,
                    sender=sender,
                    text=text,
                    kind="chat",
                    player_id=self.player_id,
                    color=color,
                    initials=initials,
                )
                save_game(self.code, state)
                await self.broadcast_sync()

        elif action == "update_wishlist":
            wishlist = content.get("wishlist", "")
            target_pid = content.get("player_id") or self.player_id
            # Non-admins can only update their own wishlist; admins can update couch players too
            if target_pid == self.player_id or is_admin:
                if target_pid:
                    update_wishlist(state, target_pid, wishlist)
                    await self.broadcast_sync()

        elif action == "change_color":
            target_pid = content.get("player_id") or self.player_id
            color = str(content.get("color") or "").strip()
            if color and (target_pid == self.player_id or is_admin):
                if target_pid:
                    change_player_color(state, target_pid, color)
                    await self.broadcast_sync()

        elif action == "set_exclusions":
            target_pid = content.get("player_id") or self.player_id
            excluded = content.get("excluded_ids", [])
            if target_pid == self.player_id or is_admin:
                if target_pid and isinstance(excluded, list):
                    set_player_exclusions(state, target_pid, excluded)
                    await self.broadcast_sync()

        elif action == "add_offline_player" and is_admin:
            name = (content.get("name") or "").strip()
            if name:
                add_offline_player(state, name, added_by_name=self.player_name or "Host")
                await self.broadcast_sync()

        elif action == "remove_player":
            target_pid = content.get("player_id")
            if target_pid and (target_pid == self.player_id or is_admin):
                remove_player(state, target_pid)
                await self.broadcast_sync()

        elif action == "update_settings" and is_admin:
            settings_data = content.get("settings", {})
            if isinstance(settings_data, dict):
                update_settings(state, settings_data)
                append_event(
                    state,
                    "System",
                    "⚙️ Room settings updated.",
                    kind="system",
                )
                save_game(self.code, state)
                await self.broadcast_sync()

        elif action == "generate_matches" and is_admin:
            ok, msg = generate_matches(state)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "reset_to_lobby" and is_admin:
            reset_to_lobby(state)
            await self.broadcast_sync()

        elif action == "reveal_all_admin" and is_admin:
            if self.player_id:
                ok, res = reveal_all_admin(state, self.player_id)
                if ok:
                    await self.send_json({"type": "master_reveal", "matches": res})
                else:
                    await self.send_json({"type": "error", "message": str(res)})

        elif action == "sync":
            await self.send_state_to_self(state)

    async def _handle_join(self, state: dict[str, Any] | None, content: dict[str, Any]):
        if not state:
            state = create_game(self.code)

        name = (content.get("name") or "").strip()
        token = content.get("token")
        is_admin = bool(content.get("is_admin"))

        state, player, is_new = add_player(
            state=state,
            name=name or "Participant",
            token=token,
            is_admin=is_admin,
            is_offline=False,
        )

        self.player_id = player["id"]
        self.player_name = player["name"]
        self.player_token = player["token"]

        if is_new:
            append_event(
                state,
                "System",
                f"👋 {player['name']} joined the room.",
                kind="system",
            )
            save_game(self.code, state)

        await self.broadcast_sync()

    async def broadcast_sync(self):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "sync_state",
            },
        )

    async def sync_state(self, event):
        state = get_game(self.code)
        if state:
            await self.send_state_to_self(state)

    async def send_state_to_self(self, state: dict[str, Any]):
        view = get_sanitized_player_view(state, viewer_id=self.player_id)
        await self.send_json({"type": "state", "state": view})

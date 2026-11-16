"""WebSocket consumer for real-time 'Don't Say the Same Thing as Me' gameplay."""

import time
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    add_player,
    advance_next_round,
    append_event,
    evaluate_and_reveal_round,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    is_player_admin,
    kick_player,
    reset_game,
    save_game,
    start_game,
    submit_answer,
    toggle_answer_validity,
    toggle_spectator,
    update_settings,
)


class DontSayConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler anti-hivemind consumer for 'Don't Say the Same Thing as Me'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: Optional[str] = None
        self.player_token: Optional[str] = None
        self.player_name: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"dontsay_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        state = get_game(self.code)
        player = state.get("players", {}).get(self.player_id) if self.player_id else None
        if player:
            player["connected"] = False
            if player.get("channel_name") == self.channel_name:
                player["channel_name"] = None
            save_game(self.code, state)
            await self.broadcast_sync()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _is_admin(self, state: dict) -> bool:
        if not self.player_id:
            return False
        player = state.get("players", {}).get(self.player_id)
        return is_player_admin(state, player)

    async def broadcast_sync(self):
        await self.channel_layer.group_send(self.group_name, {"type": "dontsay.state.sync"})

    async def send_state_to_self(self, state: Optional[dict] = None):
        if state is None:
            state = get_game(self.code)
        await self.send_json(get_sanitized_player_view(state, self.player_token or self.player_id))

    async def send_error(self, msg: str):
        await self.send_json({"type": "error", "msg": msg})

    async def dontsay_state_sync(self, event):
        state = get_game(self.code)
        if not state:
            return
        if self.player_id and self.player_id in state.get("players", {}):
            self.player_name = state["players"][self.player_id].get("name", self.player_name)
        await self.send_state_to_self(state)

    async def receive_json(self, content):
        action = content.get("action")
        state = get_game(self.code)

        if action == "join":
            await self._handle_join(state, content)
            return

        if not self.player_id or self.player_id not in state.get("players", {}):
            await self.send_error("You must join the room before performing actions.")
            return

        if action == "chat":
            await self._handle_chat(state, content)
        elif action == "update_settings":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can change room settings.")
            update_settings(state, content.get("settings") or content)
            await self.broadcast_sync()
        elif action == "toggle_spectator":
            target_id = content.get("player_id") or self.player_id
            if target_id != self.player_id and not self._is_admin(state):
                return await self.send_error("Only the Host can toggle other players' spectator mode.")
            toggle_spectator(state, target_id)
            await self.broadcast_sync()
        elif action == "kick_player":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can kick players.")
            target_id = str(content.get("player_id", ""))
            if target_id == self.player_id:
                return await self.send_error("Host cannot kick themselves.")
            kick_player(state, target_id, by_name=self.player_name or "Host")
            await self.broadcast_sync()
        elif action == "start_game":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can start the game.")
            start_game(state)
            await self.broadcast_sync()
        elif action == "submit_answer":
            answer = str(content.get("answer", ""))
            submit_answer(state, self.player_id, answer)
            await self.broadcast_sync()
        elif action == "reveal_round":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can trigger early reveal.")
            evaluate_and_reveal_round(state)
            await self.broadcast_sync()
        elif action == "toggle_validity":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can arbitrate answer validity.")
            target_pid = str(content.get("player_id", ""))
            is_valid = bool(content.get("is_valid", True))
            toggle_answer_validity(state, target_pid, is_valid)
            await self.broadcast_sync()
        elif action == "next_round":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can advance to the next round.")
            advance_next_round(state)
            await self.broadcast_sync()
        elif action == "reset_game":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can reset the game.")
            reset_game(state)
            await self.broadcast_sync()

    async def _handle_join(self, state: dict, content: dict):
        raw_name = (content.get("name") or "Player").strip()
        token = content.get("token")
        admin_token = content.get("admin_token")
        is_admin = bool(admin_token and admin_token == state.get("admin_token"))

        state, player, _ = add_player(
            state,
            name=raw_name,
            token=token,
            is_admin=is_admin,
            channel_name=self.channel_name,
        )
        self.player_id = player["id"]
        self.player_token = player["token"]
        self.player_name = player["name"]
        await self.send_state_to_self(state)
        await self.broadcast_sync()

    async def _handle_chat(self, state: dict, content: dict):
        msg = " ".join(str(content.get("msg") or "").strip().split())[:200]
        if not msg:
            return
        append_event(state, self.player_name or "Player", f"💬 {msg}")
        save_game(self.code, state)
        await self.broadcast_sync()

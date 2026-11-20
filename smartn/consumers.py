"""WebSocket consumer for real-time SmartN (Smart 10 Trivia) gameplay."""

import logging
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from gamerooms.models import create_user_prompt_suggestion
from smartn.game_state import (
    add_player,
    append_event,
    change_player_color,
    find_player_by_id,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    host_arbitrate,
    kick_player,
    next_round,
    pass_turn,
    pick_capsule,
    process_chat_answer,
    reset_game,
    save_game,
    set_player_connection,
    start_game,
    transfer_host,
    update_settings,
)

logger = logging.getLogger(__name__)


class SmartNConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler consumer for SmartN."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: str | None = None
        self.player_name: str | None = None
        self.player_token: str | None = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"smartn_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.player_id:
            set_player_connection(self.code, self.player_id, False)
            await self.broadcast_sync()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _is_admin(self, state: dict[str, Any] | None) -> bool:
        if not state or not self.player_id:
            return False
        p = find_player_by_id(state, self.player_id)
        return bool(p and p.get("is_admin"))

    async def receive_json(self, content: dict[str, Any]):
        action = content.get("action")
        state = get_game(self.code)

        if action == "join":
            await self._handle_join(state, content)
            return

        # Attempt reconnect resolution via token or name if player_id is missing
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
        is_single_device = state.get("settings", {}).get("mode") == "single_device"

        if action == "pick_capsule":
            slot = int(content.get("slot") or 0)
            prediction = content.get("prediction")
            ok, msg, new_state = pick_capsule(self.code, self.player_id or "", slot, prediction=prediction)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "pass_turn":
            ok, msg, new_state = pass_turn(self.code, self.player_id or "")
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "chat":
            msg = " ".join(str(content.get("msg") or "").strip().split())[:200]
            if msg and self.player_name:
                p = find_player_by_id(state, self.player_id)
                p_color = p.get("color") if p else None
                p_initials = p.get("initials") if p else None
                append_event(
                    state,
                    self.player_name,
                    msg,
                    kind="chat",
                    player_id=self.player_id,
                    color=p_color,
                    initials=p_initials,
                )
                save_game(self.code, state)

                # Try auto-answering from chat text
                if state.get("phase") == "playing":
                    matched_ok, _, _ = process_chat_answer(self.code, self.player_id or "", msg)
                    if matched_ok:
                        logger.info("Chat auto-matched answer from %s: '%s'", self.player_name, msg)

                await self.broadcast_sync()

        elif action == "host_arbitrate" and (is_admin or is_single_device):
            slot = int(content.get("slot") or 0)
            mark_correct = bool(content.get("mark_correct", True))
            target_pid = content.get("target_player_id") or self.player_id
            ok, msg, new_state = host_arbitrate(self.code, slot, mark_correct, target_player_id=target_pid)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "start_game" and is_admin:
            ok, msg, new_state = start_game(self.code)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "next_round" and (is_admin or is_single_device):
            ok, msg, new_state = next_round(self.code)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "reset_game" and is_admin:
            ok, msg, new_state = reset_game(self.code)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "update_settings" and is_admin:
            settings_dict = content.get("settings") or {}
            ok, msg, new_state = update_settings(self.code, settings_dict)
            if ok:
                await self.broadcast_sync()
            else:
                await self.send_json({"type": "error", "message": msg})

        elif action == "change_color":
            target_pid = (content.get("player_id") if is_admin else None) or self.player_id
            new_color = str(content.get("color") or "").strip()
            if target_pid and new_color:
                ok = change_player_color(self.code, target_pid, new_color)
                if ok:
                    await self.broadcast_sync()

        elif action == "kick_player" and is_admin:
            target_pid = str(content.get("player_id") or "").strip()
            if target_pid:
                ok, msg, new_state = kick_player(self.code, target_pid)
                if ok:
                    await self.broadcast_sync()
                else:
                    await self.send_json({"type": "error", "message": msg})

        elif action == "transfer_host" and is_admin:
            target_pid = str(content.get("new_host_id") or "").strip()
            if target_pid:
                ok, msg, new_state = transfer_host(self.code, target_pid)
                if ok:
                    await self.broadcast_sync()
                else:
                    await self.send_json({"type": "error", "message": msg})

        elif action == "suggest_prompt":
            await self._handle_suggest_prompt(content)

    async def _handle_join(self, state: dict[str, Any] | None, content: dict[str, Any]):
        name = str(content.get("name") or "Player").strip()[:30]
        token = content.get("token")
        is_admin = bool(content.get("is_admin"))
        color = content.get("color")

        state, player, is_new = add_player(
            code_or_state=state or self.code,
            name=name,
            token=token,
            is_admin=is_admin,
            color=color,
            channel_name=self.channel_name,
        )
        self.player_id = player["id"]
        self.player_token = player["token"]
        self.player_name = player["name"]
        await self.broadcast_sync()

    async def _handle_suggest_prompt(self, content: dict[str, Any]):
        text = str(content.get("text") or "").strip()
        pack = str(content.get("pack") or "mix").strip()
        sample_answers = content.get("sample_answers") or []

        ok, msg, prompt = await database_sync_to_async(create_user_prompt_suggestion)(
            text=text,
            domain=pack,
            game_type="smartn",
            sample_answers=sample_answers,
            submitter_name=self.player_name or "",
            submitter_room=self.code,
        )
        await self.send_json(
            {
                "type": "prompt_suggestion_ack",
                "success": ok,
                "message": msg,
                "prompt_id": prompt.prompt_id if prompt else None,
            }
        )

    async def broadcast_sync(self):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "sync_state",
            },
        )

    async def sync_state(self, event: dict[str, Any]):
        state = get_game(self.code)
        if not state:
            return
        view = get_sanitized_player_view(state, viewer_id=self.player_id)
        await self.send_json({"type": "state", "state": view})

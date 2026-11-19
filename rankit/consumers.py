"""WebSocket consumer for real-time 'Rank It!' (ito cooperative party game)."""

from typing import Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from gamerooms.models import create_user_prompt_suggestion

from .game_state import (
    add_player,
    append_event,
    change_player_color,
    get_game,
    get_sanitized_player_view,
    is_player_admin,
    kick_player,
    play_again,
    play_card,
    save_game,
    set_card_clue,
    start_level,
    transfer_host,
    update_settings,
)


class RankitConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler cooperative multiplayer consumer for Rank It!"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: Optional[str] = None
        self.player_name: Optional[str] = None
        self.player_token: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"rankit_{self.code}"
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
        p = state.get("players", {}).get(self.player_id)
        return is_player_admin(state, p)

    async def receive_json(self, content):
        action = content.get("action")
        state = get_game(self.code)

        if action == "join":
            await self._handle_join(state, content)
            return

        if not self.player_id and content.get("token"):
            for p in state.get("players", {}).values():
                if p.get("token") == content.get("token"):
                    self.player_id = p["id"]
                    self.player_name = p["name"]
                    self.player_token = p["token"]
                    break

        if action == "update_settings" and self._is_admin(state):
            update_settings(state, content.get("settings", {}))
            await self.broadcast_sync()

        elif action in ("start_game", "start_level") and self._is_admin(state):
            from_lvl = content.get("from_level")
            success = start_level(state, from_level=from_lvl)
            if success:
                await self.broadcast_sync()

        elif action == "change_color":
            target_pid = content.get("player_id") or self.player_id
            new_color = str(content.get("color") or "").strip()
            success = change_player_color(
                state,
                target_player_id=target_pid,
                new_color=new_color,
                requested_by_admin=self._is_admin(state),
                requester_player_id=self.player_id or "",
            )
            if success:
                await self.broadcast_sync()

        elif action == "set_clue" and self.player_id:
            card_id = content.get("card_id", "")
            clue = content.get("clue", "")
            if set_card_clue(state, self.player_id, card_id, clue):
                await self.broadcast_sync()

        elif action == "play_card" and self.player_id:
            card_id = content.get("card_id", "")
            ok, msg = play_card(state, self.player_id, card_id)
            await self.broadcast_sync()

        elif action == "chat":
            await self._handle_chat(state, content)

        elif action == "suggest_prompt":
            await self._handle_suggest_prompt(content)

        elif action == "play_again" and self._is_admin(state):
            play_again(state)
            await self.broadcast_sync()

        elif action == "kick_player" and self._is_admin(state):
            target_id = content.get("player_id")
            if target_id and target_id != self.player_id:
                kick_player(state, target_id)
                await self.broadcast_sync()

        elif action == "transfer_host" and self._is_admin(state):
            target_id = content.get("player_id")
            if target_id:
                transfer_host(state, target_id)
                await self.broadcast_sync()

    async def _handle_join(self, state: dict, content: dict):
        name = str(content.get("name") or "Player").strip()[:30]
        token = content.get("token")
        is_admin = bool(content.get("is_admin"))

        state, player, is_new = add_player(
            state=state,
            name=name,
            token=token,
            is_admin=is_admin,
            channel_name=self.channel_name,
        )
        self.player_id = player["id"]
        self.player_token = player["token"]
        self.player_name = player["name"]
        await self.broadcast_sync()

    async def _handle_chat(self, state: dict, content: dict):
        msg = " ".join(str(content.get("msg") or "").strip().split())[:200]
        if not msg:
            return
        append_event(state, self.player_name or "Player", f"💬 {msg}")
        save_game(self.code, state)
        await self.broadcast_sync()

    async def _handle_suggest_prompt(self, content: dict):
        text = str(content.get("text") or "").strip()
        low_desc = str(content.get("low_desc") or "").strip()
        high_desc = str(content.get("high_desc") or "").strip()
        domain = str(content.get("pack") or "mix").strip()

        combined_text = text
        sample_answers = []
        if low_desc:
            sample_answers.append(f"1: {low_desc}")
        if high_desc:
            sample_answers.append(f"100: {high_desc}")

        ok, msg, prompt = await database_sync_to_async(create_user_prompt_suggestion)(
            text=combined_text,
            domain=domain
            if domain in ("classic", "everyday", "superpowers", "food", "scary", "deep", "nsfw")
            else "mix",
            game_type="rankit",
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

    async def sync_state(self, event):
        state = get_game(self.code)
        await self.send_state_to_self(state)

    async def send_state_to_self(self, state: dict):
        view = get_sanitized_player_view(state, viewer_id=self.player_id)
        await self.send_json({"type": "state", "state": view})

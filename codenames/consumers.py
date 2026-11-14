"""WebSocket consumer for real-time Codenames Multiplayer."""

import time
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    add_custom_word,
    add_player,
    add_table_player,
    append_event,
    auto_balance_teams,
    end_match_early,
    end_turn,
    get_game,
    get_sanitized_player_view,
    guess_card,
    is_player_admin,
    join_team,
    kick_player,
    reset_to_lobby,
    save_game,
    set_phase_timer,
    start_round,
    submit_clue,
    toggle_spectator,
    update_settings,
)
from .words import is_clue_forbidden_on_board


class CodenamesConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler multiplayer consumer for Codenames."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: Optional[str] = None
        self.player_name: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"codenames_{self.code}"
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
        await self.channel_layer.group_send(self.group_name, {"type": "codenames.state.sync"})

    async def send_state_to_self(self, state: Optional[dict] = None):
        if state is None:
            state = get_game(self.code)
        await self.send_json(get_sanitized_player_view(state, self.player_id))

    async def send_error(self, msg: str):
        await self.send_json({"type": "error", "msg": msg})

    async def codenames_state_sync(self, event):
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
        elif action == "add_custom_word":
            if not state["settings"].get("allow_custom_deck", True) and not self._is_admin(state):
                return await self.send_error("Custom words are disabled in this room.")
            ok, msg = add_custom_word(state, state["players"][self.player_id], content.get("word", ""))
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "add_table_player":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can add oral/table players.")
            ok, msg = add_table_player(state, content.get("name", ""))
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "join_team":
            ok, msg = join_team(
                state,
                self.player_id,
                team=str(content.get("team", "")),
                role=str(content.get("role", "operative")),
                target_player_id=content.get("target_player_id"),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "auto_balance_teams":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can auto-balance teams.")
            ok, msg = auto_balance_teams(state)
            if not ok:
                return await self.send_error(msg)
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
            target_id = content.get("player_id")
            if target_id == self.player_id:
                return await self.send_error("Host cannot kick themselves.")
            if kick_player(state, target_id, by_name=self.player_name or "Host"):
                await self.broadcast_sync()
        elif action in ("start_game", "next_round"):
            if not self._is_admin(state):
                return await self.send_error("Only the Host can start a Codenames board.")
            ok, msg = start_round(state, is_redraw=False)
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "blind_redraw":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can redraw the board.")
            ok, msg = start_round(state, is_redraw=True)
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "submit_clue":
            ok, msg = submit_clue(
                state,
                self.player_id,
                clue_word=content.get("clue", ""),
                clue_count=content.get("count", 1),
                by_mod=bool(content.get("by_mod", False)),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "guess_card":
            ok, msg = guess_card(
                state,
                self.player_id,
                card_index=content.get("index", -1),
                by_mod=bool(content.get("by_mod", False)),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "end_turn":
            ok, msg = end_turn(
                state,
                self.player_id,
                by_mod=bool(content.get("by_mod", False)),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "timer_control":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can control the timer.")
            cmd = content.get("command")
            now = time.time()
            if cmd == "pause" and state.get("timer_ends_at"):
                state["timer_paused_remaining"] = max(0, int(round(state["timer_ends_at"] - now)))
                state["timer_ends_at"] = None
            elif cmd == "resume" and state.get("timer_paused_remaining") is not None:
                rem = max(1, int(state["timer_paused_remaining"]))
                state["timer_paused_remaining"] = None
                state["timer_ends_at"] = now + rem
            elif cmd == "add":
                delta = int(content.get("seconds", 15))
                if state.get("timer_paused_remaining") is not None:
                    state["timer_paused_remaining"] += delta
                elif state.get("timer_ends_at"):
                    state["timer_ends_at"] += delta
                else:
                    set_phase_timer(state, delta)
            save_game(self.code, state)
            await self.broadcast_sync()
        elif action == "end_game":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can end the board.")
            end_match_early(state, by_name=self.player_name or "Host")
            await self.broadcast_sync()
        elif action == "play_again":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can return to Lobby.")
            reset_to_lobby(state)
            await self.broadcast_sync()

    async def _handle_join(self, state: dict, content: dict):
        raw_name = (content.get("name") or "Agent").strip()
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
        self.player_name = player["name"]
        await self.send_state_to_self(state)
        await self.broadcast_sync()

    async def _handle_chat(self, state: dict, content: dict):
        msg = " ".join(str(content.get("msg") or "").strip().split())[:200]
        if not msg:
            return
        # Guard Spymaster keycard spoilers in room chat during active play
        viewer = state.get("players", {}).get(self.player_id)
        if state.get("phase") == "playing" and viewer and viewer.get("role") == "spymaster":
            if any(w in msg.lower() for w in ("red", "blue", "assassin", "bystander")):
                for word in msg.split():
                    if is_clue_forbidden_on_board(word, state.get("board", [])):
                        msg = "🤐 [Possible board hint redacted]"
                        break
        append_event(state, self.player_name or "Agent", msg, kind="chat", sender_id=self.player_id)
        save_game(self.code, state)
        await self.broadcast_sync()

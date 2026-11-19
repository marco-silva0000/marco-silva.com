"""WebSocket consumer for real-time Stop! (Categories & Letter Speed Race)."""

import time
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    add_custom_category,
    add_player,
    append_event,
    call_stop,
    change_player_color,
    end_match,
    finish_round,
    get_game,
    get_sanitized_player_view,
    is_player_admin,
    kick_player,
    play_again,
    remove_custom_category,
    save_game,
    set_phase_timer,
    start_round,
    submit_answer,
    toggle_answer_validity,
    toggle_spectator,
    toggle_submission_clash,
    transfer_host,
    update_settings,
)


class StopConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler multiplayer consumer for Stop!"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: Optional[str] = None
        self.player_name: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"stop_{self.code}"
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
        await self.channel_layer.group_send(self.group_name, {"type": "stop.state.sync"})

    async def send_state_to_self(self, state: Optional[dict] = None):
        if state is None:
            state = get_game(self.code)
        await self.send_json(get_sanitized_player_view(state, self.player_id))

    async def send_error(self, msg: str):
        await self.send_json({"type": "error", "msg": msg})

    async def stop_state_sync(self, event):
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
        elif action == "change_color":
            target_pid = content.get("player_id") or self.player_id
            new_color = str(content.get("color") or "").strip()
            ok = change_player_color(
                state,
                target_player_id=target_pid,
                new_color=new_color,
                requested_by_admin=self._is_admin(state),
                requester_player_id=self.player_id or "",
            )
            if ok:
                await self.broadcast_sync()
        elif action == "update_settings":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can change room settings.")
            update_settings(state, content.get("settings") or content)
            await self.broadcast_sync()
        elif action == "add_custom_category":
            if not state["settings"].get("allow_custom_categories", True) and not self._is_admin(state):
                return await self.send_error("Custom categories are disabled in this room.")
            player = state["players"][self.player_id]
            ok, msg = add_custom_category(state, author=player, title=content.get("title", ""))
            if not ok:
                return await self.send_error(msg)
            try:
                from channels.db import database_sync_to_async

                from gamerooms.models import create_user_prompt_suggestion

                await database_sync_to_async(create_user_prompt_suggestion)(
                    text=content.get("title", ""),
                    domain="custom",
                    game_type="stop",
                    submitter_name=player.get("name", "Player"),
                    submitter_room=self.room_code,
                )
            except Exception:
                pass
            await self.broadcast_sync()
        elif action == "suggest_prompt":
            text = (content.get("text") or "").strip()
            domain = content.get("domain", "custom")
            sample_answers = content.get("sample_answers", [])
            player = state["players"].get(self.player_id, {})
            from channels.db import database_sync_to_async

            from gamerooms.models import create_user_prompt_suggestion

            ok, msg, _ = await database_sync_to_async(create_user_prompt_suggestion)(
                text=text,
                domain=domain,
                game_type="stop",
                sample_answers=sample_answers,
                submitter_name=player.get("name") or self.player_name or "Player",
                submitter_room=self.room_code,
            )
            if ok:
                await self.send_json(
                    {
                        "type": "prompt_suggestion_ack",
                        "success": True,
                        "message": (
                            "💡 Category submitted for review! It has been queued in the deck curation dashboard."
                        ),
                    }
                )
            else:
                return await self.send_error(msg)
        elif action == "remove_custom_category":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can remove custom categories.")
            if remove_custom_category(state, str(content.get("category_id", ""))):
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
            removed = kick_player(state, target_id, by_name=self.player_name or "Host")
            if removed:
                await self.broadcast_sync()
        elif action == "transfer_host":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can transfer room ownership.")
            target_id = content.get("target_id") or content.get("player_id")
            if target_id and transfer_host(state, target_id):
                await self.broadcast_sync()
        elif action in ("start_game", "next_round"):
            if not self._is_admin(state):
                return await self.send_error("Only the Host can start or advance rounds.")
            from_round = content.get("from_round") or content.get("current_round")
            cur_round = int(state.get("round_num", 0))
            if from_round is not None and int(from_round) != cur_round:
                return  # Drop duplicate clicks from stale round
            max_rounds = int(state.get("settings", {}).get("max_rounds", 8))
            if action == "next_round" and max_rounds > 0 and cur_round >= max_rounds:
                end_match(state, by_name=self.player_name or "Host")
                await self.broadcast_sync()
                return
            ok, msg = start_round(
                state,
                is_redraw=False,
                forced_category=str(content.get("forced_category", "")),
                forced_letter=str(content.get("forced_letter", "")),
                from_round=from_round,
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "redraw_round":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can redraw the Category & Letter.")
            ok, msg = start_round(
                state,
                is_redraw=True,
                forced_category=str(content.get("forced_category", "")),
                forced_letter=str(content.get("forced_letter", "")),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "submit_answer":
            ok, msg = submit_answer(
                state,
                self.player_id,
                answer_text=content.get("answer", ""),
                call_stop_now=bool(content.get("call_stop", False)),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "call_stop":
            ok, msg = call_stop(state, self.player_id, reason=str(content.get("reason", "")))
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "round_timeout":
            if state.get("phase") == "playing":
                ends_at = state.get("timer_ends_at")
                if self._is_admin(state) or (ends_at and time.time() >= ends_at - 1.0):
                    finish_round(state, stopped_by="Timer", reason="⏰ Time's up!")
                    await self.broadcast_sync()
        elif action == "toggle_validity":
            ok, msg = toggle_answer_validity(
                state,
                self.player_id,
                target_pid=str(content.get("player_id", "")),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "toggle_clash":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can arbitrate collisions.")
            ok, msg = toggle_submission_clash(
                state,
                self.player_id,
                target_pid=str(content.get("player_id", "")),
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
                return await self.send_error("Only the Host can end the match.")
            end_match(state, by_name=self.player_name or "Host")
            await self.broadcast_sync()
        elif action == "play_again":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can restart the match.")
            play_again(state)
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
        self.player_name = player["name"]
        await self.send_state_to_self(state)
        await self.broadcast_sync()

    async def _handle_chat(self, state: dict, content: dict):
        msg = " ".join(str(content.get("msg") or "").strip().split())[:200]
        if not msg:
            return
        append_event(state, self.player_name or "Player", msg, kind="chat", sender_id=self.player_id)
        save_game(self.code, state)
        await self.broadcast_sync()

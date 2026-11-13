"""WebSocket consumer for real-time Advanced Word Impostor."""

import time
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    add_custom_pair,
    add_player,
    add_table_player,
    append_event,
    cast_vote,
    end_match,
    expire_last_chance,
    get_game,
    get_sanitized_player_view,
    is_player_admin,
    kick_player,
    resolve_voting,
    save_game,
    set_phase_timer,
    skip_current_turn,
    start_round,
    start_voting_phase,
    submit_clue,
    submit_steal_guess,
    toggle_spectator,
    update_settings,
)
from .word_pairs import text_matches_term


class ImpostorConsumer(AsyncJsonWebsocketConsumer):
    """Real-time zero-spoiler multiplayer consumer for Word Impostor."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: Optional[str] = None
        self.player_name: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"impostor_{self.code}"
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
        await self.channel_layer.group_send(self.group_name, {"type": "impostor.state.sync"})

    async def send_state_to_self(self, state: Optional[dict] = None):
        if state is None:
            state = get_game(self.code)
        await self.send_json(get_sanitized_player_view(state, self.player_id))

    async def send_error(self, msg: str):
        await self.send_json({"type": "error", "msg": msg})

    async def impostor_state_sync(self, event):
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
        elif action == "add_custom_pair":
            if not state["settings"].get("allow_custom_deck", True) and not self._is_admin(state):
                return await self.send_error("Custom Pair cards are disabled in this room.")
            player = state["players"][self.player_id]
            ok, msg = add_custom_pair(
                state,
                author=player,
                citizen_word=content.get("citizen_word", ""),
                poison_word=content.get("poison_word", ""),
                lethal_word=content.get("lethal_word", ""),
                category=content.get("category", "custom"),
            )
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
        elif action in ("start_game", "next_round"):
            if not self._is_admin(state):
                return await self.send_error("Only the Host can start or advance rounds.")
            max_rounds = int(state["settings"].get("max_rounds", 5))
            if state.get("phase") == "reveal" and state.get("round_num", 0) >= max_rounds:
                end_match(state, by_name=self.player_name or "Host")
                await self.broadcast_sync()
                return
            ok, msg = start_round(state, is_redraw=False)
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "blind_redraw":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can trigger Blind Redraw.")
            if state.get("phase") != "clue" or len(state.get("clues", [])) > 0:
                return await self.send_error("Blind Redraw is only available before any clues are given.")
            ok, msg = start_round(state, is_redraw=True)
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "submit_clue":
            ok, msg = submit_clue(
                state,
                self.player_id,
                clue_text=content.get("clue", ""),
                spoken=False,
                target_player_id=content.get("target_player_id"),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "spoken_clue":
            ok, msg = submit_clue(
                state,
                self.player_id,
                spoken=True,
                target_player_id=content.get("target_player_id"),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "skip_turn":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can skip turns.")
            if skip_current_turn(state, by_name=self.player_name or "Host"):
                await self.broadcast_sync()
        elif action == "start_voting":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can open voting early.")
            start_voting_phase(state)
            await self.broadcast_sync()
        elif action == "cast_vote":
            ok, msg = cast_vote(
                state,
                self.player_id,
                str(content.get("target_id", "")),
                on_behalf_of=content.get("voter_id"),
                auto_tally=bool(content.get("auto_tally", True)),
            )
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "tally_votes":
            if not self._is_admin(state):
                return await self.send_error("Only the Host can force-tally votes early.")
            resolve_voting(state)
            await self.broadcast_sync()
        elif action == "submit_steal_guess":
            ok, msg = submit_steal_guess(state, self.player_id, content.get("guess", ""))
            if not ok:
                return await self.send_error(msg)
            await self.broadcast_sync()
        elif action == "steal_timeout":
            if not self._is_admin(state) and self.player_id != state.get("impostor_id"):
                return await self.send_error("Not authorized to expire Last-Chance Steal.")
            expire_last_chance(state)
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
            for p in state.get("players", {}).values():
                p["score"] = 0
            state["round_num"] = 0
            state["phase"] = "lobby"
            state["status"] = "open"
            state["started"] = False
            state["current_pair"] = None
            state["clues"] = []
            state["votes"] = {}
            state["rounds_history"] = []
            append_event(state, "System", "🔄 Match reset back to Lobby!")
            save_game(self.code, state)
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
        pair = state.get("current_pair") or {}
        if state.get("phase") in ("clue", "voting", "last_chance") and pair:
            if text_matches_term(msg, pair.get("citizen_matches", [])) or text_matches_term(
                msg, pair.get("poison_matches", [])
            ):
                msg = "🤐 [Secret word redacted]"
        append_event(state, self.player_name or "Player", msg, kind="chat", sender_id=self.player_id)
        save_game(self.code, state)
        await self.broadcast_sync()

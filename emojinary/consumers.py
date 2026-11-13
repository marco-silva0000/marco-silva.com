"""WebSocket consumer for real-time Emojinary synchronization, unified chat/guessing, and host controls."""

import copy
import time
from typing import Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    DEFAULT_SETTINGS,
    SETTINGS_PRESETS,
    add_player,
    append_chat_event,
    censor_spoilers,
    current_player_id,
    find_player_by_channel,
    get_game,
    get_sanitized_player_view,
    kick_player,
    player_list,
    rename_player,
    save_game,
    sync_room_db_status,
    toggle_spectator,
    transfer_admin,
)
from .modes.best_guess import BestGuessMixin
from .modes.round_robin import RoundRobinMixin


class EmojinaryConsumer(RoundRobinMixin, BestGuessMixin, AsyncJsonWebsocketConsumer):
    """
    Game consumer supporting:
    - Persistent player identity (player_id + token) decoupled from ephemeral channel_name
    - Deterministic state synchronization (`game.state.sync`) + legacy event compatibility
    - Unified chat & guess stream with spoiler protection and attempt-level replay logging
    - Modes: round_robin, collective, best_guess
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str = ""
        self.group_name: str = ""
        self.player_id: Optional[str] = None
        self.player_name: Optional[str] = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"emojinary_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        state = get_game(self.code)
        player = None
        if self.player_id and self.player_id in state.get("players", {}):
            player = state["players"][self.player_id]
        else:
            player = find_player_by_channel(state, self.channel_name)

        if player:
            player["connected"] = False
            if player.get("channel_name") == self.channel_name:
                player["channel_name"] = None
            save_game(self.code, state)
            await self.broadcast_sync()

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _is_player_admin(self, state: dict) -> bool:
        if not self.player_id or self.player_id not in state.get("players", {}):
            return False
        p = state["players"][self.player_id]
        # Authorize by persistent identity only (never by display name, which is user-controlled)
        return bool(p.get("is_admin") or self.player_id == state.get("creator_id"))

    async def broadcast_sync(self):
        """Instruct all connected clients in the room to re-render their sanitized perspective."""
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "game.state.sync"},
        )

    async def send_state_to_self(self, state: Optional[dict] = None):
        """Send sanitized state snapshot directly to this client."""
        if state is None:
            state = get_game(self.code)
        payload = get_sanitized_player_view(state, self.player_id)
        await self.send_json(payload)

    async def game_state_sync(self, event):
        """Channel layer handler for `game.state.sync` broadcasts."""
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
        elif action in ("chat", "chat_or_guess"):
            await self._handle_unified_chat_or_guess(state, content)
        elif action == "rename":
            await self._handle_rename(state, content)
        elif action == "toggle_spectator":
            await self._handle_toggle_spectator(state, content)
        elif action == "kick_player":
            await self._handle_kick_player(state, content)
        elif action == "transfer_admin":
            await self._handle_transfer_admin(state, content)
        elif action == "settings":
            await self._handle_settings(state, content)
        elif action == "apply_preset":
            await self._handle_apply_preset(state, content)
        elif action == "timer_control":
            await self._handle_timer_control(state, content)
        elif action == "end_game":
            await self._handle_end_game(state)
        elif action == "play_again":
            await self._handle_play_again(state)
        else:
            mode = state.get("mode", "round_robin")
            if mode == "best_guess":
                await self.handle_best_guess_action(action, state, content)
            else:
                await self.handle_game_action(action, state, content)

    async def _handle_join(self, state: dict, content: dict):
        raw_name = (content.get("name") or "Player").strip()
        token = content.get("token")
        admin_token = content.get("admin_token")
        is_admin = bool(admin_token and admin_token == state.get("admin_token"))

        state, player, is_new = add_player(
            state,
            name=raw_name,
            token=token,
            channel_name=self.channel_name,
            is_admin=is_admin,
        )
        self.player_id = player["id"]
        self.player_name = player["name"]

        if is_new:
            await self._group_send("game.message", msg=f"{self.player_name} joined", players=player_list(state))

        # Always send full state snapshot to joining/reconnecting client and sync room
        await self.send_state_to_self(state)
        await self.broadcast_sync()

    async def _handle_unified_chat_or_guess(self, state: dict, content: dict):
        msg = (content.get("msg") or content.get("guess") or "").strip()
        if not msg or not self.player_id:
            return

        phase = state.get("phase", "lobby")
        mode = state.get("mode", "round_robin")
        cp = current_player_id(state)
        player = state.get("players", {}).get(self.player_id, {})

        # In Round Robin or Collective guessing phase, active guessers' chat messages ARE guesses!
        if (
            phase == "guess"
            and mode in ("round_robin", "collective")
            and self.player_id != cp
            and self.player_id not in state.get("guessed", [])
            and not player.get("is_spectator", False)
        ):
            await self._rr_guess(state, {"guess": msg})
            return

        # Otherwise it's a regular chat message — apply spoiler guard if a secret word is in play
        if phase in ("emoji", "guess") and state.get("current_word"):
            msg = censor_spoilers(msg, state.get("current_word"))

        append_chat_event(
            state,
            kind="chat",
            text=msg,
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)
        await self._group_send("game.chat", name=self.player_name, msg=msg)
        await self.broadcast_sync()

    async def _handle_rename(self, state: dict, content: dict):
        if not self.player_id:
            return
        new_name = (content.get("name") or "").strip()
        ok, result = rename_player(state, self.player_id, new_name)
        if not ok:
            await self.send_json({"type": "error", "msg": result})
            return
        self.player_name = result
        await self._group_send("game.message", msg=f"✨ Renamed to {result}", players=player_list(state))
        await self.broadcast_sync()

    async def _handle_toggle_spectator(self, state: dict, content: dict):
        target_id = content.get("player_id") or self.player_id
        if target_id != self.player_id and not self._is_player_admin(state):
            return
        toggle_spectator(state, target_id)
        await self.broadcast_sync()

    async def _handle_kick_player(self, state: dict, content: dict):
        if not self._is_player_admin(state):
            return
        target_id = content.get("player_id")
        if not target_id or target_id == self.player_id:
            return
        kick_player(state, target_id, by_name=self.player_name or "Host")
        await self.broadcast_sync()

    async def _handle_transfer_admin(self, state: dict, content: dict):
        if not self._is_player_admin(state):
            return
        target_id = content.get("player_id")
        if target_id and transfer_admin(state, target_id):
            await self.broadcast_sync()

    async def _handle_settings(self, state: dict, content: dict):
        if not self._is_player_admin(state):
            return
        s = state.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))
        for key in ("max_rounds", "emoji_timer", "guess_timer", "difficulty", "allow_rerolls"):
            if key in content:
                try:
                    val = max(0, int(content[key]))
                    if key == "max_rounds":
                        val = max(1, min(50, val))
                    s[key] = val
                except (ValueError, TypeError):
                    pass

        if "chat_mode" in content and content["chat_mode"] in ("public", "private"):
            s["chat_mode"] = content["chat_mode"]
        if "end_on_first_guess" in content:
            s["end_on_first_guess"] = bool(content["end_on_first_guess"])
        if "allow_custom_words" in content:
            s["allow_custom_words"] = bool(content["allow_custom_words"])
        if "categories" in content and isinstance(content["categories"], list):
            s["categories"] = content["categories"] or ["all"]
        if "mode" in content and content["mode"] in ("round_robin", "collective", "best_guess"):
            state["mode"] = content["mode"]

        state["settings"] = s
        append_chat_event(
            state,
            kind="system",
            text=f"⚙️ {self.player_name} updated room settings (Mode: {state['mode'].replace('_', ' ').title()}, Rounds: {s['max_rounds']})",
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)
        await self._group_send("game.message", msg="settings updated", players=player_list(state))
        await self.broadcast_sync()

    async def _handle_apply_preset(self, state: dict, content: dict):
        if not self._is_player_admin(state):
            return
        preset_key = content.get("preset")
        preset = SETTINGS_PRESETS.get(preset_key)
        if not preset:
            return
        state["mode"] = preset["mode"]
        state.setdefault("settings", {}).update(copy.deepcopy(preset["settings"]))
        append_chat_event(
            state,
            kind="system",
            text=f"🎛️ Applied preset: {preset['label']}",
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)
        await self.broadcast_sync()

    async def _handle_timer_control(self, state: dict, content: dict):
        if not self._is_player_admin(state):
            return
        op = content.get("op")
        now = time.time()
        if op == "pause" and state.get("timer_ends_at") and state.get("timer_paused_remaining") is None:
            state["timer_paused_remaining"] = max(1, round(state["timer_ends_at"] - now, 1))
            state["timer_ends_at"] = None
            append_chat_event(state, kind="system", text=f"⏸️ {self.player_name} paused the timer")
        elif op == "resume" and state.get("timer_paused_remaining") is not None:
            rem = state["timer_paused_remaining"]
            state["timer_ends_at"] = now + rem
            state["timer_paused_remaining"] = None
            append_chat_event(state, kind="system", text=f"▶️ {self.player_name} resumed the timer")
        elif op == "add_time":
            extra = int(content.get("seconds", 15))
            if state.get("timer_paused_remaining") is not None:
                state["timer_paused_remaining"] = max(1, state["timer_paused_remaining"] + extra)
            elif state.get("timer_ends_at"):
                state["timer_ends_at"] += extra
                state["timer_duration"] = state.get("timer_duration", 60) + extra
            append_chat_event(state, kind="system", text=f"⏱️ {self.player_name} added +{extra}s to the timer")
        save_game(self.code, state)
        await self.broadcast_sync()

    async def _handle_end_game(self, state: dict):
        if not self._is_player_admin(state):
            return
        if not state.get("started") or state.get("phase") in ("lobby", "gameover"):
            return

        last_word = state.get("current_word")
        state["phase"] = "gameover"
        state["status"] = "finished"
        state["timer_ends_at"] = None
        state["timer_paused_remaining"] = None

        msg = f"🛑 {self.player_name} ended the game!"
        if last_word:
            msg += f' (Word was: "{last_word}")'
        append_chat_event(
            state,
            kind="system",
            text=msg,
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)
        await database_sync_to_async(sync_room_db_status)(self.code, "finished")
        await self._group_send("game.game_over", players=player_list(state))
        await self.broadcast_sync()

    async def _handle_play_again(self, state: dict):
        if not self._is_player_admin(state) and state.get("phase") != "gameover":
            return
        state["started"] = False
        state["status"] = "open"
        state["phase"] = "lobby"
        state["round_num"] = 0
        state["current_turn"] = 0
        state["history"] = []
        state["rounds_history"] = []
        state["guessed"] = []
        state["current_attempts"] = []
        state["submissions"] = {}
        state["collective_queue"] = {}
        state["emoji_clue"] = ""
        state["emoji_hints"] = []
        state["current_word"] = None
        state["timer_ends_at"] = None
        state["timer_paused_remaining"] = None
        for p in state["players"].values():
            p["score"] = 0

        append_chat_event(
            state,
            kind="system",
            text="🔄 New match lobby ready! Adjust settings or click Start Game.",
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)
        await database_sync_to_async(sync_room_db_status)(self.code, "open")
        await self._group_send("game.message", msg="new game! waiting to start...", players=player_list(state))
        for pid, info in state["players"].items():
            if info.get("is_admin") or info.get("name") == state.get("creator"):
                ch = info.get("channel_name") or (pid if pid.startswith("specific.") else None)
                if ch:
                    await self.channel_layer.send(ch, {"type": "game.show_start"})
        await self.broadcast_sync()

    async def _group_send(self, msg_type: str, **kwargs):
        await self.channel_layer.group_send(self.group_name, {"type": msg_type, **kwargs})

    # Shared legacy message handlers
    async def game_message(self, event):
        await self.send_json({"type": "message", "msg": event["msg"], "players": event.get("players")})

    async def game_chat(self, event):
        await self.send_json({"type": "chat", "name": event["name"], "msg": event["msg"]})

    async def game_over(self, event):
        await self.send_json({"type": "game_over", "players": event["players"], "history": event.get("history", [])})

    async def game_show_start(self, event):
        await self.send_json({"type": "show_start"})

    async def game_state(self, event):
        await self.send_json(event)

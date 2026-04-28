"""Main WebSocket consumer — dispatches to game mode handlers."""

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import get_game, player_list, save_game
from .modes.best_guess import BestGuessMixin
from .modes.round_robin import RoundRobinMixin


class EmojinaryConsumer(RoundRobinMixin, BestGuessMixin, AsyncJsonWebsocketConsumer):
    """
    Game consumer that delegates to mode-specific mixins.
    Modes: round_robin (default), best_guess, telephone (future).
    """

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"]
        self.group_name = f"emojinary_{self.code}"
        self.player_name = None
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        state = get_game(self.code)
        if self.channel_name in state["players"]:
            name = state["players"][self.channel_name]["name"]
            del state["players"][self.channel_name]
            if self.channel_name in state["turn_order"]:
                state["turn_order"].remove(self.channel_name)
            save_game(self.code, state)
            await self._group_send("game.message", msg=f"{name} left", players=player_list(state))
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        action = content.get("action")
        state = get_game(self.code)

        # Common actions
        if action == "join":
            await self._handle_join(state, content)
        elif action == "chat":
            msg = content.get("msg", "").strip()
            if msg and self.player_name:
                await self._group_send("game.chat", name=self.player_name, msg=msg)
        elif action == "settings":
            await self._handle_settings(state, content)
        elif action == "play_again":
            await self._handle_play_again(state)
        else:
            # Delegate to mode-specific handler
            mode = state.get("mode", "round_robin")
            if mode == "best_guess":
                await self.handle_best_guess_action(action, state, content)
            else:
                await self.handle_game_action(action, state, content)

    async def _handle_join(self, state, content):
        from .game_state import current_player_channel

        self.player_name = content.get("name", "anon")
        old_ch = None
        for ch, info in state["players"].items():
            if info["name"] == self.player_name and ch != self.channel_name:
                old_ch = ch
                break
        if old_ch:
            state["players"][self.channel_name] = state["players"].pop(old_ch)
            if old_ch in state["turn_order"]:
                state["turn_order"][state["turn_order"].index(old_ch)] = self.channel_name
            save_game(self.code, state)
        elif self.channel_name not in state["players"]:
            state["players"][self.channel_name] = {"name": self.player_name, "score": 0}
            state["turn_order"].append(self.channel_name)
            if not state["creator"]:
                state["creator"] = self.player_name
            save_game(self.code, state)
            await self._group_send("game.message", msg=f"{self.player_name} joined", players=player_list(state))
            return

        cp = current_player_channel(state)
        await self.send_json(
            {
                "type": "state",
                "players": player_list(state),
                "started": state["started"],
                "creator": state.get("creator"),
                "phase": state.get("phase", "lobby"),
                "history": state.get("history", []),
                "emoji_clue": state.get("emoji_clue", "") if state.get("phase") == "guess" else "",
                "round_num": state.get("round_num", 0),
                "current_word": state["current_word"] if self.channel_name == cp else None,
                "settings": state.get("settings", {}),
            }
        )

    async def _handle_settings(self, state, content):
        if self.player_name != state.get("creator") or state["started"]:
            return
        s = state.get("settings", {})
        for key in ("max_rounds", "emoji_timer", "guess_timer", "difficulty"):
            if key in content:
                try:
                    s[key] = max(0, int(content[key]))
                except (ValueError, TypeError):
                    pass
        if "chat_mode" in content and content["chat_mode"] in ("public", "private"):
            s["chat_mode"] = content["chat_mode"]
        if "mode" in content and content["mode"] in ("round_robin", "best_guess"):
            state["mode"] = content["mode"]
        state["settings"] = s
        save_game(self.code, state)
        await self._group_send("game.message", msg="settings updated", players=player_list(state))

    async def _handle_play_again(self, state):
        state["started"] = False
        state["phase"] = "lobby"
        state["round_num"] = 0
        state["current_turn"] = 0
        state["history"] = []
        state["guessed"] = []
        state["emoji_clue"] = ""
        state["current_word"] = None
        for ch in state["players"]:
            state["players"][ch]["score"] = 0
        save_game(self.code, state)
        await self._group_send("game.message", msg="new game! waiting to start...", players=player_list(state))
        for ch, info in state["players"].items():
            if info["name"] == state.get("creator"):
                await self.channel_layer.send(ch, {"type": "game.show_start"})

    async def _group_send(self, msg_type, **kwargs):
        await self.channel_layer.group_send(self.group_name, {"type": msg_type, **kwargs})

    # Message handlers (shared across modes)
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

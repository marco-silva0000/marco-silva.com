import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import (
    check_guess,
    current_player_channel,
    get_game,
    next_round,
    player_list,
    save_game,
)
from .models import EmojinaryWord


class EmojinaryConsumer(AsyncJsonWebsocketConsumer):
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

        if action == "join":
            await self._handle_join(state, content)
        elif action == "chat":
            msg = content.get("msg", "").strip()
            if msg and self.player_name:
                await self._group_send("game.chat", name=self.player_name, msg=msg)
        elif action == "settings":
            await self._handle_settings(state, content)
        elif action == "start":
            await self._handle_start(state)
        elif action == "emoji":
            await self._handle_emoji(state, content)
        elif action == "reveal":
            await self._handle_reveal(state)
        elif action == "guess":
            await self._handle_guess(state, content)
        elif action == "skip":
            await self._handle_skip(state)
        elif action == "play_again":
            await self._handle_play_again(state)

    async def _handle_join(self, state, content):
        self.player_name = content.get("name", "anon")
        # Reconnect — replace old channel
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

        # Send current state on reconnect
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
        state["settings"] = s
        save_game(self.code, state)
        await self._group_send("game.message", msg="settings updated", players=player_list(state))

    async def _handle_start(self, state):
        if state["started"]:
            return
        if self.player_name != state.get("creator"):
            await self.send_json({"type": "error", "msg": "only the creator can start"})
            return
        if len(state["players"]) < 2:
            await self._group_send("game.message", msg="need at least 2 players", players=player_list(state))
            return
        state["started"] = True
        words = await self._get_words(state)
        state = next_round(state, words)
        state["phase"] = "emoji"
        state["turn_start_time"] = time.time()
        save_game(self.code, state)
        await self._broadcast_emoji_phase(state)

    async def _handle_emoji(self, state, content):
        if state.get("phase") != "emoji" or self.channel_name != current_player_channel(state):
            return
        state["emoji_clue"] = content.get("emoji", "")
        save_game(self.code, state)
        # Only show to the emoji player as preview
        await self.send_json({"type": "emoji_preview", "emoji": state["emoji_clue"]})

    async def _handle_reveal(self, state):
        if state.get("phase") != "emoji" or self.channel_name != current_player_channel(state):
            return
        state["phase"] = "guess"
        state["turn_start_time"] = time.time()
        save_game(self.code, state)
        s = state.get("settings", {})
        await self._group_send(
            "game.guess_phase",
            emoji=state["emoji_clue"],
            guess_timer=s.get("guess_timer", 60),
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
        )

    async def _handle_guess(self, state, content):
        if state.get("phase") != "guess":
            return
        cp = current_player_channel(state)
        if self.channel_name == cp or self.channel_name in state["guessed"]:
            return
        guess = content.get("guess", "")
        correct, partial = check_guess(state, guess)
        if correct:
            elapsed = time.time() - (state.get("turn_start_time") or time.time())
            points = max(1, 10 - int(elapsed) // 6)
            state["guessed"].append(self.channel_name)
            state["players"][self.channel_name]["score"] += points
            if cp in state["players"]:
                state["players"][cp]["score"] += 3
            save_game(self.code, state)
            await self._group_send(
                "game.correct",
                guesser=self.player_name,
                word=state["current_word"],
                points=points,
                players=player_list(state),
            )
            if len(state["guessed"]) >= len(state["players"]) - 1:
                await self._advance_round(state)
        elif partial:
            await self.send_json({"type": "partial", "matches": partial})
            chat_mode = state.get("settings", {}).get("chat_mode", "public")
            if chat_mode == "public":
                await self._group_send("game.chat", name=self.player_name, msg=f"{'_' * len(guess)} (close!)")
        else:
            chat_mode = state.get("settings", {}).get("chat_mode", "public")
            if chat_mode == "public":
                await self._group_send("game.chat", name=self.player_name, msg=guess)
            else:
                await self.send_json({"type": "chat", "name": "you", "msg": f"{guess} ❌"})

    async def _handle_skip(self, state):
        cp = current_player_channel(state)
        if self.channel_name != cp:
            return
        state.setdefault("history", []).append(
            {
                "emoji": state["emoji_clue"],
                "word": state["current_word"],
                "category": state["current_category"],
                "guesser": None,
            }
        )
        await self._group_send("game.message", msg=f"Skipped! The word was: {state['current_word']}")
        await self._advance_round(state)

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
        # Show start button for creator
        for ch, info in state["players"].items():
            if info["name"] == state.get("creator"):
                await self.channel_layer.send(ch, {"type": "game.show_start"})

    async def _advance_round(self, state):
        state.setdefault("history", []).append(
            {
                "emoji": state["emoji_clue"],
                "word": state["current_word"],
                "category": state["current_category"],
                "guesser": ", ".join(state["players"][ch]["name"] for ch in state["guessed"] if ch in state["players"]),
            }
        )
        s = state.get("settings", {})
        max_rounds = s.get("max_rounds", 10)
        if state["round_num"] >= max_rounds:
            state["phase"] = "gameover"
            save_game(self.code, state)
            await self._group_send("game.over", players=player_list(state), history=state.get("history", []))
            return
        words = await self._get_words(state)
        state = next_round(state, words)
        state["phase"] = "emoji"
        state["turn_start_time"] = time.time()
        save_game(self.code, state)
        await self._broadcast_emoji_phase(state)

    async def _broadcast_emoji_phase(self, state):
        cp = current_player_channel(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        s = state.get("settings", {})
        await self._group_send(
            "game.emoji_phase",
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
            category=state["current_category"],
            word_length=len(state["current_word"]),
            current_player=cp_name,
            players=player_list(state),
            emoji_timer=s.get("emoji_timer", 60),
        )
        if cp:
            await self.channel_layer.send(cp, {"type": "game.your_word", "word": state["current_word"]})

    async def _group_send(self, msg_type, **kwargs):
        await self.channel_layer.group_send(self.group_name, {"type": msg_type, **kwargs})

    # Handlers
    async def game_message(self, event):
        await self.send_json({"type": "message", "msg": event["msg"], "players": event.get("players")})

    async def game_emoji_phase(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "emoji_phase"})

    async def game_guess_phase(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "guess_phase"})

    async def game_your_word(self, event):
        await self.send_json({"type": "your_word", "word": event["word"]})

    async def game_emoji_update(self, event):
        await self.send_json({"type": "emoji_update", "emoji": event["emoji"]})

    async def game_correct(self, event):
        await self.send_json(
            {
                "type": "correct",
                "guesser": event["guesser"],
                "word": event["word"],
                "points": event.get("points", 0),
                "players": event.get("players"),
            }
        )

    async def game_chat(self, event):
        await self.send_json({"type": "chat", "name": event["name"], "msg": event["msg"]})

    async def game_over(self, event):
        await self.send_json({"type": "game_over", "players": event["players"], "history": event.get("history", [])})

    async def game_show_start(self, event):
        await self.send_json({"type": "show_start"})

    async def game_state(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def _get_words(self, state):
        difficulty = state.get("settings", {}).get("difficulty", 0)
        qs = EmojinaryWord.objects.all()
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        return list(qs.values_list("text", "category"))

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
            await self.channel_layer.group_send(
                self.group_name, {"type": "game.message", "msg": f"{name} left", "players": player_list(state)}
            )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        action = content.get("action")
        state = get_game(self.code)

        if action == "join":
            self.player_name = content.get("name", "anon")
            # Handle reconnect — same name replaces old channel
            old_channel = None
            for ch, info in state["players"].items():
                if info["name"] == self.player_name and ch != self.channel_name:
                    old_channel = ch
                    break
            if old_channel:
                state["players"][self.channel_name] = state["players"].pop(old_channel)
                idx = state["turn_order"].index(old_channel) if old_channel in state["turn_order"] else -1
                if idx >= 0:
                    state["turn_order"][idx] = self.channel_name
                save_game(self.code, state)
                await self.send_json(
                    {
                        "type": "state",
                        "players": player_list(state),
                        "started": state["started"],
                        "creator": state.get("creator"),
                        "history": state.get("history", []),
                        "emoji_clue": state.get("emoji_clue", ""),
                        "round_num": state.get("round_num", 0),
                        "current_word": state["current_word"]
                        if self.channel_name == current_player_channel(state)
                        else None,  # noqa: E501
                    }
                )
                return
            if self.channel_name in state["players"]:
                await self.send_json(
                    {
                        "type": "state",
                        "players": player_list(state),
                        "started": state["started"],
                        "creator": state.get("creator"),
                        "history": state.get("history", []),
                        "emoji_clue": state.get("emoji_clue", ""),
                        "round_num": state.get("round_num", 0),
                        "current_word": state["current_word"]
                        if self.channel_name == current_player_channel(state)
                        else None,  # noqa: E501
                    }
                )
                return
            state["players"][self.channel_name] = {"name": self.player_name, "score": 0}
            state["turn_order"].append(self.channel_name)
            if not state["creator"]:
                state["creator"] = self.player_name
            save_game(self.code, state)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "game.message", "msg": f"{self.player_name} joined", "players": player_list(state)},
            )

        elif action == "chat":
            msg = content.get("msg", "").strip()
            if msg and self.player_name:
                await self.channel_layer.group_send(
                    self.group_name, {"type": "game.chat", "name": self.player_name, "msg": msg}
                )

        elif action == "start":
            if state["started"]:
                await self.send_json({"type": "error", "msg": "game already started"})
                return
            if self.player_name != state.get("creator"):
                await self.send_json({"type": "error", "msg": "only the room creator can start"})
                return
            if len(state["players"]) < 2:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "game.message", "msg": "need at least 2 players to start", "players": player_list(state)},
                )
                return
            state["started"] = True
            words = await self._get_words()
            state = next_round(state, words)
            save_game(self.code, state)
            await self._broadcast_new_round(state)

        elif action == "emoji":
            if self.channel_name != current_player_channel(state):
                return
            state["emoji_clue"] = content.get("emoji", "")
            save_game(self.code, state)
            await self.channel_layer.group_send(
                self.group_name, {"type": "game.emoji_update", "emoji": state["emoji_clue"]}
            )

        elif action == "guess":
            if self.channel_name == current_player_channel(state):
                return
            if self.channel_name in state["guessed"]:
                return
            guess = content.get("guess", "")
            correct, partial = check_guess(state, guess)
            if correct:
                state["guessed"].append(self.channel_name)
                state["players"][self.channel_name]["score"] += 10
                cp = current_player_channel(state)
                if cp in state["players"]:
                    state["players"][cp]["score"] += 5
                save_game(self.code, state)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game.correct",
                        "guesser": self.player_name,
                        "word": state["current_word"],
                        "players": player_list(state),
                    },
                )
                if len(state["guessed"]) >= len(state["players"]) - 1:
                    # Record history
                    state.setdefault("history", []).append(
                        {
                            "emoji": state["emoji_clue"],
                            "word": state["current_word"],
                            "category": state["current_category"],
                            "guesser": self.player_name,
                        }
                    )
                    words = await self._get_words()
                    state = next_round(state, words)
                    save_game(self.code, state)
                    await self._broadcast_new_round(state)
            elif partial:
                await self.send_json({"type": "partial", "matches": partial, "guess": guess})
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "game.chat", "name": self.player_name, "msg": f"{'_' * len(guess)} (partial!)"},
                )
            else:
                await self.channel_layer.group_send(
                    self.group_name, {"type": "game.chat", "name": self.player_name, "msg": guess}
                )

        elif action == "skip":
            if self.channel_name != current_player_channel(state):
                return
            # Record history
            state.setdefault("history", []).append(
                {
                    "emoji": state["emoji_clue"],
                    "word": state["current_word"],
                    "category": state["current_category"],
                    "guesser": None,
                }
            )
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "game.message", "msg": f"Skipped! The word was: {state['current_word']}"},
            )
            words = await self._get_words()
            state = next_round(state, words)
            save_game(self.code, state)
            await self._broadcast_new_round(state)

    async def _broadcast_new_round(self, state):
        cp = current_player_channel(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game.new_round",
                "round": state["round_num"],
                "category": state["current_category"],
                "word_length": len(state["current_word"]),
                "current_player": cp_name,
                "players": player_list(state),
            },
        )
        if cp:
            await self.channel_layer.send(cp, {"type": "game.your_word", "word": state["current_word"]})

    # Group message handlers
    async def game_message(self, event):
        await self.send_json({"type": "message", "msg": event["msg"], "players": event.get("players")})

    async def game_new_round(self, event):
        await self.send_json(
            {
                "type": "new_round",
                "round": event["round"],
                "category": event["category"],
                "word_length": event["word_length"],
                "current_player": event["current_player"],
                "players": event.get("players"),
            }
        )

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
                "players": event.get("players"),
            }
        )

    async def game_chat(self, event):
        await self.send_json({"type": "chat", "name": event["name"], "msg": event["msg"]})

    async def game_state(self, event):
        await self.send_json({"type": "state", "players": event["players"], "started": event["started"]})

    @database_sync_to_async
    def _get_words(self):
        return list(EmojinaryWord.objects.values_list("text", "category"))

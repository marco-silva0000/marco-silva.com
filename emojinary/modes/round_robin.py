"""Round Robin game mode: one player picks emojis, others guess."""

import time

from channels.db import database_sync_to_async

from ..game_state import (
    check_guess,
    current_player_channel,
    next_round,
    player_list,
    save_game,
)
from ..models import EmojinaryWord


class RoundRobinMixin:
    """Mixin providing round-robin game actions."""

    async def handle_game_action(self, action, state, content):
        if action == "start":
            await self._rr_start(state)
        elif action == "emoji":
            await self._rr_emoji(state, content)
        elif action == "reveal":
            await self._rr_reveal(state)
        elif action == "guess":
            await self._rr_guess(state, content)
        elif action == "skip":
            await self._rr_skip(state)

    async def _rr_start(self, state):
        if state["started"]:
            return
        if self.player_name != state.get("creator"):
            await self.send_json({"type": "error", "msg": "only the creator can start"})
            return
        if len(state["players"]) < 2:
            await self._group_send("game.message", msg="need at least 2 players", players=player_list(state))
            return
        state["started"] = True
        words = await self._rr_get_words(state)
        state = next_round(state, words)
        state["phase"] = "emoji"
        state["turn_start_time"] = time.time()
        save_game(self.code, state)
        await self._rr_broadcast_emoji_phase(state)

    async def _rr_emoji(self, state, content):
        if state.get("phase") != "emoji" or self.channel_name != current_player_channel(state):
            return
        state["emoji_clue"] = content.get("emoji", "")
        save_game(self.code, state)
        await self.send_json({"type": "emoji_preview", "emoji": state["emoji_clue"]})

    async def _rr_reveal(self, state):
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

    async def _rr_guess(self, state, content):
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
                await self._rr_advance(state)
        elif partial:
            await self.send_json({"type": "partial", "matches": partial})
            if state.get("settings", {}).get("chat_mode", "public") == "public":
                await self._group_send("game.chat", name=self.player_name, msg=f"{'_' * len(guess)} (close!)")
        else:
            chat_mode = state.get("settings", {}).get("chat_mode", "public")
            if chat_mode == "public":
                await self._group_send("game.chat", name=self.player_name, msg=guess)
            else:
                await self.send_json({"type": "chat", "name": "you", "msg": f"{guess} ❌"})

    async def _rr_skip(self, state):
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
        await self._rr_advance(state)

    async def _rr_advance(self, state):
        state.setdefault("history", []).append(
            {
                "emoji": state["emoji_clue"],
                "word": state["current_word"],
                "category": state["current_category"],
                "guesser": ", ".join(state["players"][ch]["name"] for ch in state["guessed"] if ch in state["players"]),
            }
        )
        s = state.get("settings", {})
        if state["round_num"] >= s.get("max_rounds", 10):
            state["phase"] = "gameover"
            save_game(self.code, state)
            await self._group_send("game.over", players=player_list(state), history=state.get("history", []))
            return
        words = await self._rr_get_words(state)
        state = next_round(state, words)
        state["phase"] = "emoji"
        state["turn_start_time"] = time.time()
        save_game(self.code, state)
        await self._rr_broadcast_emoji_phase(state)

    async def _rr_broadcast_emoji_phase(self, state):
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

    # Mode-specific message handlers
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

    @database_sync_to_async
    def _rr_get_words(self, state):
        difficulty = state.get("settings", {}).get("difficulty", 0)
        qs = EmojinaryWord.objects.all()
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        return list(qs.values_list("text", "category"))

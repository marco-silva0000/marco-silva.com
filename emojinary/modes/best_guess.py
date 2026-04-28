"""Best Guess mode: picker sends a word, everyone submits emojis, picker picks the best."""

import time

from channels.db import database_sync_to_async

from ..game_state import (
    current_player_channel,
    next_round,
    player_list,
    save_game,
)
from ..models import EmojinaryWord


class BestGuessMixin:
    """Mixin providing best-guess game actions."""

    async def handle_best_guess_action(self, action, state, content):
        if action == "start":
            await self._bg_start(state)
        elif action == "reroll":
            await self._bg_reroll(state)
        elif action == "send_prompt":
            await self._bg_send_prompt(state, content)
        elif action == "submit_emoji":
            await self._bg_submit_emoji(state, content)
        elif action == "pick_best":
            await self._bg_pick_best(state, content)

    async def _bg_start(self, state):
        if state["started"]:
            return
        if self.player_name != state.get("creator"):
            await self.send_json({"type": "error", "msg": "only the creator can start"})
            return
        if len(state["players"]) < 2:
            await self._group_send("game.message", msg="need at least 2 players", players=player_list(state))
            return
        state["started"] = True
        state["mode"] = "best_guess"
        words = await self._bg_get_words(state)
        state = next_round(state, words)
        state["phase"] = "picking"
        state["submissions"] = {}  # channel -> emoji
        save_game(self.code, state)
        await self._bg_broadcast_picking(state)

    async def _bg_reroll(self, state):
        if state.get("phase") != "picking" or self.channel_name != current_player_channel(state):
            return
        words = await self._bg_get_words(state)
        if words:
            import random

            word, cat = random.choice(words)
            state["current_word"] = word
            state["current_category"] = cat
            save_game(self.code, state)
        await self.send_json({"type": "your_word", "word": state["current_word"]})

    async def _bg_send_prompt(self, state, content):
        if state.get("phase") != "picking" or self.channel_name != current_player_channel(state):
            return
        custom = content.get("prompt", "").strip()
        if custom:
            state["current_word"] = custom
        state["phase"] = "submitting"
        state["submissions"] = {}
        state["turn_start_time"] = time.time()
        save_game(self.code, state)
        s = state.get("settings", {})
        await self._group_send(
            "game.bg_submit_phase",
            prompt=state["current_word"],
            emoji_timer=s.get("emoji_timer", 60),
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
            current_player=state["players"].get(current_player_channel(state), {}).get("name", "?"),
            players=player_list(state),
        )

    async def _bg_submit_emoji(self, state, content):
        if state.get("phase") != "submitting":
            return
        cp = current_player_channel(state)
        if self.channel_name == cp:
            return
        emoji = content.get("emoji", "").strip()
        if emoji:
            state.setdefault("submissions", {})[self.channel_name] = emoji
            save_game(self.code, state)
            await self._group_send(
                "game.message",
                msg=f"{self.player_name} submitted!",
                players=player_list(state),
            )
            # Check if all submitted
            expected = len(state["players"]) - 1
            if len(state["submissions"]) >= expected:
                await self._bg_show_submissions(state)

    async def _bg_show_submissions(self, state):
        state["phase"] = "judging"
        save_game(self.code, state)
        subs = [
            {"channel": ch, "name": state["players"].get(ch, {}).get("name", "?"), "emoji": em}
            for ch, em in state.get("submissions", {}).items()
        ]
        await self._group_send("game.bg_judging", submissions=subs, prompt=state["current_word"])

    async def _bg_pick_best(self, state, content):
        if state.get("phase") != "judging" or self.channel_name != current_player_channel(state):
            return
        winner_channel = content.get("winner")
        if winner_channel not in state.get("submissions", {}):
            return
        winner_name = state["players"].get(winner_channel, {}).get("name", "?")
        state["players"][winner_channel]["score"] += 10
        state["players"][self.channel_name]["score"] += 3

        state.setdefault("history", []).append(
            {
                "emoji": state["submissions"].get(winner_channel, ""),
                "word": state["current_word"],
                "category": state.get("current_category", ""),
                "guesser": winner_name,
            }
        )

        save_game(self.code, state)
        await self._group_send(
            "game.bg_winner",
            winner=winner_name,
            emoji=state["submissions"].get(winner_channel, ""),
            prompt=state["current_word"],
            players=player_list(state),
        )

        # Advance
        s = state.get("settings", {})
        if state["round_num"] >= s.get("max_rounds", 10):
            state["phase"] = "gameover"
            save_game(self.code, state)
            await self._group_send("game.over", players=player_list(state), history=state.get("history", []))
        else:
            words = await self._bg_get_words(state)
            state = next_round(state, words)
            state["phase"] = "picking"
            state["submissions"] = {}
            save_game(self.code, state)
            # Brief pause then next round
            await self._bg_broadcast_picking(state)

    async def _bg_broadcast_picking(self, state):
        cp = current_player_channel(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        s = state.get("settings", {})
        await self._group_send(
            "game.bg_picking",
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
            current_player=cp_name,
            players=player_list(state),
        )
        if cp:
            await self.channel_layer.send(cp, {"type": "game.your_word", "word": state["current_word"]})

    # Message handlers for best guess
    async def game_bg_picking(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_picking"})

    async def game_bg_submit_phase(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_submit_phase"})

    async def game_bg_judging(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_judging"})

    async def game_bg_winner(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_winner"})

    @database_sync_to_async
    def _bg_get_words(self, state):
        difficulty = state.get("settings", {}).get("difficulty", 0)
        qs = EmojinaryWord.objects.all()
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        return list(qs.values_list("text", "category"))

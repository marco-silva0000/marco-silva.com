"""Best Guess (Judge's Pick) mode: picker sets a prompt, everyone submits emojis, picker judges the best."""

import time

from channels.db import database_sync_to_async

from ..game_state import (
    append_chat_event,
    current_player_id,
    next_round,
    pick_unused_word,
    player_list,
    record_round_to_history,
    save_game,
    set_phase_timer,
    sync_room_db_status,
)
from ..models import EmojinaryWord


class BestGuessMixin:
    """Mixin providing Best Guess (Judge's Pick) game actions."""

    async def handle_best_guess_action(self, action: str, state: dict, content: dict):
        if action == "start":
            await self._bg_start(state)
        elif action == "reroll":
            await self._bg_reroll(state)
        elif action in ("send_prompt", "reveal", "custom_word"):
            await self._bg_send_prompt(state, content)
        elif action in ("submit_emoji", "emoji"):
            if action == "emoji" and state.get("phase") == "submitting" and not content.get("submit"):
                # Live preview only
                await self.send_json({"type": "emoji_preview", "emoji": content.get("emoji", "")})
                return
            await self._bg_submit_emoji(state, content)
        elif action == "pick_best":
            await self._bg_pick_best(state, content)
        elif action in ("skip", "force_advance"):
            await self._bg_skip(state)

    async def _bg_start(self, state: dict):
        if state.get("started") and state.get("phase") not in ("lobby", "gameover"):
            return
        if not self._is_player_admin(state):
            await self.send_json({"type": "error", "msg": "Only the Room Host can start the game."})
            return
        active_order = [pid for pid in state.get("turn_order", []) if pid in state.get("players", {})]
        if len(active_order) < 2:
            await self._group_send("game.message", msg="Need at least 2 players to start!", players=player_list(state))
            return

        state["started"] = True
        state["status"] = "running"
        state["mode"] = "best_guess"
        state["round_num"] = 0
        state["current_turn"] = 0
        state["history"] = []
        state["rounds_history"] = []
        state["used_words"] = []
        for p in state["players"].values():
            p["score"] = 0

        words = await self._bg_get_words(state)
        state = next_round(state, words)
        state["phase"] = "picking"
        state["submissions"] = {}
        s = state.get("settings", {})
        set_phase_timer(state, s.get("emoji_timer", 60))

        cp = current_player_id(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="round_start",
            text=f"🎭 Round {state['round_num']}/{s.get('max_rounds', 10)} — Judge {cp_name} is choosing a prompt",
            player_id=cp,
            player_name=cp_name,
        )
        save_game(self.code, state)
        await database_sync_to_async(sync_room_db_status)(self.code, "running")
        await self._bg_broadcast_picking(state)
        await self.broadcast_sync()

    async def _bg_reroll(self, state: dict):
        if state.get("phase") != "picking" or self.player_id != current_player_id(state):
            return
        s = state.get("settings", {})
        max_rerolls = int(s.get("allow_rerolls", 2))
        if state.get("rerolls_used", 0) >= max_rerolls:
            await self.send_json({"type": "error", "msg": "No rerolls left for this turn."})
            return

        words = await self._bg_get_words(state)
        word, cat = pick_unused_word(state, words)
        state["current_word"] = word
        state["current_category"] = cat
        state["rerolls_used"] = state.get("rerolls_used", 0) + 1
        save_game(self.code, state)
        await self.send_json({"type": "your_word", "word": state["current_word"], "category": cat})
        await self.broadcast_sync()

    async def _bg_send_prompt(self, state: dict, content: dict):
        cp = current_player_id(state)
        if state.get("phase") != "picking" or (self.player_id != cp and not self._is_player_admin(state)):
            return
        custom = (content.get("prompt") or content.get("word") or "").strip()[:100]
        # Clean accidental prefix or button text if sent by legacy JS
        if custom.lower().startswith("your word:"):
            custom = custom[len("your word:") :].strip()
        for suffix in ("🎲 reroll", "✅ send", "✅ Use Prompt"):
            custom = custom.replace(suffix, "").strip()
        if custom:
            state["current_word"] = custom

        state["phase"] = "submitting"
        state["submissions"] = {}
        state["current_attempts"] = []
        s = state.get("settings", {})
        set_phase_timer(state, s.get("emoji_timer", 60))

        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="round_start",
            text=f'📢 Judge {cp_name} set the prompt: "{state["current_word"]}" — Submit your best emoji creation!',
            player_id=cp,
            player_name=cp_name,
        )
        save_game(self.code, state)
        await self._group_send(
            "game.bg_submit_phase",
            prompt=state["current_word"],
            emoji_timer=s.get("emoji_timer", 60),
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
            current_player=cp_name,
            players=player_list(state),
        )
        await self.broadcast_sync()

    async def _bg_submit_emoji(self, state: dict, content: dict):
        if state.get("phase") != "submitting":
            return
        cp = current_player_id(state)
        if not self.player_id or self.player_id == cp:
            return
        emoji = (content.get("emoji") or "").strip()
        if not emoji:
            return

        elapsed = round(time.time() - (state.get("turn_start_time") or time.time()), 1)
        state.setdefault("submissions", {})[self.player_id] = emoji
        # Update or append attempt record
        attempts = state.setdefault("current_attempts", [])
        attempts[:] = [a for a in attempts if a.get("player_id") != self.player_id]
        attempts.append(
            {
                "player_id": self.player_id,
                "player_name": self.player_name,
                "text": emoji,
                "emoji": emoji,
                "outcome": "submission",
                "matches": [],
                "elapsed_sec": elapsed,
                "points": 0,
            }
        )

        append_chat_event(
            state,
            kind="system",
            text=f"🎨 {self.player_name} submitted their emoji entry!",
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)
        await self._group_send(
            "game.message",
            msg=f"{self.player_name} submitted!",
            players=player_list(state),
        )

        eligible = [
            pid
            for pid, p in state["players"].items()
            if pid != cp and not p.get("is_spectator", False) and p.get("connected", True)
        ]
        if len(state["submissions"]) >= max(1, len(eligible)):
            await self._bg_show_submissions(state)
        else:
            await self.broadcast_sync()

    async def _bg_show_submissions(self, state: dict):
        state["phase"] = "judging"
        set_phase_timer(state, state.get("settings", {}).get("guess_timer", 60))
        save_game(self.code, state)
        subs = [
            {
                "channel": pid,
                "player_id": pid,
                "name": state["players"].get(pid, {}).get("name", "?"),
                "emoji": em,
            }
            for pid, em in state.get("submissions", {}).items()
        ]
        append_chat_event(
            state,
            kind="system",
            text=f"⚖️ All {len(subs)} emoji entries are in! Waiting for the Judge to pick a winner...",
        )
        save_game(self.code, state)
        await self._group_send("game.bg_judging", submissions=subs, prompt=state["current_word"])
        await self.broadcast_sync()

    async def _bg_pick_best(self, state: dict, content: dict):
        cp = current_player_id(state)
        if state.get("phase") != "judging" or (self.player_id != cp and not self._is_player_admin(state)):
            return
        winner_id = content.get("winner")
        submissions = state.get("submissions", {})
        if winner_id not in submissions:
            return

        winner_info = state.get("players", {}).get(winner_id)
        winner_name = winner_info.get("name", "?") if winner_info else "?"
        winning_emoji = submissions.get(winner_id, "")

        if winner_info:
            winner_info["score"] += 10
        if cp and cp in state["players"]:
            state["players"][cp]["score"] += 3

        # Mark winning attempt in current_attempts
        for att in state.get("current_attempts", []):
            if att.get("player_id") == winner_id:
                att["outcome"] = "winner"
                att["points"] = 10

        state["emoji_clue"] = winning_emoji
        state["emoji_hints"] = [{"hint_num": 1, "emoji": winning_emoji, "elapsed_sec": 0.0}]
        record_round_to_history(
            state,
            outcome="judged",
            guesser_str=winner_name,
            override_emoji=winning_emoji,
        )

        append_chat_event(
            state,
            kind="round_end",
            text=f'🏆 {winner_name} won the Judge\'s Pick (+10 pts) for "{state["current_word"]}"!',
            player_id=winner_id,
            player_name=winner_name,
            emoji=winning_emoji,
            points=10,
        )
        save_game(self.code, state)
        await self._group_send(
            "game.bg_winner",
            winner=winner_name,
            emoji=winning_emoji,
            prompt=state["current_word"],
            players=player_list(state),
        )

        await self._bg_advance_next(state)

    async def _bg_skip(self, state: dict):
        cp = current_player_id(state)
        if self.player_id != cp and not self._is_player_admin(state):
            return
        if state.get("phase") == "submitting" and state.get("submissions"):
            await self._bg_show_submissions(state)
            return

        record_round_to_history(state, outcome="skipped", guesser_str=None)
        append_chat_event(
            state,
            kind="round_end",
            text=f'⏭️ Judge\'s round skipped (Prompt: "{state.get("current_word")}")',
        )
        await self._bg_advance_next(state)

    async def _bg_advance_next(self, state: dict):
        s = state.get("settings", {})
        if state["round_num"] >= int(s.get("max_rounds", 10)):
            state["phase"] = "gameover"
            state["status"] = "finished"
            state["timer_ends_at"] = None
            save_game(self.code, state)
            await database_sync_to_async(sync_room_db_status)(self.code, "finished")
            await self._group_send("game.over", players=player_list(state), history=state.get("history", []))
            await self.broadcast_sync()
            return

        words = await self._bg_get_words(state)
        state = next_round(state, words)
        state["phase"] = "picking"
        state["submissions"] = {}
        set_phase_timer(state, s.get("emoji_timer", 60))

        cp = current_player_id(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="round_start",
            text=f"🎭 Round {state['round_num']}/{s.get('max_rounds', 10)} — Judge {cp_name} is choosing a prompt",
            player_id=cp,
            player_name=cp_name,
        )
        save_game(self.code, state)
        await self._bg_broadcast_picking(state)
        await self.broadcast_sync()

    async def _bg_broadcast_picking(self, state: dict):
        cp = current_player_id(state)
        cp_info = state["players"].get(cp, {})
        cp_name = cp_info.get("name", "?")
        cp_channel = cp_info.get("channel_name") or (cp if cp and cp.startswith("specific.") else None)
        s = state.get("settings", {})
        await self._group_send(
            "game.bg_picking",
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
            current_player=cp_name,
            players=player_list(state),
        )
        if cp_channel:
            await self.channel_layer.send(
                cp_channel,
                {"type": "game.your_word", "word": state["current_word"], "category": state["current_category"]},
            )

    async def game_bg_picking(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_picking"})

    async def game_bg_submit_phase(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_submit_phase"})

    async def game_bg_judging(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_judging"})

    async def game_bg_winner(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "bg_winner"})

    @database_sync_to_async
    def _bg_get_words(self, state: dict):
        s = state.get("settings", {})
        difficulty = s.get("difficulty", 0)
        categories = s.get("categories", ["all"])
        qs = EmojinaryWord.objects.all()
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if categories and "all" not in categories:
            qs = qs.filter(category__in=categories)
        results = list(qs.values_list("text", "category"))
        if not results:
            results = list(EmojinaryWord.objects.all().values_list("text", "category"))
        return results

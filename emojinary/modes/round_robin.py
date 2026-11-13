"""Round Robin & Collective Prep game modes with live progressive emoji hints and chat guessing."""

import time
from typing import Optional

from channels.db import database_sync_to_async

from ..game_state import (
    append_chat_event,
    build_word_mask,
    check_guess,
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


class RoundRobinMixin:
    """Mixin providing Round Robin and Collective Prep game mode actions."""

    async def handle_game_action(self, action: str, state: dict, content: dict):
        if action == "start":
            if state.get("mode") == "collective":
                await self._collective_start(state)
            else:
                await self._rr_start(state)
        elif action == "emoji":
            await self._rr_emoji(state, content)
        elif action in ("reveal", "submit_prep"):
            if state.get("mode") == "collective" and state.get("phase") == "prep":
                await self._collective_submit_prep(state, content)
            else:
                await self._rr_reveal(state, content)
        elif action == "add_hint":
            await self._rr_add_hint(state, content)
        elif action == "reroll":
            await self._rr_reroll(state)
        elif action == "custom_word":
            await self._rr_set_custom_word(state, content)
        elif action == "guess":
            await self._rr_guess(state, content)
        elif action in ("skip", "force_advance"):
            await self._rr_skip(state, forced=(action == "force_advance"))

    # ========================================================================
    # Classic Round Robin Mode
    # ========================================================================

    async def _rr_start(self, state: dict):
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
        state["round_num"] = 0
        state["current_turn"] = 0
        state["history"] = []
        state["rounds_history"] = []
        state["used_words"] = []
        for p in state["players"].values():
            p["score"] = 0

        words = await self._rr_get_words(state)
        state = next_round(state, words)
        state["phase"] = "emoji"
        s = state.get("settings", {})
        set_phase_timer(state, s.get("emoji_timer", 60))

        cp = current_player_id(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="round_start",
            text=f"🎬 Round {state['round_num']}/{s.get('max_rounds', 10)} — {cp_name} is crafting an emoji clue ({state['current_category']})",
            player_id=cp,
            player_name=cp_name,
        )
        save_game(self.code, state)
        await database_sync_to_async(sync_room_db_status)(self.code, "running")
        await self._rr_broadcast_emoji_phase(state)
        await self.broadcast_sync()

    async def _rr_emoji(self, state: dict, content: dict):
        emoji_str = (content.get("emoji") or "").strip()
        if state.get("mode") == "collective" and state.get("phase") == "prep":
            q = state.setdefault("collective_queue", {}).get(self.player_id)
            if q and not q.get("submitted"):
                q["emoji_clue"] = emoji_str
                save_game(self.code, state)
                await self.send_json({"type": "emoji_preview", "emoji": emoji_str})
                await self.send_state_to_self(state)
            return

        if state.get("phase") != "emoji" or self.player_id != current_player_id(state):
            return
        state["emoji_clue"] = emoji_str
        save_game(self.code, state)
        await self.send_json({"type": "emoji_preview", "emoji": state["emoji_clue"]})

    async def _rr_reroll(self, state: dict):
        s = state.get("settings", {})
        max_rerolls = int(s.get("allow_rerolls", 2))

        if state.get("mode") == "collective" and state.get("phase") == "prep":
            q = state.get("collective_queue", {}).get(self.player_id)
            if not q or q.get("submitted"):
                return
            if q.get("rerolls_used", 0) >= max_rerolls:
                await self.send_json({"type": "error", "msg": "No rerolls left for this round."})
                return
            words = await self._rr_get_words(state)
            w, cat = pick_unused_word(state, words)
            q["word"] = w
            q["category"] = cat
            q["rerolls_used"] = q.get("rerolls_used", 0) + 1
            save_game(self.code, state)
            await self.send_json({"type": "your_word", "word": w, "category": cat})
            await self.send_state_to_self(state)
            return

        if state.get("phase") != "emoji" or self.player_id != current_player_id(state):
            return
        if state.get("rerolls_used", 0) >= max_rerolls:
            await self.send_json({"type": "error", "msg": "No rerolls left for this turn."})
            return

        words = await self._rr_get_words(state)
        w, cat = pick_unused_word(state, words)
        state["current_word"] = w
        state["current_category"] = cat
        state["rerolls_used"] = state.get("rerolls_used", 0) + 1
        save_game(self.code, state)
        await self.send_json({"type": "your_word", "word": w, "category": cat})
        await self.broadcast_sync()

    async def _rr_set_custom_word(self, state: dict, content: dict):
        if not state.get("settings", {}).get("allow_custom_words", False) and not self._is_player_admin(state):
            return
        custom = (content.get("word") or "").strip()[:80]
        if not custom:
            return
        if state.get("mode") == "collective" and state.get("phase") == "prep":
            q = state.get("collective_queue", {}).get(self.player_id)
            if q and not q.get("submitted"):
                q["word"] = custom
                q["category"] = "custom"
                save_game(self.code, state)
                await self.send_state_to_self(state)
            return

        if state.get("phase") == "emoji" and self.player_id == current_player_id(state):
            state["current_word"] = custom
            state["current_category"] = "custom"
            save_game(self.code, state)
            await self.broadcast_sync()

    async def _rr_reveal(self, state: dict, content: Optional[dict] = None):
        cp = current_player_id(state)
        if state.get("phase") != "emoji" or (self.player_id != cp and not self._is_player_admin(state)):
            return
        if content and content.get("emoji"):
            state["emoji_clue"] = content["emoji"].strip()
        if not state.get("emoji_clue", "").strip():
            await self.send_json({"type": "error", "msg": "Pick at least one emoji before revealing!"})
            return

        elapsed = round(time.time() - (state.get("turn_start_time") or time.time()), 1)
        state["phase"] = "guess"
        state["emoji_hints"] = [{"hint_num": 1, "emoji": state["emoji_clue"], "elapsed_sec": elapsed}]
        s = state.get("settings", {})
        set_phase_timer(state, s.get("guess_timer", 60))

        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="emoji_hint",
            text=f"🔍 {cp_name} revealed Hint #1 — type your guesses below!",
            player_id=cp,
            player_name=cp_name,
            emoji=state["emoji_clue"],
        )
        save_game(self.code, state)
        await self._group_send(
            "game.guess_phase",
            emoji=state["emoji_clue"],
            guess_timer=s.get("guess_timer", 60),
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
        )
        await self.broadcast_sync()

    async def _rr_add_hint(self, state: dict, content: dict):
        """Allow the active word writer to submit progressive extra emoji hints during guessing."""
        cp = current_player_id(state)
        if state.get("phase") != "guess" or self.player_id != cp:
            return
        extra_emoji = (content.get("emoji") or "").strip()
        if not extra_emoji:
            return

        hints = state.setdefault("emoji_hints", [])
        hint_num = len(hints) + 1
        elapsed = round(time.time() - (state.get("turn_start_time") or time.time()), 1)
        hints.append({"hint_num": hint_num, "emoji": extra_emoji, "elapsed_sec": elapsed})

        # Combine hints into display clue
        state["emoji_clue"] = "  ".join(h["emoji"] for h in hints)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="emoji_hint",
            text=f"💡 {cp_name} added Hint #{hint_num}:",
            player_id=cp,
            player_name=cp_name,
            emoji=extra_emoji,
        )
        save_game(self.code, state)
        await self._group_send("game.emoji_update", emoji=state["emoji_clue"])
        await self.broadcast_sync()

    async def _rr_guess(self, state: dict, content: dict):
        if state.get("phase") != "guess":
            return
        cp = current_player_id(state)
        if not self.player_id or self.player_id == cp or self.player_id in state.get("guessed", []):
            return

        guess = (content.get("guess") or content.get("msg") or "").strip()
        if not guess:
            return

        elapsed = round(time.time() - (state.get("turn_start_time") or time.time()), 1)
        correct, partial = check_guess(state, guess)
        s = state.get("settings", {})
        chat_mode = s.get("chat_mode", "public")

        if correct:
            # First guesser gets a +2 speed bonus, time-based points from 2..10
            first_bonus = 2 if len(state.get("guessed", [])) == 0 else 0
            points = max(2, 10 - int(elapsed) // 7) + first_bonus
            state.setdefault("guessed", []).append(self.player_id)
            if self.player_id in state["players"]:
                state["players"][self.player_id]["score"] += points
            if cp and cp in state["players"]:
                state["players"][cp]["score"] += 3

            state.setdefault("current_attempts", []).append(
                {
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                    "text": guess,
                    "outcome": "correct",
                    "matches": [],
                    "elapsed_sec": elapsed,
                    "points": points,
                }
            )
            append_chat_event(
                state,
                kind="guess_correct",
                text=f"🎯 {self.player_name} guessed the word! (+{points} pts in {elapsed}s)",
                player_id=self.player_id,
                player_name=self.player_name,
                points=points,
            )
            save_game(self.code, state)

            # Check if round should end now
            eligible_guessers = [
                pid
                for pid, p in state["players"].items()
                if pid != cp and not p.get("is_spectator", False) and p.get("connected", True)
            ]
            end_now = bool(s.get("end_on_first_guess", False)) or (
                len(state["guessed"]) >= max(1, len(eligible_guessers))
            )

            await self._group_send(
                "game.correct",
                guesser=self.player_name,
                word=state["current_word"] if end_now else build_word_mask(state["current_word"]),
                points=points,
                players=player_list(state),
            )

            if end_now:
                await self._rr_advance(state, outcome="guessed")
            else:
                await self.broadcast_sync()

        elif partial:
            state.setdefault("current_attempts", []).append(
                {
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                    "text": guess,
                    "outcome": "close",
                    "matches": partial,
                    "elapsed_sec": elapsed,
                    "points": 0,
                }
            )
            match_hint = ", ".join(partial)
            append_chat_event(
                state,
                kind="guess_close",
                text=f"🔥 {guess} — Close! (matched: {match_hint})",
                player_id=self.player_id,
                player_name=self.player_name,
                private_to=[self.player_id, cp] if chat_mode == "private" else None,
                masked_text="🔥 Close guess!",
            )
            save_game(self.code, state)
            await self.send_json({"type": "partial", "matches": partial})
            if chat_mode == "public":
                await self._group_send("game.chat", name=self.player_name, msg=f"{'_' * len(guess)} (close!)")
            await self.broadcast_sync()

        else:
            state.setdefault("current_attempts", []).append(
                {
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                    "text": guess,
                    "outcome": "wrong",
                    "matches": [],
                    "elapsed_sec": elapsed,
                    "points": 0,
                }
            )
            append_chat_event(
                state,
                kind="guess_wrong",
                text=guess,
                player_id=self.player_id,
                player_name=self.player_name,
                private_to=[self.player_id, cp] if chat_mode == "private" else None,
                masked_text="guessed ❌",
            )
            save_game(self.code, state)
            if chat_mode == "public":
                await self._group_send("game.chat", name=self.player_name, msg=guess)
            else:
                await self.send_json({"type": "chat", "name": "you", "msg": f"{guess} ❌"})
            await self.broadcast_sync()

    async def _rr_skip(self, state: dict, forced: bool = False):
        cp = current_player_id(state)
        is_admin = self._is_player_admin(state)
        # Allow active player, admin, or timer expiration in guess phase
        timer_expired = bool(state.get("timer_ends_at") and time.time() >= state["timer_ends_at"] - 1.0)
        if self.player_id != cp and not is_admin and not timer_expired:
            return

        if state.get("mode") == "collective" and state.get("phase") == "prep":
            await self._collective_begin_guessing_rounds(state)
            return

        word = state.get("current_word") or "mystery"
        had_guessers = len(state.get("guessed", [])) > 0
        outcome = "guessed" if had_guessers else ("timeout" if timer_expired else "skipped")

        if not had_guessers:
            append_chat_event(
                state,
                kind="round_end",
                text=f'⏭️ Round ended! The secret phrase was: "{word}"',
                emoji=state.get("emoji_clue", "🤷"),
            )
            await self._group_send("game.message", msg=f"Skipped! The word was: {word}")

        await self._rr_advance(state, outcome=outcome)

    async def _rr_advance(self, state: dict, outcome: str = "guessed"):
        word = state.get("current_word") or ""
        record_round_to_history(state, outcome=outcome)
        last_round = state["rounds_history"][-1]

        if outcome == "guessed":
            append_chat_event(
                state,
                kind="round_end",
                text=f'✅ Round {last_round["round"]} complete! Phrase: "{word}" (Guessed by: {last_round.get("guesser")})',
                emoji=last_round.get("emoji_clue", ""),
            )

        s = state.get("settings", {})
        max_rounds = int(s.get("max_rounds", 10))

        # Handle Collective Mode progression through prepared clues
        if state.get("mode") == "collective":
            state["collective_index"] = state.get("collective_index", 0) + 1
            order = state.get("collective_order", [])
            if state["round_num"] >= max_rounds or state["collective_index"] >= len(order):
                await self._finish_game(state)
                return
            await self._collective_launch_current_index(state)
            return

        if state["round_num"] >= max_rounds:
            await self._finish_game(state)
            return

        words = await self._rr_get_words(state)
        state = next_round(state, words)
        state["phase"] = "emoji"
        set_phase_timer(state, s.get("emoji_timer", 60))

        cp = current_player_id(state)
        cp_name = state["players"].get(cp, {}).get("name", "?")
        append_chat_event(
            state,
            kind="round_start",
            text=f"🎬 Round {state['round_num']}/{max_rounds} — {cp_name} is crafting an emoji clue ({state['current_category']})",
            player_id=cp,
            player_name=cp_name,
        )
        save_game(self.code, state)
        await self._rr_broadcast_emoji_phase(state)
        await self.broadcast_sync()

    async def _finish_game(self, state: dict):
        state["phase"] = "gameover"
        state["status"] = "finished"
        state["timer_ends_at"] = None
        state["timer_paused_remaining"] = None

        p_list = player_list(state)
        sorted_p = sorted(p_list, key=lambda x: x["score"], reverse=True)
        winner_str = f"{sorted_p[0]['name']} ({sorted_p[0]['score']} pts)" if sorted_p else "Everyone"
        append_chat_event(
            state,
            kind="system",
            text=f"🏆 Game Over! Winner: {winner_str} — Open the Replay tab to inspect every round and attempt!",
        )
        save_game(self.code, state)
        await database_sync_to_async(sync_room_db_status)(self.code, "finished")
        await self._group_send("game.over", players=p_list, history=state.get("history", []))
        await self.broadcast_sync()

    # ========================================================================
    # Collective Prep Mode (Everyone builds initial emoji clues simultaneously)
    # ========================================================================

    async def _collective_start(self, state: dict):
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
        state["mode"] = "collective"
        state["phase"] = "prep"
        state["round_num"] = 0
        state["history"] = []
        state["rounds_history"] = []
        state["used_words"] = []
        for p in state["players"].values():
            p["score"] = 0

        words = await self._rr_get_words(state)
        queue = {}
        for pid in active_order:
            w, cat = pick_unused_word(state, words)
            queue[pid] = {
                "word": w,
                "category": cat,
                "difficulty": 1,
                "emoji_clue": "",
                "submitted": False,
                "rerolls_used": 0,
            }
        state["collective_queue"] = queue
        state["collective_order"] = list(active_order)
        state["collective_index"] = 0

        s = state.get("settings", {})
        # Adjust max_rounds to match collective players count if needed
        if s.get("max_rounds", 10) > len(active_order):
            s["max_rounds"] = len(active_order)
        set_phase_timer(state, s.get("emoji_timer", 60))

        append_chat_event(
            state,
            kind="round_start",
            text="⚡ Collective Prep Phase! Everyone has received a secret phrase — craft your initial emoji clue now!",
        )
        save_game(self.code, state)
        await database_sync_to_async(sync_room_db_status)(self.code, "running")
        await self.broadcast_sync()

    async def _collective_submit_prep(self, state: dict, content: Optional[dict] = None):
        if state.get("phase") != "prep":
            return
        q = state.get("collective_queue", {}).get(self.player_id)
        if not q:
            return
        if content and content.get("emoji"):
            q["emoji_clue"] = content["emoji"].strip()
        if not q.get("emoji_clue", "").strip():
            await self.send_json({"type": "error", "msg": "Pick at least one emoji before locking in!"})
            return

        q["submitted"] = True
        ready_count = sum(1 for item in state["collective_queue"].values() if item.get("submitted"))
        total_count = len(state["collective_queue"])
        append_chat_event(
            state,
            kind="system",
            text=f"✅ {self.player_name} locked in their emoji clue ({ready_count}/{total_count} ready)",
            player_id=self.player_id,
            player_name=self.player_name,
        )
        save_game(self.code, state)

        if ready_count >= total_count:
            await self._collective_begin_guessing_rounds(state)
        else:
            await self.broadcast_sync()

    async def _collective_begin_guessing_rounds(self, state: dict):
        # Filter order to players who submitted (or fallback to all with placeholder emoji if skipped)
        for pid, item in state.get("collective_queue", {}).items():
            if not item.get("emoji_clue"):
                item["emoji_clue"] = "❓"
            item["submitted"] = True
        state["collective_index"] = 0
        await self._collective_launch_current_index(state)

    async def _collective_launch_current_index(self, state: dict):
        order = state.get("collective_order", [])
        idx = state.get("collective_index", 0)
        if idx >= len(order):
            await self._finish_game(state)
            return

        giver_id = order[idx]
        q_item = state.get("collective_queue", {}).get(giver_id, {})
        giver_name = state.get("players", {}).get(giver_id, {}).get("name", "?")

        state["round_num"] = idx + 1
        state["current_word"] = q_item.get("word", "Mystery")
        state["current_category"] = q_item.get("category", "thing")
        state["emoji_clue"] = q_item.get("emoji_clue", "❓")
        state["emoji_hints"] = [{"hint_num": 1, "emoji": state["emoji_clue"], "elapsed_sec": 0.0}]
        state["guessed"] = []
        state["current_attempts"] = []
        state["phase"] = "guess"

        s = state.get("settings", {})
        set_phase_timer(state, s.get("guess_timer", 60))

        append_chat_event(
            state,
            kind="emoji_hint",
            text=f"🎬 Round {state['round_num']}/{len(order)} — Guess {giver_name}'s {state['current_category']}! ({giver_name} can drop extra emoji hints live)",
            player_id=giver_id,
            player_name=giver_name,
            emoji=state["emoji_clue"],
        )
        save_game(self.code, state)
        await self._group_send(
            "game.guess_phase",
            emoji=state["emoji_clue"],
            guess_timer=s.get("guess_timer", 60),
            round=state["round_num"],
            max_rounds=len(order),
        )
        await self.broadcast_sync()

    # ========================================================================
    # Legacy Event Broadcasts & DB Queries
    # ========================================================================

    async def _rr_broadcast_emoji_phase(self, state: dict):
        cp = current_player_id(state)
        cp_info = state["players"].get(cp, {})
        cp_name = cp_info.get("name", "?")
        cp_channel = cp_info.get("channel_name") or (cp if cp and cp.startswith("specific.") else None)
        s = state.get("settings", {})
        await self._group_send(
            "game.emoji_phase",
            round=state["round_num"],
            max_rounds=s.get("max_rounds", 10),
            category=state["current_category"],
            word_length=len(state["current_word"] or ""),
            current_player=cp_name,
            players=player_list(state),
            emoji_timer=s.get("emoji_timer", 60),
        )
        if cp_channel:
            await self.channel_layer.send(
                cp_channel,
                {"type": "game.your_word", "word": state["current_word"], "category": state["current_category"]},
            )

    async def game_emoji_phase(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "emoji_phase"})

    async def game_guess_phase(self, event):
        await self.send_json({k: v for k, v in event.items() if k != "type"} | {"type": "guess_phase"})

    async def game_your_word(self, event):
        await self.send_json({"type": "your_word", "word": event["word"], "category": event.get("category")})

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
    def _rr_get_words(self, state: dict):
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

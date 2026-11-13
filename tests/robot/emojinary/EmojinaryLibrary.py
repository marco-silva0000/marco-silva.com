"""Robot Framework Keyword Library for Emojinary Party Game Simulation.

Exposes human-readable DSL keywords for setting up Emojinary rooms, simulating
multi-player matches across Round Robin, Collective Prep, and Best Guess (Judge's Pick)
modes, and verifying player persistence, spoiler censoring, and round replay logs.
"""

import os
import sys
from typing import Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
os.environ.setdefault("SECRET_KEY", "robot-emojinary-test-secret")
os.environ.setdefault("USE_SQLITE", "1")
try:
    django.setup()
except Exception:
    pass

import emojinary.game_state as gs  # noqa: E402
from tests.robot.emojinary.EmojinarySimulator import EmojinarySimulator  # noqa: E402


class EmojinaryLibrary:
    """Robot Framework keyword library for Emojinary simulations."""

    ROBOT_LIBRARY_SCOPE = "TEST SUITE"

    def __init__(self):
        self.sim: Optional[EmojinarySimulator] = None
        self.saved_tokens: dict[str, str] = {}

    def _require_sim(self) -> EmojinarySimulator:
        if not self.sim:
            raise RuntimeError("Simulation not initialized. Call 'A New Emojinary Room' first.")
        return self.sim

    # =========================================================================
    # Room Setup, Player Identity & Admin Controls
    # =========================================================================

    def a_new_emojinary_room(
        self,
        code: str = "EMJSIM1",
        mode: str = "round_robin",
        **settings,
    ) -> None:
        """Initialize a fresh Emojinary game room with optional settings."""
        parsed_settings: dict[str, Any] = {}
        for k, v in settings.items():
            s_val = str(v)
            if s_val.lower() in ("true", "yes"):
                parsed_settings[k] = True
            elif s_val.lower() in ("false", "no"):
                parsed_settings[k] = False
            elif k == "categories":
                parsed_settings[k] = [c.strip() for c in s_val.split(",") if c.strip()]
            else:
                try:
                    parsed_settings[k] = int(s_val)
                except (ValueError, TypeError):
                    parsed_settings[k] = v

        self.sim = EmojinarySimulator(code=code, mode=mode, settings=parsed_settings)
        self.saved_tokens.clear()

    def player_joins_room(self, name: str, is_admin: bool = False) -> str:
        """Join a player into the active room and record their secret reconnect token."""
        sim = self._require_sim()
        admin_flag = str(is_admin).lower() in ("true", "1", "yes")
        player = sim.join_player(name=name, is_admin=admin_flag)
        self.saved_tokens[name] = player["token"]
        self.saved_tokens[player["id"]] = player["token"]
        return player["id"]

    def player_disconnects(self, name: str) -> None:
        """Simulate a WebSocket disconnect (e.g. mobile refresh or Wi-Fi drop)."""
        sim = self._require_sim()
        sim.disconnect_player(name)

    def player_reconnects_with_token(self, name: str, token_owner: Optional[str] = None) -> str:
        """Reconnect a player using their stored secret token on a brand-new WebSocket channel."""
        sim = self._require_sim()
        key = token_owner or name
        token = self.saved_tokens.get(key)
        if not token:
            pid = sim.get_pid(key)
            token = sim.state["players"][pid]["token"]
        player = sim.join_player(name=name, token=token)
        return player["id"]

    def player_renames_to(self, current_name: str, new_name: str) -> None:
        """Player requests a live self-service display name change."""
        sim = self._require_sim()
        pid = sim.get_pid(current_name)
        sim.send_action(pid, {"action": "rename", "name": new_name})
        if new_name in sim.name_to_id:
            self.saved_tokens[new_name] = sim.state["players"][pid]["token"]

    def host_transfers_admin_to(self, host_name: str, target_name: str) -> None:
        """Host grants admin rights to another player."""
        sim = self._require_sim()
        target_id = sim.get_pid(target_name)
        sim.send_action(host_name, {"action": "transfer_admin", "player_id": target_id})

    def player_toggles_spectator(self, actor_name: str, target_name: Optional[str] = None) -> None:
        """Toggle spectator mode for self (or target player if actor is Host)."""
        sim = self._require_sim()
        target_id = sim.get_pid(target_name) if target_name else sim.get_pid(actor_name)
        sim.send_action(actor_name, {"action": "toggle_spectator", "player_id": target_id})

    def host_kicks_player(self, host_name: str, target_name: str) -> None:
        """Host removes a player from the room."""
        sim = self._require_sim()
        target_id = sim.get_pid(target_name)
        sim.send_action(host_name, {"action": "kick_player", "player_id": target_id})

    def host_applies_preset(self, host_name: str, preset_key: str) -> None:
        """Host applies one of the room presets (standard, collective_fast, best_guess_party, speed_blitz)."""
        sim = self._require_sim()
        sim.send_action(host_name, {"action": "apply_preset", "preset": preset_key})

    def host_updates_settings(self, host_name: str, **settings) -> None:
        """Host updates room settings via WebSocket."""
        sim = self._require_sim()
        payload: dict[str, Any] = {"action": "settings"}
        for k, v in settings.items():
            s_val = str(v)
            if s_val.lower() in ("true", "yes"):
                payload[k] = True
            elif s_val.lower() in ("false", "no"):
                payload[k] = False
            elif k == "categories":
                payload[k] = [c.strip() for c in s_val.split(",") if c.strip()]
            else:
                try:
                    payload[k] = int(s_val)
                except (ValueError, TypeError):
                    payload[k] = v
        sim.send_action(host_name, payload)

    # =========================================================================
    # Gameplay Actions (Round Robin, Collective Prep, Best Guess)
    # =========================================================================

    def game_starts(self, host_name: Optional[str] = None) -> None:
        """Host starts the match."""
        sim = self._require_sim()
        actor = host_name or sim.state.get("creator") or next(iter(sim.state["players"].keys()))
        sim.send_action(actor, {"action": "start"})

    def force_current_secret_word(self, word: str, category: str = "movie") -> None:
        """Deterministic helper to pin the active round's secret word for scenario testing."""
        sim = self._require_sim()
        state = sim.refresh_state()
        state["current_word"] = word
        state["current_category"] = category
        gs.save_game(sim.code, state)
        sim.refresh_state()

    def force_collective_word_for_player(self, player_name: str, word: str, category: str = "movie") -> None:
        """Deterministic helper to pin a player's assigned word during Collective Prep."""
        sim = self._require_sim()
        pid = sim.get_pid(player_name)
        state = sim.refresh_state()
        if pid in state.get("collective_queue", {}):
            state["collective_queue"][pid]["word"] = word
            state["collective_queue"][pid]["category"] = category
            gs.save_game(sim.code, state)
            sim.refresh_state()

    def player_rerolls_word(self, player_name: str) -> None:
        """Active clue-giver (or prep player / judge) rerolls their secret word."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "reroll"})

    def player_sets_custom_word(self, player_name: str, custom_word: str) -> None:
        """Clue-giver sets a custom secret word (when allow_custom_words is enabled)."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "set_custom_word", "word": custom_word})

    def player_sets_emoji_clue(self, player_name: str, emoji: str) -> None:
        """Clue-giver updates their staged emoji clue."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "emoji", "emoji": emoji})

    def player_clears_emoji_clue(self, player_name: str) -> None:
        """Clue-giver clears their staged emoji clue (syncing empty string to server)."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "emoji", "emoji": ""})

    def player_reveals_clue(self, player_name: str, emoji: Optional[str] = None) -> None:
        """Clue-giver reveals their initial emoji clue to start the guessing phase."""
        sim = self._require_sim()
        payload: dict[str, Any] = {"action": "reveal"}
        if emoji is not None:
            payload["emoji"] = emoji
        sim.send_action(player_name, payload)

    def player_adds_extra_emoji_hint(self, player_name: str, emoji: str) -> None:
        """Word writer drops an additional progressive emoji hint live during the guess phase."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "add_hint", "emoji": emoji})

    def player_submits_collective_prep(self, player_name: str, emoji: str) -> None:
        """Player locks in their initial emoji clue during Collective Prep."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "submit_prep", "emoji": emoji})

    def player_sends_unified_chat(self, player_name: str, message: str) -> None:
        """Player submits text into the unified chat/guess input box."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "chat", "msg": message})

    def player_sends_prompt(self, judge_name: str, prompt: str) -> None:
        """Judge in Best Guess mode sets the round prompt."""
        sim = self._require_sim()
        sim.send_action(judge_name, {"action": "send_prompt", "prompt": prompt})

    def player_submits_best_guess_emoji(self, player_name: str, emoji: str) -> None:
        """Non-judge player submits their emoji entry in Best Guess mode."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "submit_emoji", "emoji": emoji})

    def judge_picks_best_emoji_winner(self, judge_name: str, winner_name: str) -> None:
        """Judge picks the winning player's emoji submission in Best Guess mode."""
        sim = self._require_sim()
        winner_id = sim.get_pid(winner_name)
        sim.send_action(judge_name, {"action": "pick_best", "winner": winner_id})

    def player_skips_round(self, player_name: str) -> None:
        """Active player or Host skips the current round."""
        sim = self._require_sim()
        sim.send_action(player_name, {"action": "skip"})

    def host_forces_advance(self, host_name: str) -> None:
        """Host force-advances a stuck phase or round."""
        sim = self._require_sim()
        sim.send_action(host_name, {"action": "force_advance"})

    def host_controls_timer(self, host_name: str, op: str, seconds: int = 15) -> None:
        """Host pauses, resumes, or adds time to the active timer."""
        sim = self._require_sim()
        sim.send_action(host_name, {"action": "timer_control", "op": op, "seconds": int(seconds)})

    def host_triggers_play_again(self, host_name: str) -> None:
        """Host resets the finished game back to the lobby for another match."""
        sim = self._require_sim()
        sim.send_action(host_name, {"action": "play_again"})

    # =========================================================================
    # State, Privacy, Chat & Replay Assertions
    # =========================================================================

    def phase_should_be(self, expected_phase: str) -> None:
        sim = self._require_sim()
        actual = sim.refresh_state().get("phase")
        if actual != expected_phase:
            raise AssertionError(f"Expected phase '{expected_phase}', got '{actual}'")

    def mode_should_be(self, expected_mode: str) -> None:
        sim = self._require_sim()
        actual = sim.refresh_state().get("mode")
        if actual != expected_mode:
            raise AssertionError(f"Expected mode '{expected_mode}', got '{actual}'")

    def round_number_should_be(self, expected_round: int) -> None:
        sim = self._require_sim()
        actual = int(sim.refresh_state().get("round_num", 0))
        if actual != int(expected_round):
            raise AssertionError(f"Expected round_num {expected_round}, got {actual}")

    def current_turn_player_should_be(self, expected_name: str) -> None:
        sim = self._require_sim()
        state = sim.refresh_state()
        cp = gs.current_player_id(state)
        actual = state.get("players", {}).get(cp, {}).get("name")
        if actual != expected_name:
            raise AssertionError(f"Expected current turn player '{expected_name}', got '{actual}'")

    def player_score_should_be(self, player_name: str, expected_score: int) -> None:
        sim = self._require_sim()
        pid = sim.get_pid(player_name)
        actual = int(sim.state["players"][pid]["score"])
        if actual != int(expected_score):
            raise AssertionError(f"Expected {player_name} score to be {expected_score}, got {actual}")

    def player_should_be_connected(self, player_name: str, expected: bool = True) -> None:
        sim = self._require_sim()
        pid = sim.get_pid(player_name)
        exp = str(expected).lower() in ("true", "1", "yes")
        actual = bool(sim.state["players"][pid].get("connected"))
        if actual != exp:
            raise AssertionError(f"Expected {player_name} connected={exp}, got {actual}")

    def player_should_be_admin(self, player_name: str, expected: bool = True) -> None:
        sim = self._require_sim()
        pid = sim.get_pid(player_name)
        exp = str(expected).lower() in ("true", "1", "yes")
        actual = bool(sim.state["players"][pid].get("is_admin"))
        if actual != exp:
            raise AssertionError(f"Expected {player_name} is_admin={exp}, got {actual}")

    def player_should_be_spectator(self, player_name: str, expected: bool = True) -> None:
        sim = self._require_sim()
        pid = sim.get_pid(player_name)
        exp = str(expected).lower() in ("true", "1", "yes")
        actual = bool(sim.state["players"][pid].get("is_spectator"))
        if actual != exp:
            raise AssertionError(f"Expected {player_name} is_spectator={exp}, got {actual}")

    def player_count_should_be(self, expected_count: int) -> None:
        sim = self._require_sim()
        actual = len(sim.refresh_state().get("players", {}))
        if actual != int(expected_count):
            raise AssertionError(f"Expected {expected_count} players, got {actual}")

    def emoji_clue_should_be(self, expected_emoji: str) -> None:
        sim = self._require_sim()
        actual = sim.refresh_state().get("emoji_clue", "")
        if actual != expected_emoji:
            raise AssertionError(f"Expected emoji_clue '{expected_emoji}', got '{actual}'")

    def hint_count_should_be(self, expected_count: int) -> None:
        sim = self._require_sim()
        actual = len(sim.refresh_state().get("emoji_hints", []))
        if actual != int(expected_count):
            raise AssertionError(f"Expected {expected_count} emoji_hints, got {actual}")

    def current_word_should_be(self, expected_word: str) -> None:
        sim = self._require_sim()
        actual = sim.refresh_state().get("current_word")
        if actual != expected_word:
            raise AssertionError(f"Expected current_word '{expected_word}', got '{actual}'")

    def sanitized_view_should_hide_secret_word_from(self, viewer_name: str) -> None:
        sim = self._require_sim()
        pid = sim.get_pid(viewer_name)
        view = gs.get_sanitized_player_view(sim.refresh_state(), pid)
        if view.get("current_word") is not None:
            raise AssertionError(f"Secret word leaked to {viewer_name}: {view.get('current_word')}")
        if not view.get("word_mask"):
            raise AssertionError(f"Expected non-empty word_mask for guesser {viewer_name}")

    def sanitized_view_should_show_secret_word_to(self, viewer_name: str, expected_word: Optional[str] = None) -> None:
        sim = self._require_sim()
        pid = sim.get_pid(viewer_name)
        view = gs.get_sanitized_player_view(sim.refresh_state(), pid)
        actual = view.get("current_word")
        if actual is None:
            raise AssertionError(f"Expected {viewer_name} to see secret word, but got None")
        if expected_word and actual != expected_word:
            raise AssertionError(f"Expected {viewer_name} to see '{expected_word}', got '{actual}'")

    def chat_log_should_contain(self, substring: str, viewer_name: Optional[str] = None) -> None:
        sim = self._require_sim()
        state = sim.refresh_state()
        if viewer_name:
            pid = sim.get_pid(viewer_name)
            entries = gs.get_sanitized_player_view(state, pid).get("chat_log", [])
        else:
            entries = state.get("chat_log", [])
        if not any(
            substring.lower() in ((e.get("text") or "") + " " + (e.get("emoji") or "")).lower() for e in entries
        ):
            texts = [e.get("text") or "" for e in entries]
            raise AssertionError(f"Chat log did not contain '{substring}'. Entries: {texts}")

    def chat_log_should_not_contain(self, substring: str, viewer_name: Optional[str] = None) -> None:
        sim = self._require_sim()
        state = sim.refresh_state()
        if viewer_name:
            pid = sim.get_pid(viewer_name)
            entries = gs.get_sanitized_player_view(state, pid).get("chat_log", [])
        else:
            entries = state.get("chat_log", [])
        if any(substring.lower() in (e.get("text") or "").lower() for e in entries):
            raise AssertionError(f"Chat log unexpectedly contained '{substring}'")

    def timer_should_be_paused(self, expected: bool = True) -> None:
        sim = self._require_sim()
        state = sim.refresh_state()
        exp = str(expected).lower() in ("true", "1", "yes")
        is_paused = state.get("timer_paused_remaining") is not None
        if is_paused != exp:
            raise AssertionError(f"Expected timer paused={exp}, got {is_paused}")

    def replay_history_count_should_be(self, expected_count: int) -> None:
        sim = self._require_sim()
        state = sim.refresh_state()
        r_count = len(state.get("rounds_history", []))
        h_count = len(state.get("history", []))
        if r_count != int(expected_count) or h_count != int(expected_count):
            raise AssertionError(
                f"Expected {expected_count} replay rounds, got rounds_history={r_count}, history={h_count}"
            )

    def replay_round_outcome_should_be(self, round_index: int, expected_outcome: str) -> None:
        sim = self._require_sim()
        rounds = sim.refresh_state().get("rounds_history", [])
        idx = int(round_index) - 1
        if idx < 0 or idx >= len(rounds):
            raise AssertionError(f"Round index {round_index} out of range (total={len(rounds)})")
        actual = rounds[idx].get("outcome")
        if actual != expected_outcome:
            raise AssertionError(f"Expected round {round_index} outcome '{expected_outcome}', got '{actual}'")

    def replay_round_attempt_count_should_be(self, round_index: int, expected_attempts: int) -> None:
        sim = self._require_sim()
        rounds = sim.refresh_state().get("rounds_history", [])
        idx = int(round_index) - 1
        actual = len(rounds[idx].get("attempts", []))
        if actual != int(expected_attempts):
            raise AssertionError(f"Expected round {round_index} to have {expected_attempts} attempts, got {actual}")

    def replay_round_hint_count_should_be(self, round_index: int, expected_hints: int) -> None:
        sim = self._require_sim()
        rounds = sim.refresh_state().get("rounds_history", [])
        idx = int(round_index) - 1
        actual = len(rounds[idx].get("emoji_hints", []))
        if actual != int(expected_hints):
            raise AssertionError(f"Expected round {round_index} to have {expected_hints} hints, got {actual}")

    def exported_replay_leaderboard_top_player_should_be(self, expected_name: str) -> None:
        sim = self._require_sim()
        replay = gs.export_game_replay(sim.refresh_state())
        lb = replay.get("leaderboard", [])
        if not lb or lb[0].get("name") != expected_name:
            raise AssertionError(f"Expected top leaderboard player '{expected_name}', got {lb}")

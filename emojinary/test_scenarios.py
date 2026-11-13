"""Scenario-level tests for Emojinary, driven by the headless EmojinarySimulator.

These complement `emojinary/tests.py` (engine + real WebSocket tests) by exercising
full multi-step game flows, permission boundaries, and edge cases through the same
consumer code paths the browser uses, without Redis or a channel layer.
The Robot Framework suites in `tests/robot/emojinary/` reuse the same simulator.
"""

import time

import pytest

import emojinary.game_state as gs
from tests.robot.emojinary.EmojinarySimulator import EmojinarySimulator


@pytest.fixture(autouse=True)
def _isolate_redis(db):
    yield
    gs._redis = None


def make_sim(players=("Marco", "Alice", "Bob"), mode="round_robin", **settings) -> EmojinarySimulator:
    sim = EmojinarySimulator(code=f"SC{int(time.time() * 1e6) % 10**6}", mode=mode, settings=settings or None)
    for name in players:
        sim.join_player(name)
    return sim


def pin_word(sim: EmojinarySimulator, word: str, category: str = "movie") -> None:
    state = sim.refresh_state()
    state["current_word"] = word
    state["current_category"] = category
    gs.save_game(sim.code, state)


def current_name(sim: EmojinarySimulator) -> str:
    state = sim.refresh_state()
    return state["players"][gs.current_player_id(state)]["name"]


def score(sim: EmojinarySimulator, name: str) -> int:
    return sim.refresh_state()["players"][sim.get_pid(name)]["score"]


# =============================================================================
# Permissions & lobby boundaries
# =============================================================================


class TestPermissionBoundaries:
    def test_first_joiner_is_host_and_others_are_not(self):
        sim = make_sim()
        assert sim.state["players"][sim.get_pid("Marco")]["is_admin"] is True
        assert sim.state["players"][sim.get_pid("Alice")]["is_admin"] is False

    def test_non_host_cannot_start_game(self):
        sim = make_sim()
        sim.send_action("Alice", {"action": "start"})
        assert sim.state["phase"] == "lobby"
        assert sim.get_conn("Alice").last_error

    def test_start_requires_two_players(self):
        sim = make_sim(players=("Marco",))
        sim.send_action("Marco", {"action": "start"})
        assert sim.state["phase"] == "lobby"
        assert sim.state["started"] is False

    def test_non_host_cannot_change_settings_kick_or_transfer(self):
        sim = make_sim()
        sim.send_action("Alice", {"action": "settings", "max_rounds": 3, "mode": "best_guess"})
        assert sim.state["mode"] == "round_robin"
        assert sim.state["settings"]["max_rounds"] == gs.DEFAULT_SETTINGS["max_rounds"]

        sim.send_action("Alice", {"action": "kick_player", "player_id": sim.get_pid("Bob")})
        assert len(sim.state["players"]) == 3

        sim.send_action("Alice", {"action": "transfer_admin", "player_id": sim.get_pid("Bob")})
        assert sim.state["players"][sim.get_pid("Bob")]["is_admin"] is False

    def test_non_host_cannot_toggle_another_players_spectator(self):
        sim = make_sim()
        sim.send_action("Alice", {"action": "toggle_spectator", "player_id": sim.get_pid("Bob")})
        assert sim.state["players"][sim.get_pid("Bob")]["is_spectator"] is False

    def test_host_cannot_kick_self(self):
        sim = make_sim()
        sim.send_action("Marco", {"action": "kick_player", "player_id": sim.get_pid("Marco")})
        assert len(sim.state["players"]) == 3

    def test_settings_are_clamped_and_validated(self):
        sim = make_sim()
        sim.send_action(
            "Marco",
            {"action": "settings", "max_rounds": 999, "emoji_timer": -5, "chat_mode": "bogus", "mode": "nope"},
        )
        s = sim.state["settings"]
        assert s["max_rounds"] == 50
        assert s["emoji_timer"] == 0
        assert s["chat_mode"] == "public"
        assert sim.state["mode"] == "round_robin"

    def test_non_admin_cannot_skip_others_turn_before_timer_expires(self):
        sim = make_sim(emoji_timer=60)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Alice", {"action": "skip"})
        assert sim.state["phase"] == "emoji"
        assert sim.state["round_num"] == 1


# =============================================================================
# Identity persistence
# =============================================================================


class TestIdentityScenarios:
    def test_reconnect_with_token_keeps_same_id_score_and_host_flag(self):
        sim = make_sim(max_rounds=2)
        marco_token = sim.state["players"][sim.get_pid("Marco")]["token"]
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "E.T.")
        sim.send_action("Marco", {"action": "reveal", "emoji": "👽🚲"})
        sim.send_action("Alice", {"action": "chat", "msg": "et"})
        marco_score = score(sim, "Marco")

        sim.disconnect_player("Marco")
        assert sim.state["players"][sim.get_pid("Marco")]["connected"] is False

        rejoined = sim.join_player("Whatever", token=marco_token)
        assert rejoined["id"] == sim.get_pid("Marco")
        assert rejoined["score"] == marco_score
        assert rejoined["is_admin"] is True
        assert len(sim.state["players"]) == 3

    def test_join_with_unknown_token_creates_new_player(self):
        sim = make_sim(players=("Marco",))
        p = sim.join_player("Eve", token="not-a-real-token")
        assert p["id"] != sim.get_pid("Marco")
        assert len(sim.state["players"]) == 2

    def test_same_name_without_token_cannot_hijack_existing_player(self):
        """Regression: a new device typing the host's name must NOT inherit their seat or host rights."""
        sim = make_sim(players=("Marco", "Alice"))
        marco_id = sim.get_pid("Marco")
        imposter = sim.join_player("Marco")
        assert imposter["id"] != marco_id
        assert imposter["name"] != "Marco"
        assert imposter["is_admin"] is False
        assert sim.state["players"][marco_id]["is_admin"] is True
        names = [p["name"] for p in sim.state["players"].values()]
        assert len(names) == len(set(names)) == 3

    def test_imposter_with_host_name_cannot_use_host_actions(self):
        sim = make_sim(players=("Marco", "Alice"))
        imposter = sim.join_player("Marco")
        sim.send_action(imposter["id"], {"action": "kick_player", "player_id": sim.get_pid("Alice")})
        sim.send_action(imposter["id"], {"action": "settings", "max_rounds": 2})
        assert len(sim.state["players"]) == 3
        assert sim.state["settings"]["max_rounds"] == gs.DEFAULT_SETTINGS["max_rounds"]

    def test_rename_rejects_blank_and_collision_and_keeps_score(self):
        sim = make_sim()
        bob = sim.get_pid("Bob")
        sim.send_action("Bob", {"action": "rename", "name": "   "})
        assert sim.state["players"][bob]["name"] == "Bob"
        sim.send_action("Bob", {"action": "rename", "name": "alice"})
        assert sim.state["players"][bob]["name"] == "Bob"
        sim.send_action("Bob", {"action": "rename", "name": "Roberto"})
        assert sim.state["players"][bob]["name"] == "Roberto"


# =============================================================================
# Round Robin flows
# =============================================================================


class TestRoundRobinScenarios:
    def test_full_three_round_rotation_reaches_gameover_with_replay(self):
        sim = make_sim(max_rounds=3, end_on_first_guess=True)
        sim.send_action("Marco", {"action": "start"})
        expected_givers = ["Marco", "Alice", "Bob"]
        for rnd, giver in enumerate(expected_givers, start=1):
            assert sim.state["round_num"] == rnd
            assert current_name(sim) == giver
            pin_word(sim, f"Word {rnd}")
            sim.send_action(giver, {"action": "reveal", "emoji": "🎯"})
            guesser = next(n for n in expected_givers if n != giver)
            sim.send_action(guesser, {"action": "chat", "msg": f"word {rnd}"})
        assert sim.state["phase"] == "gameover"
        assert [r["word"] for r in sim.state["rounds_history"]] == ["Word 1", "Word 2", "Word 3"]
        assert all(r["outcome"] == "guessed" for r in sim.state["rounds_history"])
        replay = gs.export_game_replay(sim.state)
        assert len(replay["rounds_history"]) == 3
        assert replay["leaderboard"][0]["score"] >= replay["leaderboard"][-1]["score"]

    def test_words_never_repeat_within_a_match(self):
        sim = make_sim(max_rounds=6, end_on_first_guess=True)
        sim.send_action("Marco", {"action": "start"})
        seen = []
        while sim.state["phase"] != "gameover":
            seen.append(sim.state["current_word"])
            sim.send_action(current_name(sim), {"action": "skip"})
        assert len(seen) == 6
        assert len(set(seen)) == 6

    def test_clue_giver_cannot_guess_own_word_and_chat_is_censored(self):
        sim = make_sim()
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "Interstellar")
        sim.send_action("Marco", {"action": "reveal", "emoji": "🚀"})
        sim.send_action("Marco", {"action": "chat", "msg": "Interstellar"})
        assert score(sim, "Marco") == 0
        assert sim.state["guessed"] == []
        assert not any("Interstellar" in (e.get("text") or "") for e in sim.state["chat_log"])

    def test_reveal_with_empty_clue_is_rejected(self):
        sim = make_sim()
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "reveal", "emoji": ""})
        assert sim.state["phase"] == "emoji"
        assert "emoji" in (sim.get_conn("Marco").last_error or "").lower()

    def test_non_clue_giver_cannot_set_emoji_or_add_hints(self):
        sim = make_sim()
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Alice", {"action": "emoji", "emoji": "💩"})
        assert sim.state["emoji_clue"] == ""
        sim.send_action("Marco", {"action": "reveal", "emoji": "🦁"})
        sim.send_action("Alice", {"action": "add_hint", "emoji": "💩"})
        assert len(sim.state["emoji_hints"]) == 1

    def test_add_hint_only_allowed_during_guess_phase(self):
        sim = make_sim()
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "add_hint", "emoji": "🌅"})
        assert sim.state["emoji_hints"] == []

    def test_hints_are_ordered_and_timestamped_in_replay(self):
        sim = make_sim(max_rounds=1, end_on_first_guess=True)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "The Lion King")
        sim.send_action("Marco", {"action": "reveal", "emoji": "🦁"})
        sim.send_action("Marco", {"action": "add_hint", "emoji": "👑"})
        sim.send_action("Marco", {"action": "add_hint", "emoji": "🌅"})
        sim.send_action("Alice", {"action": "chat", "msg": "lion king"})
        hints = sim.state["rounds_history"][0]["emoji_hints"]
        assert [h["hint_num"] for h in hints] == [1, 2, 3]
        assert [h["emoji"] for h in hints] == ["🦁", "👑", "🌅"]
        assert all("elapsed_sec" in h for h in hints)

    def test_spectator_is_skipped_in_rotation_and_cannot_guess(self):
        sim = make_sim(max_rounds=2, end_on_first_guess=True)
        sim.send_action("Bob", {"action": "toggle_spectator"})
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "Piece of cake", "phrase")
        sim.send_action("Marco", {"action": "reveal", "emoji": "🍰"})
        sim.send_action("Bob", {"action": "chat", "msg": "piece of cake"})
        assert score(sim, "Bob") == 0
        assert sim.state["phase"] == "guess"
        sim.send_action("Alice", {"action": "chat", "msg": "piece of cake"})
        assert current_name(sim) == "Alice"

    def test_disconnected_guesser_does_not_block_round_end(self):
        sim = make_sim(max_rounds=2, end_on_first_guess=False)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "Time machine", "thing")
        sim.send_action("Marco", {"action": "reveal", "emoji": "⏳"})
        sim.disconnect_player("Bob")
        sim.send_action("Alice", {"action": "chat", "msg": "time machine"})
        assert sim.state["round_num"] == 2

    def test_guesser_can_only_score_once_per_round(self):
        sim = make_sim(max_rounds=1, end_on_first_guess=False)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "WALL-E")
        sim.send_action("Marco", {"action": "reveal", "emoji": "🤖"})
        sim.send_action("Alice", {"action": "chat", "msg": "walle"})
        first = score(sim, "Alice")
        sim.send_action("Alice", {"action": "guess", "guess": "walle"})
        assert score(sim, "Alice") == first
        assert sim.state["guessed"].count(sim.get_pid("Alice")) == 1

    def test_reroll_limit_enforced(self):
        sim = make_sim(allow_rerolls=1)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "reroll"})
        assert sim.state["rerolls_used"] == 1
        sim.send_action("Marco", {"action": "reroll"})
        assert sim.state["rerolls_used"] == 1
        assert "reroll" in (sim.get_conn("Marco").last_error or "").lower()

    def test_custom_word_blocked_when_disabled_for_non_host_giver(self):
        sim = make_sim(max_rounds=2, allow_custom_words=False, end_on_first_guess=True)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "skip"})
        assert current_name(sim) == "Alice"
        before = sim.state["current_word"]
        sim.send_action("Alice", {"action": "set_custom_word", "word": "Secret Hack"})
        assert sim.state["current_word"] == before

    def test_category_filter_restricts_word_pool(self):
        sim = make_sim(max_rounds=3, categories=["song"])
        sim.send_action("Marco", {"action": "start"})
        assert sim.state["current_category"] == "song"

    def test_timer_expiry_lets_any_player_end_round_as_timeout(self):
        sim = make_sim(max_rounds=1, guess_timer=30)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "Birthday party", "thing")
        sim.send_action("Marco", {"action": "reveal", "emoji": "🎂"})
        state = sim.refresh_state()
        state["timer_ends_at"] = time.time() - 5
        gs.save_game(sim.code, state)
        sim.send_action("Alice", {"action": "skip"})
        assert sim.state["phase"] == "gameover"
        assert sim.state["rounds_history"][0]["outcome"] == "timeout"

    def test_skip_after_partial_guesses_counts_as_guessed(self):
        sim = make_sim(max_rounds=1, end_on_first_guess=False)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "E.T.")
        sim.send_action("Marco", {"action": "reveal", "emoji": "👽"})
        sim.send_action("Alice", {"action": "chat", "msg": "et"})
        sim.send_action("Marco", {"action": "skip"})
        assert sim.state["rounds_history"][0]["outcome"] == "guessed"
        assert len(sim.state["rounds_history"]) == 1

    def test_kicking_current_clue_giver_mid_round_does_not_crash(self):
        sim = make_sim(players=("Marco", "Alice", "Bob", "Cara"), max_rounds=3)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "skip"})
        assert current_name(sim) == "Alice"
        sim.send_action("Marco", {"action": "kick_player", "player_id": sim.get_pid("Alice")})
        state = sim.refresh_state()
        assert "Alice" not in [p["name"] for p in state["players"].values()]
        cp = gs.current_player_id(state)
        assert cp in state["players"]


# =============================================================================
# Privacy of sanitized views
# =============================================================================


class TestSanitizedViewPrivacy:
    def test_secret_word_hidden_from_guessers_and_revealed_at_gameover(self):
        sim = make_sim(max_rounds=1, end_on_first_guess=True)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "Stranger Things", "tvshow")
        alice_view = gs.get_sanitized_player_view(sim.refresh_state(), sim.get_pid("Alice"))
        assert alice_view["current_word"] is None
        assert "(8, 6)" in alice_view["word_mask"]
        marco_view = gs.get_sanitized_player_view(sim.state, sim.get_pid("Marco"))
        assert marco_view["current_word"] == "Stranger Things"

        sim.send_action("Marco", {"action": "reveal", "emoji": "🚲🧇"})
        sim.send_action("Alice", {"action": "chat", "msg": "stranger things"})
        assert sim.state["phase"] == "gameover"
        assert sim.state["rounds_history"][0]["word"] == "Stranger Things"

    def test_spectator_view_never_contains_secret_word(self):
        sim = make_sim()
        sim.send_action("Bob", {"action": "toggle_spectator"})
        sim.send_action("Marco", {"action": "start"})
        view = gs.get_sanitized_player_view(sim.refresh_state(), sim.get_pid("Bob"))
        assert view["current_word"] is None

    def test_collective_prep_players_only_see_their_own_word(self):
        sim = make_sim(mode="collective", max_rounds=3)
        sim.send_action("Marco", {"action": "start"})
        state = sim.refresh_state()
        q = state["collective_queue"]
        for name in ("Marco", "Alice", "Bob"):
            view = gs.get_sanitized_player_view(state, sim.get_pid(name))
            assert view["current_word"] == q[sim.get_pid(name)]["word"]
        words = {q[pid]["word"] for pid in q}
        assert len(words) == 3


# =============================================================================
# Collective Prep flows
# =============================================================================


class TestCollectiveScenarios:
    def test_prep_requires_emoji_and_cannot_be_resubmitted(self):
        sim = make_sim(mode="collective", max_rounds=3)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Alice", {"action": "submit_prep", "emoji": ""})
        assert sim.state["collective_queue"][sim.get_pid("Alice")]["submitted"] is False
        sim.send_action("Alice", {"action": "submit_prep", "emoji": "👽"})
        sim.send_action("Alice", {"action": "submit_prep", "emoji": "💩"})
        assert sim.state["collective_queue"][sim.get_pid("Alice")]["emoji_clue"] == "👽"

    def test_prep_reroll_changes_only_own_word(self):
        sim = make_sim(mode="collective", max_rounds=3, allow_rerolls=2)
        sim.send_action("Marco", {"action": "start"})
        q = sim.state["collective_queue"]
        bob_before = q[sim.get_pid("Bob")]["word"]
        sim.send_action("Alice", {"action": "reroll"})
        q = sim.state["collective_queue"]
        assert q[sim.get_pid("Alice")]["rerolls_used"] == 1
        assert q[sim.get_pid("Bob")]["word"] == bob_before

    def test_only_writer_can_add_hint_during_their_round(self):
        sim = make_sim(mode="collective", max_rounds=3)
        sim.send_action("Marco", {"action": "start"})
        for name, em in (("Marco", "🦁"), ("Alice", "👽"), ("Bob", "🤖")):
            sim.send_action(name, {"action": "submit_prep", "emoji": em})
        assert sim.state["phase"] == "guess"
        writer = current_name(sim)
        other = next(n for n in ("Marco", "Alice", "Bob") if n != writer)
        sim.send_action(other, {"action": "add_hint", "emoji": "💩"})
        assert len(sim.state["emoji_hints"]) == 1
        sim.send_action(writer, {"action": "add_hint", "emoji": "✨"})
        assert len(sim.state["emoji_hints"]) == 2

    def test_skipping_every_collective_round_finishes_with_full_history(self):
        sim = make_sim(mode="collective", max_rounds=3)
        sim.send_action("Marco", {"action": "start"})
        for name, em in (("Marco", "🦁"), ("Alice", "👽"), ("Bob", "🤖")):
            sim.send_action(name, {"action": "submit_prep", "emoji": em})
        while sim.state["phase"] != "gameover":
            sim.send_action("Marco", {"action": "skip"})
        assert len(sim.state["rounds_history"]) == 3
        assert {r["outcome"] for r in sim.state["rounds_history"]} == {"skipped"}


# =============================================================================
# Best Guess flows
# =============================================================================


class TestBestGuessScenarios:
    def _to_submitting(self, sim):
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "send_prompt", "prompt": "Rainy Day"})
        assert sim.state["phase"] == "submitting"

    def test_judge_cannot_submit_and_resubmission_overwrites(self):
        sim = make_sim(mode="best_guess", max_rounds=1)
        self._to_submitting(sim)
        sim.send_action("Marco", {"action": "submit_emoji", "emoji": "🌧️"})
        assert sim.get_pid("Marco") not in sim.state["submissions"]
        sim.send_action("Alice", {"action": "submit_emoji", "emoji": "☔"})
        sim.send_action("Alice", {"action": "submit_emoji", "emoji": "🌂"})
        assert sim.state["submissions"][sim.get_pid("Alice")] == "🌂"
        alice_attempts = [a for a in sim.state["current_attempts"] if a["player_id"] == sim.get_pid("Alice")]
        assert len(alice_attempts) == 1

    def test_only_judge_can_pick_and_invalid_winner_ignored(self):
        sim = make_sim(mode="best_guess", max_rounds=1)
        self._to_submitting(sim)
        sim.send_action("Alice", {"action": "submit_emoji", "emoji": "☔"})
        sim.send_action("Bob", {"action": "submit_emoji", "emoji": "🌧️"})
        assert sim.state["phase"] == "judging"
        sim.send_action("Alice", {"action": "pick_best", "winner": sim.get_pid("Alice")})
        assert sim.state["phase"] == "judging"
        sim.send_action("Marco", {"action": "pick_best", "winner": "p_999"})
        assert sim.state["phase"] == "judging"
        sim.send_action("Marco", {"action": "pick_best", "winner": sim.get_pid("Bob")})
        assert sim.state["phase"] == "gameover"
        rnd = sim.state["rounds_history"][0]
        assert rnd["outcome"] == "judged"
        assert rnd["guesser"] == "Bob"
        winners = [a for a in rnd["attempts"] if a["outcome"] == "winner"]
        assert len(winners) == 1 and winners[0]["player_name"] == "Bob"

    def test_non_judge_cannot_send_prompt(self):
        sim = make_sim(mode="best_guess", max_rounds=1)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Bob", {"action": "send_prompt", "prompt": "Hijack"})
        assert sim.state["phase"] == "picking"


# =============================================================================
# Lifecycle
# =============================================================================


class TestLifecycleScenarios:
    def test_play_again_keeps_players_and_resets_scores_history(self):
        sim = make_sim(max_rounds=1, end_on_first_guess=True)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "E.T.")
        sim.send_action("Marco", {"action": "reveal", "emoji": "👽"})
        sim.send_action("Alice", {"action": "chat", "msg": "et"})
        assert sim.state["phase"] == "gameover"
        sim.send_action("Marco", {"action": "play_again"})
        state = sim.refresh_state()
        assert state["phase"] == "lobby"
        assert len(state["players"]) == 3
        assert all(p["score"] == 0 for p in state["players"].values())
        assert state["rounds_history"] == []
        # Restarting begins a fresh word pool for the new match
        sim.send_action("Marco", {"action": "start"})
        assert sim.state["used_words"] == [sim.state["current_word"]]

    def test_timer_pause_freezes_remaining_and_resume_restores(self):
        sim = make_sim(emoji_timer=60)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Marco", {"action": "timer_control", "op": "pause"})
        paused = sim.state["timer_paused_remaining"]
        assert paused is not None and 0 < paused <= 60
        sim.send_action("Marco", {"action": "timer_control", "op": "add_time", "seconds": 15})
        assert sim.state["timer_paused_remaining"] >= paused + 14
        sim.send_action("Marco", {"action": "timer_control", "op": "resume"})
        assert sim.state["timer_paused_remaining"] is None
        assert sim.state["timer_ends_at"] > time.time() + 60

    def test_non_host_cannot_control_timer(self):
        sim = make_sim(emoji_timer=60)
        sim.send_action("Marco", {"action": "start"})
        sim.send_action("Alice", {"action": "timer_control", "op": "pause"})
        assert sim.state["timer_paused_remaining"] is None


# =============================================================================
# Clue-Giver Word Visibility (CSS/HTML + WebSocket State Regression)
# =============================================================================


class TestClueGiverWordVisibility:
    def test_template_your_word_box_not_hidden_by_css_rule(self):
        """Regression: show() sets style.display = '', which cannot override a CSS display:none rule."""
        import re
        from pathlib import Path

        html = (Path(__file__).resolve().parent.parent / "templates" / "emojinary" / "game.html").read_text()
        style_match = re.search(r"\{%\s*block\s+extra_css\s*%\}(.*?)\{%\s*endblock\s*%\}", html, re.DOTALL)
        assert style_match is not None
        style_block = style_match.group(1)

        for elem_id in ("your-word-box", "timer-badge"):
            rule_match = re.search(rf"#{elem_id}\s*\{{([^}}]*)\}}", style_block, re.DOTALL)
            assert rule_match is not None, f"#{elem_id} CSS rule missing"
            assert not re.search(r"display\s*:\s*none", rule_match.group(1)), (
                f"#{elem_id} must not have display:none in CSS or show('{elem_id}') will leave it hidden!"
            )
            assert re.search(rf'id="{elem_id}"[^>]*style="[^"]*display\s*:\s*none', html), (
                f"#{elem_id} should start hidden via inline style so show('{elem_id}') can reveal it"
            )

    def test_clue_giver_receives_word_in_state_and_your_word_across_turns(self):
        sim = make_sim(mode="round_robin", max_rounds=3)
        sim.send_action("Marco", {"action": "start"})

        # Round 1: Marco is clue-giver
        marco_state = gs.get_sanitized_player_view(sim.state, viewer_id=sim.get_pid("Marco"))
        assert marco_state["phase"] == "emoji"
        assert marco_state["me"]["is_turn"] is True
        assert marco_state["current_word"]
        assert marco_state["current_word"] == sim.state["current_word"]
        for other in ("Alice", "Bob"):
            other_state = gs.get_sanitized_player_view(sim.state, viewer_id=sim.get_pid(other))
            assert other_state["me"]["is_turn"] is False
            assert other_state["current_word"] is None

        # Finish Round 1 -> Round 2: Alice becomes clue-giver
        secret_r1 = sim.state["current_word"]
        sim.send_action("Marco", {"action": "reveal", "emoji": "🦁"})
        sim.send_action("Alice", {"action": "chat", "msg": secret_r1})
        sim.send_action("Bob", {"action": "chat", "msg": secret_r1})

        alice_state = gs.get_sanitized_player_view(sim.state, viewer_id=sim.get_pid("Alice"))
        assert alice_state["phase"] == "emoji"
        assert alice_state["me"]["is_turn"] is True
        assert alice_state["current_word"]
        assert alice_state["current_word"] == sim.state["current_word"]
        assert gs.get_sanitized_player_view(sim.state, viewer_id=sim.get_pid("Marco"))["current_word"] is None
        assert gs.get_sanitized_player_view(sim.state, viewer_id=sim.get_pid("Bob"))["current_word"] is None

    def test_export_replay_does_not_leak_active_word_or_private_guesses(self):
        import json

        sim = make_sim(mode="round_robin", chat_mode="private", max_rounds=3)
        sim.send_action("Marco", {"action": "start"})
        pin_word(sim, "Jurassic Park")
        sim.send_action("Marco", {"action": "reveal", "emoji": "🦖"})
        sim.send_action("Alice", {"action": "chat", "msg": "Dino Land"})

        dumped = json.dumps(gs.export_game_replay(sim.state))
        assert "Jurassic Park" not in dumped
        assert "Dino Land" not in dumped

        # Collective prep phase: queued words must not appear in replay export either
        csim = make_sim(mode="collective", max_rounds=3)
        csim.send_action("Marco", {"action": "start"})
        queued_words = [q["word"] for q in csim.state["collective_queue"].values()]
        assert queued_words
        cdumped = json.dumps(gs.export_game_replay(csim.state))
        for w in queued_words:
            assert w not in cdumped

    def test_host_can_end_game_early_and_non_host_cannot(self):
        sim = make_sim(mode="round_robin", max_rounds=5)
        sim.send_action("Marco", {"action": "start"})
        assert sim.state["phase"] == "emoji"

        # Non-host cannot end game
        sim.send_action("Alice", {"action": "end_game"})
        assert sim.state["phase"] == "emoji"
        assert sim.state["status"] == "playing"

        # Host ends game early
        sim.send_action("Marco", {"action": "end_game"})
        assert sim.state["phase"] == "gameover"
        assert sim.state["status"] == "finished"
        assert sim.state["timer_ends_at"] is None
        assert sim.state["timer_paused_remaining"] is None

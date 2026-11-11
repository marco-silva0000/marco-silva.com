"""Robot Framework Keyword Library for Lupus In Tabula Game Simulation.

Exposes clean, human-readable DSL keywords for setting up scenarios, executing
multi-phase night and day actions, and asserting player lifecycle states and game outcomes.
"""

import os
import sys
from typing import Optional

# Ensure project root is available for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.robot.lupus.LupusSimulator import LupusSimulator  # noqa: E402


class LupusLibrary:
    """Robot Framework keyword library for Lupus simulations."""

    ROBOT_LIBRARY_SCOPE = "TEST SUITE"

    def __init__(self):
        self.sim: Optional[LupusSimulator] = None

    def a_new_game(
        self,
        code: str = "SIM1",
        theme: str = "werewolf",
        **settings,
    ) -> None:
        """Initialize a fresh Lupus game session with custom settings."""
        # Clean boolean strings from Robot Framework (${TRUE}, ${FALSE})
        parsed_settings = {}
        for k, v in settings.items():
            if str(v).lower() == "true":
                parsed_settings[k] = True
            elif str(v).lower() == "false":
                parsed_settings[k] = False
            elif str(v).lower() == "none":
                parsed_settings[k] = None
            else:
                try:
                    parsed_settings[k] = int(v)
                except (ValueError, TypeError):
                    parsed_settings[k] = v

        self.sim = LupusSimulator(code=code, theme=theme, settings=parsed_settings)

    def player_joins_as(
        self,
        name: str,
        role: Optional[str] = None,
        is_public_mayor: bool = False,
    ) -> str:
        """Register a player into the game with an optional role."""
        if not self.sim:
            raise RuntimeError("Simulation not initialized. Call 'A New Game' first.")
        is_pub = str(is_public_mayor).lower() in ("true", "1", "yes")
        return self.sim.add_player(
            name=name,
            role=role,
            preassigned=True,
            is_public_mayor=is_pub,
        )

    def game_starts(self, skip_night_zero: bool = True) -> None:
        """Transition from pre-game lobby to Night. Defaults to lethal Night 1 unless skip_night_zero is False."""
        skip = str(skip_night_zero).lower() not in ("false", "0", "no")
        self.sim.start_game(skip_night_zero=skip)

    def game_starts_with_night_zero(self) -> None:
        """Transition to peaceful introduction Night 0 (Cupid, Hacker, introductions)."""
        self.sim.start_game(skip_night_zero=False)

    def night_falls(self) -> None:
        """Transition from Day back to Night for the next round."""
        self.sim.advance_to_night()

    def wolves_attack(self, target_name: str) -> None:
        """Werewolves select their night victim."""
        success, msg = self.sim.record_night_action("wolves", target_name)
        if not success:
            raise AssertionError(f"Failed to record wolves attack: {msg}")

    def wolves_attack_with_rampage(self, target_1_name: str, target_2_name: str) -> None:
        """Enraged werewolves attack two victims during cub rampage."""
        t2_id = self.sim.get_pid(target_2_name)
        success, msg = self.sim.record_night_action(
            "wolves", target_1_name, extra={"target_id_2": t2_id}
        )
        if not success:
            raise AssertionError(f"Failed to record wolves rampage attack: {msg}")

    def martyrdom_primes_target(self, martyr_name: str, target_name: str) -> None:
        """Martyr primes their live grenade revenge on a chosen player."""
        m_id = self.sim.get_pid(martyr_name)
        t_id = self.sim.get_pid(target_name)
        from lupus.game_state import set_martyrdom_target
        success, msg = set_martyrdom_target(self.sim.state, m_id, t_id)
        if not success:
            raise AssertionError(f"Failed to prime martyrdom target: {msg}")

    def martyrdom_sets_night_target(self, target_name: str) -> None:
        """GM records martyrdom hidden booby trap night target."""
        success, msg = self.sim.record_night_action("martyrdom", target_name)
        if not success:
            raise AssertionError(f"Failed to record martyrdom night action: {msg}")

    def night_stage_should_be_active(self, stage_id: str, expected_active: bool = True) -> None:
        """Assert whether a night stage is alive / active vs dead bluff pause."""
        from lupus.game_state import get_night_stages
        stages = get_night_stages(self.sim.state)
        stg = next((s for s in stages if s["id"] == stage_id), None)
        if not stg:
            raise AssertionError(f"Stage '{stage_id}' not found in night stages.")
        expected_bool = str(expected_active).lower() in ("true", "1", "yes")
        if bool(stg.get("is_alive")) != expected_bool:
            raise AssertionError(
                f"Expected stage '{stage_id}' is_alive to be {expected_bool}, got {stg.get('is_alive')}"
            )

    def player_faction_should_be(self, player_name: str, expected_faction: str) -> None:
        """Assert player's active faction."""
        pid = self.sim.get_pid(player_name)
        player = self.sim.state["players"].get(pid, {})
        actual = player.get("faction")
        if actual != expected_faction:
            raise AssertionError(
                f"Expected {player_name} faction '{expected_faction}', got '{actual}'"
            )

    def doctor_protects(self, target_name: str) -> None:
        """Doctor protects target player."""
        success, msg = self.sim.record_night_action("doctor", target_name)
        if not success:
            raise AssertionError(f"Failed to record doctor protect: {msg}")

    def bodyguard_protects(self, target_name: str) -> None:
        """Bodyguard intercepts attacks targeting player."""
        success, msg = self.sim.record_night_action("bodyguard", target_name)
        if not success:
            raise AssertionError(f"Failed to record bodyguard protect: {msg}")

    def detective_inspects(self, target_name: str) -> None:
        """Detective inspects alignment of target player."""
        success, msg = self.sim.record_night_action("detective", target_name)
        if not success:
            raise AssertionError(f"Failed to record detective inspect: {msg}")

    def sniper_shoots(self, target_name: str, bullet_type: str = "danger") -> None:
        """Sniper fires at target with specified bullet type ('danger' or 'silver')."""
        success, msg = self.sim.record_night_action(
            "sniper", target_name, extra={"bullet_type": bullet_type}
        )
        if not success:
            raise AssertionError(f"Failed to record sniper shot: {msg}")

    def witch_revives_and_kills(
        self,
        revive_target: Optional[str] = None,
        kill_target: Optional[str] = None,
    ) -> None:
        """Witch uses potions (revive limbo player and/or poison living player)."""
        r_tgt = None if str(revive_target).lower() in ("none", "${none}", "") else revive_target
        k_tgt = None if str(kill_target).lower() in ("none", "${none}", "") else kill_target
        extra = {"revive_target": r_tgt, "kill_target": k_tgt}
        success, msg = self.sim.record_night_action("witch", extra=extra)
        if not success:
            raise AssertionError(f"Failed to record witch potions: {msg}")

    def death_angel_strikes(self, target_name: str) -> None:
        """Death Angel unleashes fatal unblockable strike."""
        success, msg = self.sim.record_night_action("death_angel", target_name)
        if not success:
            raise AssertionError(f"Failed to record death angel strike: {msg}")

    def saboteur_blocks(self, target_name: str) -> None:
        """Saboteur Wolf disables night power of target player."""
        success, msg = self.sim.record_night_action("saboteur_wolf", target_name)
        if not success:
            raise AssertionError(f"Failed to record saboteur action: {msg}")

    def disgruntled_ghost_haunts(self, target_name: str) -> None:
        """Disgruntled ghost haunts target player, suppressing active powers."""
        success, msg = self.sim.record_night_action("disgruntled_ghost", target_name)
        if not success:
            raise AssertionError(f"Failed to record disgruntled ghost action: {msg}")

    def mayor_vetoes_execution(self) -> None:
        """Mayor uses official executive veto during the night to pardon yesterday's lynched player."""
        success, msg = self.sim.record_night_action("mayor", extra={"veto": True})
        if not success:
            raise AssertionError(f"Failed to record mayor veto: {msg}")

    def serial_killer_attacks(self, target_name: str) -> None:
        """Serial Killer strikes target."""
        success, msg = self.sim.record_night_action("serial_killer", target_name)
        if not success:
            raise AssertionError(f"Failed to record serial killer attack: {msg}")

    def framer_frames(self, target_name: str) -> None:
        """Framer frames target to appear Evil to Detective."""
        success, msg = self.sim.record_night_action("framer", target_name)
        if not success:
            raise AssertionError(f"Failed to record framer action: {msg}")

    def silencer_silences(self, target_name: str) -> None:
        """Silencer silences target for the next day."""
        success, msg = self.sim.record_night_action("silencer", target_name)
        if not success:
            raise AssertionError(f"Failed to record silencer action: {msg}")

    def night_resolves(self) -> None:
        """Resolve all simultaneous night actions and calculate dawn results."""
        self.sim.resolve_night()

    def day_voting_begins(self, system: str = "two_stage_50pct") -> None:
        """Start day voting session with the specified system."""
        self.sim.start_voting_session(system=system)

    def player_nominates(self, voter_name: str, candidate_name: str) -> None:
        """Voter raises hand to nominate candidate."""
        success, msg = self.sim.nominate(voter_name, candidate_name)
        if not success:
            raise AssertionError(f"Failed to nominate: {msg}")

    def set_official_nominees(self, *nominee_names: str) -> None:
        """Set official ballot nominees directly."""
        self.sim.set_official_nominees(list(nominee_names))

    def proceed_to_final_vote(self) -> None:
        """Lock nominations and start final execution ballot."""
        success, msg = self.sim.proceed_to_final_vote()
        if not success:
            raise AssertionError(f"Failed to proceed to final vote: {msg}")

    def player_votes_for(self, voter_name: str, candidate_name: Optional[str] = None) -> None:
        """Cast final execution vote for candidate (or abstain if None)."""
        cand = None if str(candidate_name).lower() in ("none", "${none}", "") else candidate_name
        success, msg = self.sim.cast_final_vote(voter_name, cand)
        if not success:
            raise AssertionError(f"Failed to cast final vote: {msg}")

    def final_vote_is_tallied(self) -> str:
        """Tally final votes and apply execution or tie rules."""
        result, msg = self.sim.tally_vote()
        return result

    def limbo_player_guesses_angel(self, guesser_name: str, guessed_angel_name: str) -> None:
        """Limbo player attempts guess to be revived by living Angel."""
        self.sim.guess_limbo(guesser_name, guessed_angel_name)

    def player_status_should_be(self, player_name: str, expected_status: str) -> None:
        """Assert current status ('alive', 'limbo', 'dead') of player."""
        actual = self.sim.get_player_status(player_name)
        if actual != expected_status:
            raise AssertionError(
                f"Expected status of '{player_name}' to be '{expected_status}', but got '{actual}'"
            )

    def player_role_should_be(self, player_name: str, expected_role: str) -> None:
        """Assert current role of player (e.g. after Successor inheritance)."""
        actual = self.sim.get_player_role(player_name)
        if actual != expected_role:
            raise AssertionError(
                f"Expected role of '{player_name}' to be '{expected_role}', but got '{actual}'"
            )

    def winner_should_be(self, expected_winner: Optional[str]) -> None:
        """Assert game winner faction or role ('town', 'wolves', 'jester', 'serial_killer', or None)."""
        exp = None if str(expected_winner).lower() in ("none", "${none}", "") else expected_winner
        actual = self.sim.get_winner()
        if actual != exp:
            raise AssertionError(
                f"Expected winner to be '{exp}', but got '{actual}'"
            )

    def night_report_should_contain(self, substring: str) -> None:
        """Assert that dawn report contains the specified message snippet."""
        report = self.sim.get_night_report()
        found = any(substring.lower() in line.lower() for line in report)
        if not found:
            raise AssertionError(
                f"Night report did not contain '{substring}'. Full report:\n" + "\n".join(report)
            )

    def night_report_should_not_contain(self, substring: str) -> None:
        """Assert that dawn report does NOT contain the specified message snippet."""
        report = self.sim.get_night_report()
        found = any(substring.lower() in line.lower() for line in report)
        if found:
            raise AssertionError(
                f"Night report unexpectedly contained '{substring}'. Full report:\n" + "\n".join(report)
            )

    def player_status_is_set_to(self, player_name: str, new_status: str) -> None:
        """Directly adjust player status (e.g. placing player in 'limbo' or 'dead')."""
        self.sim.set_player_status(player_name, new_status)

    def event_log_should_contain(self, substring: str) -> None:
        """Assert that GM live events log contains the specified message snippet."""
        events = self.sim.get_events_log()
        found = any(substring.lower() in e.get("message", "").lower() for e in events)
        if not found:
            all_msgs = [e.get("message", "") for e in events]
            raise AssertionError(
                f"Event log did not contain '{substring}'. Full events log:\n" + "\n".join(all_msgs)
            )

    def detective_inspection_result_should_be(self, expected_result: str) -> None:
        """Assert Detective query result ('Good' or 'Evil')."""
        actual = self.sim.get_detective_result()
        if actual != expected_result:
            raise AssertionError(
                f"Expected Detective query result to be '{expected_result}', but got '{actual}'"
            )

    def player_should_be_silenced(self, player_name: str, expected_silenced: bool = True) -> None:
        """Assert whether player is currently silenced for day discussions."""
        exp = str(expected_silenced).lower() in ("true", "1", "yes")
        actual = self.sim.is_player_silenced(player_name)
        if actual != exp:
            raise AssertionError(
                f"Expected player '{player_name}' silenced state to be '{exp}', but got '{actual}'"
            )

    def return_to_lobby(self) -> None:
        """Return room back to pre-game lobby and archive finished game."""
        import lupus.game_state as gs
        self.sim.state = gs.return_to_lobby(self.sim.state)
        self.sim.refresh_state()

    def game_history_count_should_be(self, expected_count: int) -> None:
        """Assert number of archived games in room history."""
        actual = len(self.sim.state.get("game_history", []))
        if actual != int(expected_count):
            raise AssertionError(
                f"Expected {expected_count} archived games, but got {actual}"
            )

    def assign_midgame_role(self, player_name: str, role_id: str) -> None:
        """Assign role to mid-game joiner or convert player to midgame role."""
        success, msg = self.sim.assign_midgame_role(player_name, role_id)
        if not success:
            raise AssertionError(f"Failed to assign midgame role '{role_id}' to '{player_name}': {msg}")

    def pending_gameover_winner_should_be(self, expected_winner: Optional[str]) -> None:
        """Assert the winner recorded in pending_gameover record."""
        exp = None if str(expected_winner).lower() in ("none", "${none}", "") else expected_winner
        actual = self.sim.get_pending_gameover_winner()
        if actual != exp:
            raise AssertionError(
                f"Expected pending gameover winner to be '{exp}', but got '{actual}'"
            )

    def pending_gameover_should_be_none(self) -> None:
        """Assert that pending_gameover is cleared / None."""
        actual = self.sim.get_pending_gameover_winner()
        if actual is not None:
            raise AssertionError(
                f"Expected pending gameover to be None, but got '{actual}'"
            )

    def trigger_game_over(self, winner: Optional[str] = None) -> None:
        """GM explicitly triggers Game Over."""
        import lupus.game_state as gs
        w = None if str(winner).lower() in ("none", "${none}", "") else winner
        self.sim.state = gs.trigger_game_over(self.sim.state, winner=w)
        self.sim.refresh_state()

    def living_players_count_should_be(self, expected_count: int) -> None:
        """Assert count of currently alive players."""
        import lupus.game_state as gs
        actual = len(gs.get_living_players(self.sim.state))
        if actual != int(expected_count):
            raise AssertionError(
                f"Expected {expected_count} living players, but got {actual}"
            )

    def pair_lovers(
        self,
        lover_1_name: str,
        lover_2_name: str,
        lover_type: str = "innocent",
    ) -> None:
        """Pair two players as Lovers (innocent or obsessive)."""
        import lupus.game_state as gs
        p1_id = self.sim.get_pid(lover_1_name)
        p2_id = self.sim.get_pid(lover_2_name)
        self.sim.state["players"][p1_id]["lover_id"] = p2_id
        self.sim.state["players"][p1_id]["lover_type"] = lover_type
        self.sim.state["players"][p2_id]["lover_id"] = p1_id
        self.sim.state["players"][p2_id]["lover_type"] = lover_type
        gs.save_game(self.sim.code, self.sim.state)
        self.sim.refresh_state()

    def check_win_condition(self) -> Optional[str]:
        """Explicitly evaluate win condition on the current state."""
        import lupus.game_state as gs
        winner = gs.check_win_condition(self.sim.state)
        gs.save_game(self.sim.code, self.sim.state)
        self.sim.refresh_state()
        return winner

    def player_view_role_name_should_be(
        self, player_name: str, expected_name: str, lang: str = "en"
    ) -> None:
        """Verify that sanitized player view contains the localized role name."""
        import lupus.game_state as gs
        pid = self.sim.get_pid(player_name)
        view = gs.get_sanitized_player_view(self.sim.state, pid, lang=lang)
        actual_name = view.get("me", {}).get("role", {}).get("name")
        if actual_name != expected_name:
            raise AssertionError(
                f"Expected role name for '{player_name}' in lang '{lang}' to be '{expected_name}', got '{actual_name}'"
            )

    def player_view_status_display_should_be(
        self, player_name: str, expected_status_display: str, lang: str = "en"
    ) -> None:
        """Verify that sanitized player view contains the localized status display."""
        import lupus.game_state as gs
        pid = self.sim.get_pid(player_name)
        view = gs.get_sanitized_player_view(self.sim.state, pid, lang=lang)
        actual_status = view.get("me", {}).get("status_display")
        if actual_status != expected_status_display:
            raise AssertionError(
                f"Expected status_display for '{player_name}' in lang '{lang}' to be '{expected_status_display}', got '{actual_status}'"
            )

    def player_view_phase_display_should_be(
        self, player_name: str, expected_phase_display: str, lang: str = "en"
    ) -> None:
        """Verify that sanitized player view contains the localized phase display."""
        import lupus.game_state as gs
        pid = self.sim.get_pid(player_name)
        view = gs.get_sanitized_player_view(self.sim.state, pid, lang=lang)
        actual_phase = view.get("phase_display")
        if actual_phase != expected_phase_display:
            raise AssertionError(
                f"Expected phase_display for '{player_name}' in lang '{lang}' to be '{expected_phase_display}', got '{actual_phase}'"
            )

    def player_view_ui_string_should_be(
        self, player_name: str, key: str, expected_value: str, lang: str = "en"
    ) -> None:
        """Verify that sanitized player view contains the localized UI string."""
        import lupus.game_state as gs
        pid = self.sim.get_pid(player_name)
        view = gs.get_sanitized_player_view(self.sim.state, pid, lang=lang)
        actual_val = view.get("ui_strings", {}).get(key)
        if actual_val != expected_value:
            raise AssertionError(
                f"Expected UI string '{key}' in lang '{lang}' to be '{expected_value}', got '{actual_val}'"
            )

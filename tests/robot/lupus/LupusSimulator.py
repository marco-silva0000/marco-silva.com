"""Headless Lupus Game Simulator with In-Memory MockRedis backend.

Enables ultra-fast, deterministic, and dependency-free execution of multi-round
Lupus games for Robot Framework simulation testing and replay verification.
"""

from typing import Any, Optional

import lupus.game_state as gs


class MockRedis:
    """In-memory Redis mock implementing get/set/delete for game state."""

    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    def flushall(self) -> bool:
        self.store.clear()
        return True


class LupusSimulator:
    """Headless simulator that manipulates game states via lupus.game_state engine."""

    def __init__(
        self,
        code: str = "SIM1",
        theme: str = "werewolf",
        settings: Optional[dict[str, Any]] = None,
    ):
        self.mock_redis = MockRedis()
        gs._redis_client = self.mock_redis

        self.code = code.upper()
        self.theme = theme
        self.settings = settings or {}

        self.state = gs.create_initial_state(
            code=self.code,
            title=f"Simulation {self.code}",
            theme=self.theme,
            settings=self.settings,
        )

        self.name_to_id: dict[str, str] = {}
        self.id_to_name: dict[str, str] = {}

    def refresh_state(self) -> dict[str, Any]:
        loaded = gs.get_game(self.code)
        if loaded:
            self.state = loaded
        return self.state

    def get_pid(self, name_or_id: Optional[str]) -> Optional[str]:
        if not name_or_id:
            return None
        if name_or_id in self.name_to_id:
            return self.name_to_id[name_or_id]
        if name_or_id in self.state.get("players", {}):
            return name_or_id
        return name_or_id

    def get_player_name(self, name_or_id: Optional[str]) -> Optional[str]:
        if not name_or_id:
            return None
        if name_or_id in self.id_to_name:
            return self.id_to_name[name_or_id]
        if name_or_id in self.state.get("players", {}):
            return self.state["players"][name_or_id]["name"]
        return name_or_id

    def add_player(
        self,
        name: str,
        role: Optional[str] = None,
        preassigned: bool = True,
        is_public_mayor: bool = False,
    ) -> str:
        self.state, player = gs.add_player(self.state, name)
        pid = player["id"]
        self.name_to_id[name] = pid
        self.id_to_name[pid] = name

        if role:
            if preassigned:
                gs.set_preassigned_role(self.state, pid, role)
            else:
                gs.set_manual_player_role(self.state, pid, role)

            if role == "mayor":
                self.state["players"][pid]["is_public_mayor"] = is_public_mayor
                gs.save_game(self.code, self.state)

        self.refresh_state()
        return pid

    def set_manual_role(self, name: str, role: str) -> None:
        pid = self.get_pid(name)
        if pid:
            gs.set_manual_player_role(self.state, pid, role)
            self.refresh_state()

    def start_game(self, deck: Optional[list[str]] = None, skip_night_zero: bool = True) -> None:
        self.state = gs.start_game(self.state, deck)
        if skip_night_zero:
            self.state["is_night_zero"] = False
            self.state["round_number"] = 1
            gs.save_game(self.code, self.state)
        self.refresh_state()

    def advance_to_night(self) -> None:
        self.state = gs.advance_to_night(self.state)
        self.refresh_state()

    def record_night_action(
        self,
        stage_id: str,
        target_name_or_id: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        target_id = self.get_pid(target_name_or_id) if target_name_or_id else None

        # Resolve IDs inside extra payload (e.g. revive_target, kill_target, targets)
        resolved_extra = dict(extra) if extra else {}
        for rev_key in ("revive_target", "revive_id"):
            if rev_key in resolved_extra and resolved_extra[rev_key]:
                resolved_extra["revive_target"] = self.get_pid(resolved_extra[rev_key])
        for kill_key in ("kill_target", "kill_id"):
            if kill_key in resolved_extra and resolved_extra[kill_key]:
                resolved_extra["kill_target"] = self.get_pid(resolved_extra[kill_key])
        if "targets" in resolved_extra and resolved_extra["targets"]:
            resolved_extra["targets"] = [self.get_pid(t) for t in resolved_extra["targets"]]

        success, msg = gs.record_gm_night_action(
            self.state,
            stage_id=stage_id,
            target_id=target_id,
            extra=resolved_extra,
        )
        self.refresh_state()
        return success, msg

    def resolve_night(self) -> dict[str, Any]:
        self.state = gs.resolve_night(self.state)
        self.refresh_state()
        return self.state

    def start_voting_session(self, system: Optional[str] = None) -> None:
        self.state = gs.start_voting_session(self.state, system=system)
        self.refresh_state()

    def nominate(self, voter_name: str, candidate_name: str) -> tuple[bool, str]:
        voter_id = self.get_pid(voter_name)
        cand_id = self.get_pid(candidate_name)
        success, msg = gs.toggle_nomination_vote(self.state, voter_id, cand_id)
        self.refresh_state()
        return success, msg

    def set_official_nominees(self, candidate_names: list[str]) -> None:
        pids = [self.get_pid(c) for c in candidate_names]
        self.state.setdefault("voting", {})["nominated_player_ids"] = pids
        gs.save_game(self.code, self.state)
        self.refresh_state()

    def proceed_to_final_vote(self) -> tuple[bool, str]:
        success, msg = gs.proceed_to_final_vote(self.state)
        self.refresh_state()
        return success, msg

    def cast_final_vote(self, voter_name: str, candidate_name: Optional[str]) -> tuple[bool, str]:
        voter_id = self.get_pid(voter_name)
        cand_id = self.get_pid(candidate_name) if candidate_name else None
        success, msg = gs.cast_final_vote(self.state, voter_id, cand_id)
        self.refresh_state()
        return success, msg

    def tally_vote(self) -> tuple[str, str]:
        res, msg = gs.tally_and_resolve_vote(self.state)
        self.refresh_state()
        return res, msg

    def guess_limbo(self, guesser_name: str, guessed_angel_name: str) -> tuple[bool, str]:
        g_id = self.get_pid(guesser_name)
        a_id = self.get_pid(guessed_angel_name)
        success, msg = gs.guess_angel_in_limbo(self.state, g_id, a_id)
        self.refresh_state()
        return success, msg

    def set_player_status(self, name: str, status: str) -> None:
        pid = self.get_pid(name)
        if pid:
            gs.set_player_status(self.state, pid, status)
            self.refresh_state()

    def get_player_status(self, name: str) -> Optional[str]:
        self.refresh_state()
        pid = self.get_pid(name)
        return self.state.get("players", {}).get(pid, {}).get("status")

    def get_player_role(self, name: str) -> Optional[str]:
        self.refresh_state()
        pid = self.get_pid(name)
        return self.state.get("players", {}).get(pid, {}).get("role")

    def get_winner(self) -> Optional[str]:
        self.refresh_state()
        if self.state.get("winner"):
            return self.state["winner"]
        if self.state.get("pending_gameover"):
            return self.state["pending_gameover"].get("winner")
        return None

    def get_night_report(self) -> list[str]:
        self.refresh_state()
        return self.state.get("night_report", [])

    def get_events_log(self) -> list[dict[str, Any]]:
        self.refresh_state()
        return self.state.get("events_log", [])

    def get_detective_result(self) -> Optional[str]:
        self.refresh_state()
        return self.state.get("night_actions", {}).get("detective_query", {}).get("result")

    def is_player_silenced(self, name: str) -> bool:
        self.refresh_state()
        pid = self.get_pid(name)
        return bool(self.state.get("players", {}).get(pid, {}).get("is_silenced", False))

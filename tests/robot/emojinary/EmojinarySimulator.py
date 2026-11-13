"""Headless Emojinary Game Simulator with In-Memory MockRedis backend.

Enables ultra-fast, deterministic, and dependency-free execution of multi-round
Emojinary matches across all 3 game modes (`round_robin`, `collective`, `best_guess`)
for Robot Framework simulation testing and replay verification.
"""

from typing import Any, Optional

from asgiref.sync import async_to_sync

import emojinary.game_state as gs
from emojinary.consumers import EmojinaryConsumer

DEFAULT_SIM_WORDS = [
    ("The Lion King", "movie", 1),
    ("E.T.", "movie", 1),
    ("WALL-E", "movie", 2),
    ("Interstellar", "movie", 2),
    ("Spill the beans", "phrase", 1),
    ("Piece of cake", "phrase", 1),
    ("Bohemian Rhapsody", "song", 2),
    ("Stranger Things", "tvshow", 1),
    ("Birthday party", "thing", 1),
    ("Time machine", "thing", 2),
]


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


class _DummyChannelLayer:
    async def send(self, *args, **kwargs):
        pass

    async def group_send(self, *args, **kwargs):
        pass

    async def group_add(self, *args, **kwargs):
        pass

    async def group_discard(self, *args, **kwargs):
        pass


class SimulatedPlayerConnection(EmojinaryConsumer):
    """Lightweight headless consumer representing a single connected player."""

    def __init__(self, sim: "EmojinarySimulator", channel_name: str):
        super().__init__()
        self.sim = sim
        self.code = sim.code
        self.group_name = f"emojinary_{sim.code}"
        self.channel_name = channel_name
        self.channel_layer = _DummyChannelLayer()
        self.sent_messages: list[dict[str, Any]] = []
        self.last_error: Optional[str] = None

    async def broadcast_sync(self):
        pass

    async def _group_send(self, msg_type, **kwargs):
        pass

    async def send_json(self, content, close=False):
        self.sent_messages.append(content)
        if content.get("type") == "error":
            self.last_error = content.get("msg")

    async def _rr_get_words(self, state: dict) -> list[tuple[str, str]]:
        return self.sim.get_filtered_words(state)

    async def _bg_get_words(self, state: dict) -> list[tuple[str, str]]:
        return self.sim.get_filtered_words(state)


class EmojinarySimulator:
    """Headless simulator driving Emojinary games via EmojinaryConsumer and game_state."""

    def __init__(
        self,
        code: str = "EMJSIM1",
        mode: str = "round_robin",
        settings: Optional[dict[str, Any]] = None,
    ):
        self.mock_redis = MockRedis()
        gs._redis = self.mock_redis

        self.code = code.upper()
        self.word_pool = list(DEFAULT_SIM_WORDS)
        self.state = gs.create_initial_state(
            code=self.code,
            title=f"Simulation {self.code}",
            mode=mode,
            settings=settings,
        )
        gs.save_game(self.code, self.state)

        self.connections: dict[str, SimulatedPlayerConnection] = {}
        self.name_to_id: dict[str, str] = {}
        self.id_to_name: dict[str, str] = {}
        self._ch_seq = 1

    def get_filtered_words(self, state: dict) -> list[tuple[str, str]]:
        s = state.get("settings", {})
        diff = int(s.get("difficulty", 0) or 0)
        cats = s.get("categories", ["all"])
        filtered = []
        for text, cat, d in self.word_pool:
            if diff and d != diff:
                continue
            if cats and "all" not in cats and cat not in cats:
                continue
            filtered.append((text, cat))
        return filtered or [(w[0], w[1]) for w in self.word_pool]

    def refresh_state(self) -> dict[str, Any]:
        self.state = gs.get_game(self.code)
        for pid, p in self.state.get("players", {}).items():
            self.name_to_id[p["name"]] = pid
            self.id_to_name[pid] = p["name"]
        return self.state

    def get_pid(self, name_or_id: str) -> str:
        self.refresh_state()
        if name_or_id in self.state.get("players", {}):
            return name_or_id
        if name_or_id in self.name_to_id and self.name_to_id[name_or_id] in self.state.get("players", {}):
            return self.name_to_id[name_or_id]
        for pid, p in self.state.get("players", {}).items():
            if p["name"].lower() == name_or_id.lower():
                return pid
        raise KeyError(f"Player '{name_or_id}' not found in room {self.code}")

    def get_conn(self, name_or_id: str) -> SimulatedPlayerConnection:
        pid = self.get_pid(name_or_id)
        if pid not in self.connections:
            raise RuntimeError(f"No active connection for player '{name_or_id}' ({pid})")
        conn = self.connections[pid]
        conn.player_name = self.state["players"][pid]["name"]
        return conn

    def send_action(self, actor_name_or_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self.get_conn(actor_name_or_id)
        conn.last_error = None
        async_to_sync(conn.receive_json)(payload)
        return self.refresh_state()

    def join_player(
        self,
        name: str,
        token: Optional[str] = None,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        ch_name = f"sim_ch_{self._ch_seq}"
        self._ch_seq += 1
        conn = SimulatedPlayerConnection(self, ch_name)
        state = self.refresh_state()
        admin_token = state.get("admin_token") if is_admin else None
        async_to_sync(conn.receive_json)(
            {
                "action": "join",
                "name": name,
                "token": token,
                "admin_token": admin_token,
            }
        )
        self.refresh_state()
        pid = conn.player_id
        assert pid is not None
        self.connections[pid] = conn
        self.name_to_id[self.state["players"][pid]["name"]] = pid
        self.id_to_name[pid] = self.state["players"][pid]["name"]
        return self.state["players"][pid]

    def disconnect_player(self, name_or_id: str) -> None:
        conn = self.get_conn(name_or_id)
        async_to_sync(conn.disconnect)(1000)
        self.refresh_state()

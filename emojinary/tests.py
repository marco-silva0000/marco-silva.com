"""Comprehensive unit and async WebSocket tests for the revamped Emojinary party game."""

import json

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import Client
from django.urls import reverse

from emojinary.game_state import (
    add_player,
    build_word_mask,
    censor_spoilers,
    check_guess,
    create_initial_state,
    delete_game,
    get_game,
    kick_player,
    pick_unused_word,
    rename_player,
    save_game,
    toggle_spectator,
    transfer_admin,
)
from emojinary.models import EmojinaryWord
from gamerooms.models import Room
from website.asgi import application


class MockRedis:
    """In-memory dictionary mock for Redis to run tests without external daemon."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture(autouse=True)
def mock_redis_and_channels(monkeypatch, settings):
    r = MockRedis()
    monkeypatch.setattr("emojinary.game_state._get_redis", lambda: r)
    monkeypatch.setattr("emojinary.game_state.get_redis_client", lambda: r)
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
    return r


@pytest.fixture(autouse=True)
def seed_words(db):
    words = [
        ("The Lion King", "movie", 1),
        ("E.T.", "movie", 1),
        ("WALL-E", "movie", 2),
        ("Interstellar", "movie", 2),
        ("Birthday party", "thing", 1),
        ("Spill the beans", "phrase", 1),
    ]
    for text, cat, diff in words:
        EmojinaryWord.objects.get_or_create(text=text, defaults={"category": cat, "difficulty": diff})


@pytest.fixture
def clean_room(db):
    code = "EMJTEST1"
    delete_game(code)
    room = Room.objects.create(title="Emojinary Test Room", code=code, game_type="emojinary")
    yield room
    delete_game(code)


class TestEmojinaryPlayerIdentityAndRoomMechanics:
    def test_persistent_player_identity_and_reconnect_preserves_score(self, clean_room):
        state = create_initial_state(code=clean_room.code, title=clean_room.title)
        state, p1, is_new1 = add_player(state, "Marco", channel_name="ch_1")
        assert is_new1 is True
        assert p1["id"] == "p_1"
        assert p1["is_admin"] is True
        assert p1["token"]

        # Award points and simulate disconnect + reconnect on a new WebSocket channel
        state["players"]["p_1"]["score"] = 42
        state["players"]["p_1"]["connected"] = False
        state["players"]["p_1"]["channel_name"] = None
        save_game(clean_room.code, state)

        # Reconnect using token
        state, p1_reconn, is_new_reconn = add_player(state, "Marco", token=p1["token"], channel_name="ch_2")
        assert is_new_reconn is False
        assert p1_reconn["id"] == "p_1"
        assert p1_reconn["score"] == 42
        assert p1_reconn["connected"] is True
        assert p1_reconn["channel_name"] == "ch_2"

    def test_rename_player_updates_creator_and_rejects_collision(self, clean_room):
        state = create_initial_state(code=clean_room.code)
        state, p1, _ = add_player(state, "Alice")
        state, p2, _ = add_player(state, "Bob")

        # Cannot rename to existing player's name
        ok_dup, msg_dup = rename_player(state, p2["id"], "Alice")
        assert ok_dup is False
        assert "taken" in msg_dup.lower()

        # Valid rename updates creator name and logs to chat_log
        ok, new_name = rename_player(state, p1["id"], "Alicia")
        assert ok is True
        assert new_name == "Alicia"
        assert state["players"][p1["id"]]["name"] == "Alicia"
        assert state["creator"] == "Alicia"
        assert any("Alicia" in e["text"] for e in state["chat_log"])

    def test_admin_transfer_spectator_toggle_and_kick(self, clean_room):
        state = create_initial_state(code=clean_room.code)
        state, p1, _ = add_player(state, "HostUser")
        state, p2, _ = add_player(state, "PlayerTwo")
        state, p3, _ = add_player(state, "PlayerThree")

        assert p1["id"] in state["turn_order"]
        is_spec = toggle_spectator(state, p1["id"])
        assert is_spec is True
        assert p1["id"] not in state["turn_order"]

        # Toggle back to active player
        is_spec = toggle_spectator(state, p1["id"])
        assert is_spec is False
        assert p1["id"] in state["turn_order"]

        # Transfer admin to p2
        assert transfer_admin(state, p2["id"]) is True
        assert state["players"][p2["id"]]["is_admin"] is True

        # Kick p3
        removed = kick_player(state, p3["id"], by_name="HostUser")
        assert removed == "PlayerThree"
        assert p3["id"] not in state["players"]
        assert p3["id"] not in state["turn_order"]

    def test_views_qr_reconnect_and_replay_export(self, clean_room):
        client = Client()
        # Enter game view creates player session and renders QR codes
        url = reverse("gamerooms:emojinary:game", kwargs={"code": clean_room.code, "name": "Marco"})
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "data:image/png;base64," in content
        assert clean_room.code in content

        state = get_game(clean_room.code)
        p = next(iter(state["players"].values()))
        token = p["token"]

        # Personal QR JSON endpoint
        qr_url = reverse("gamerooms:emojinary:player-qr", kwargs={"code": clean_room.code, "token": token})
        qr_resp = client.get(qr_url)
        assert qr_resp.status_code == 200
        qr_data = qr_resp.json()
        assert "qr" in qr_data and "url" in qr_data

        # Personal Reconnect URL restores session on a fresh client
        fresh_client = Client()
        reconn_url = reverse("gamerooms:emojinary:reconnect", kwargs={"code": clean_room.code, "token": token})
        reconn_resp = fresh_client.get(reconn_url)
        assert reconn_resp.status_code == 302
        assert fresh_client.session.get(f"emojinary_player_{clean_room.code}") == token

        # Replay JSON export endpoint
        replay_url = reverse("gamerooms:emojinary:replay", kwargs={"code": clean_room.code})
        replay_resp = client.get(replay_url)
        assert replay_resp.status_code == 200
        replay_json = json.loads(replay_resp.content.decode())
        assert replay_json["code"] == clean_room.code
        assert replay_json["game"] == "emojinary"

    def test_qr_password_auto_auth_on_room_join(self, db):
        locked = Room.objects.create(title="Locked Emojinary", code="LCKEMJ01", password="1234", game_type="emojinary")
        client = Client()
        # Visiting with ?pwd=1234 bypasses password screen and goes straight to name screen
        join_url = reverse("gamerooms:room-join", kwargs={"code": locked.code}) + "?pwd=1234"
        resp = client.get(join_url)
        assert resp.status_code == 200
        assert 'name="name"' in resp.content.decode()

        # Short /games/emojinary/<code>/?pwd=1234 redirects preserving ?pwd=1234
        short_url = reverse("gamerooms:emojinary:join", kwargs={"code": locked.code}) + "?pwd=1234"
        short_resp = client.get(short_url)
        assert short_resp.status_code == 302
        assert "pwd=1234" in short_resp.headers["Location"]


class TestEmojinarySmartGuessAndSpoilerGuard:
    def test_article_and_punctuation_insensitive_matching(self):
        # Leading article tolerance
        assert check_guess({"current_word": "The Lion King"}, "Lion King") == (True, [])
        assert check_guess({"current_word": "The Lion King"}, "the lion king!") == (True, [])

        # Punctuation and hyphen tolerance
        assert check_guess({"current_word": "E.T."}, "et") == (True, [])
        assert check_guess({"current_word": "E.T."}, "e t") == (True, [])
        assert check_guess({"current_word": "WALL-E"}, "wall e") == (True, [])
        assert check_guess({"current_word": "WALL-E"}, "walle") == (True, [])

    def test_partial_word_and_typo_close_matches(self):
        # Partial word match
        correct, matches = check_guess({"current_word": "The Lion King"}, "King Kong")
        assert correct is False
        assert "king" in matches

        # Close spelling typo
        correct_typo, matches_typo = check_guess({"current_word": "Interstellar"}, "Interstelar")
        assert correct_typo is False
        assert len(matches_typo) > 0

    def test_spoiler_censor_and_word_mask(self):
        assert censor_spoilers("The answer is Lion King", "The Lion King") != "The answer is Lion King"
        assert "•••" in censor_spoilers("Wait is it lion?", "The Lion King")
        assert censor_spoilers("Lion King", "The Lion King") == "🔒 [spoiler blocked]"

        mask = build_word_mask("The Lion King")
        assert "(3, 4, 4)" in mask

    def test_non_repeating_word_picker(self):
        state = create_initial_state("POOLTEST")
        pool = [("Word A", "thing"), ("Word B", "thing"), ("Word C", "thing")]
        picked = {pick_unused_word(state, pool)[0] for _ in range(3)}
        assert picked == {"Word A", "Word B", "Word C"}


class TestEmojinaryWebSocketModesAndReplay:
    async def _connect_player(self, code: str, name: str, token: str = None, admin_token: str = None):
        comm = WebsocketCommunicator(application, f"/ws/emojinary/{code}/")
        connected, _ = await comm.connect()
        assert connected is True
        await comm.send_json_to({"action": "join", "name": name, "token": token, "admin_token": admin_token})
        # Drain initial messages until we get type == 'state'
        state_msg = None
        for _ in range(5):
            msg = await comm.receive_json_from(timeout=2)
            if msg.get("type") == "state":
                state_msg = msg
                if await comm.receive_nothing(timeout=0.05):
                    break
        return comm, state_msg

    async def _drain_until_state(self, comm: WebsocketCommunicator) -> dict:
        last_state = None
        for _ in range(10):
            if await comm.receive_nothing(timeout=0.05) and last_state is not None:
                break
            msg = await comm.receive_json_from(timeout=2)
            if msg.get("type") == "state":
                last_state = msg
        return last_state

    def test_round_robin_unified_chat_guesses_progressive_hints_and_replay(self, clean_room):
        @async_to_sync
        async def _run():
            code = clean_room.code
            c1, s1 = await self._connect_player(code, "Alice")
            c2, s2 = await self._connect_player(code, "Bob")
            await self._drain_until_state(c1)

            # Configure 1 round
            await c1.send_json_to({"action": "settings", "max_rounds": 1, "mode": "round_robin"})
            await self._drain_until_state(c1)
            await self._drain_until_state(c2)

            # Start game
            await c1.send_json_to({"action": "start"})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s1["phase"] == "emoji"
            assert s1["me"]["is_turn"] is True
            assert s1["current_word"] is not None
            # Guesser (Bob) must NOT see the secret word during active play
            assert s2["current_word"] is None
            assert s2["word_mask"] != ""

            secret_word = s1["current_word"]

            # Alice sets initial emoji clue and reveals
            await c1.send_json_to({"action": "emoji", "emoji": "🦁👑"})
            await c1.send_json_to({"action": "reveal"})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s2["phase"] == "guess"
            assert s2["emoji_clue"] == "🦁👑"

            # Alice (word writer) drops a live additional emoji hint during guessing!
            await c1.send_json_to({"action": "add_hint", "emoji": "🌅🐗"})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert len(s2["emoji_hints"]) == 2
            assert "🌅🐗" in s2["emoji_clue"]

            # Bob guesses wrong via the unified chat action
            await c2.send_json_to({"action": "chat", "msg": "Totally Wrong Movie"})
            s2 = await self._drain_until_state(c2)
            await self._drain_until_state(c1)

            # Bob guesses correctly via the unified chat action
            await c2.send_json_to({"action": "chat", "msg": secret_word})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)

            # Game over after 1 round; verify replay history and attempt log!
            assert s1["phase"] == "gameover"
            assert len(s1["rounds_history"]) == 1
            r_hist = s1["rounds_history"][0]
            assert r_hist["word"] == secret_word
            assert len(r_hist["emoji_hints"]) == 2
            assert len(r_hist["attempts"]) == 2
            assert r_hist["attempts"][0]["outcome"] == "wrong"
            assert r_hist["attempts"][1]["outcome"] == "correct"
            assert r_hist["guesser"] == "Bob"

            await c1.disconnect()
            await c2.disconnect()

        _run()

    def test_skip_records_single_history_entry(self, clean_room):
        @async_to_sync
        async def _run():
            code = clean_room.code
            c1, _ = await self._connect_player(code, "Alice")
            c2, _ = await self._connect_player(code, "Bob")
            await self._drain_until_state(c1)

            await c1.send_json_to({"action": "settings", "max_rounds": 1, "mode": "round_robin"})
            await self._drain_until_state(c1)
            await c1.send_json_to({"action": "start"})
            await self._drain_until_state(c1)

            # Skip round
            await c1.send_json_to({"action": "skip"})
            s1 = await self._drain_until_state(c1)
            assert s1["phase"] == "gameover"
            # Must only record 1 entry, not 2!
            assert len(s1["history"]) == 1
            assert len(s1["rounds_history"]) == 1
            assert s1["rounds_history"][0]["outcome"] == "skipped"

            await c1.disconnect()
            await c2.disconnect()

        _run()

    def test_collective_prep_mode_full_flow(self, clean_room):
        @async_to_sync
        async def _run():
            code = clean_room.code
            c1, _ = await self._connect_player(code, "Alice")
            c2, _ = await self._connect_player(code, "Bob")
            await self._drain_until_state(c1)

            await c1.send_json_to({"action": "settings", "mode": "collective", "max_rounds": 2})
            await self._drain_until_state(c1)
            await self._drain_until_state(c2)

            # Start Collective Mode -> enters 'prep' phase where BOTH players get secret words
            await c1.send_json_to({"action": "start"})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s1["phase"] == "prep"
            assert s2["phase"] == "prep"
            assert s1["current_word"] is not None
            assert s2["current_word"] is not None
            alice_word = s1["current_word"]
            bob_word = s2["current_word"]

            # Both lock in their initial emoji clues simultaneously
            await c1.send_json_to({"action": "submit_prep", "emoji": "🦁👑"})
            await self._drain_until_state(c1)
            await c2.send_json_to({"action": "submit_prep", "emoji": "👽🚲🌕"})

            # Automatically transitions to Round 1 'guess' phase for Alice's word!
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s1["phase"] == "guess"
            assert s2["emoji_clue"] == "🦁👑"

            # Alice adds an extra hint live during Round 1 guessing
            await c1.send_json_to({"action": "add_hint", "emoji": "🌅"})
            s2 = await self._drain_until_state(c2)
            assert "🌅" in s2["emoji_clue"]

            # Bob guesses Alice's word -> immediately launches Round 2 for Bob's word!
            await c2.send_json_to({"action": "chat", "msg": alice_word})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s1["phase"] == "guess"
            assert s1["round_num"] == 2
            assert s1["emoji_clue"] == "👽🚲🌕"

            # Alice guesses Bob's word -> gameover!
            await c1.send_json_to({"action": "chat", "msg": bob_word})
            s1 = await self._drain_until_state(c1)
            assert s1["phase"] == "gameover"
            assert len(s1["rounds_history"]) == 2

            await c1.disconnect()
            await c2.disconnect()

        _run()

    def test_best_guess_judges_pick_mode_flow(self, clean_room):
        @async_to_sync
        async def _run():
            code = clean_room.code
            c1, _ = await self._connect_player(code, "Alice")
            c2, _ = await self._connect_player(code, "Bob")
            await self._drain_until_state(c1)

            await c1.send_json_to({"action": "settings", "mode": "best_guess", "max_rounds": 1})
            await self._drain_until_state(c1)
            await c1.send_json_to({"action": "start"})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s1["phase"] == "picking"

            # Alice sends prompt (even if accidental button text is included, it gets stripped)
            await c1.send_json_to({"action": "send_prompt", "prompt": "Space Cow 🎲 reroll ✅ send"})
            s1 = await self._drain_until_state(c1)
            s2 = await self._drain_until_state(c2)
            assert s2["phase"] == "submitting"
            assert s2["current_word"] == "Space Cow"

            # Bob submits emoji
            await c2.send_json_to({"action": "submit_emoji", "emoji": "🚀🐄🌌"})
            s1 = await self._drain_until_state(c1)
            assert s1["phase"] == "judging"
            assert len(s1["submissions"]) == 1
            winner_id = s1["submissions"][0]["player_id"]

            # Alice picks Bob's submission
            await c1.send_json_to({"action": "pick_best", "winner": winner_id})
            s1 = await self._drain_until_state(c1)
            assert s1["phase"] == "gameover"
            assert len(s1["rounds_history"]) == 1
            assert s1["rounds_history"][0]["guesser"] == "Bob"
            assert s1["rounds_history"][0]["word"] == "Space Cow"

            await c1.disconnect()
            await c2.disconnect()

        _run()

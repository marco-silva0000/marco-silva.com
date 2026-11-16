"""Unit and integration test suite for 'Don't Say the Same Thing as Me' party game and Prompt Engine."""

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import Client, TestCase
from django.urls import reverse

from gamerooms.models import Room
from gamerooms.prompt_engine import (
    ALL_FRAMES,
    GOLD_PROMPTS,
    clean_answer_key,
    get_curated_deck,
    get_next_prompt,
    synthesize_prompt_from_frame,
    validate_player_answer,
)
from website.asgi import application

from .game_state import (
    DEFAULT_SETTINGS,
    add_player,
    advance_next_round,
    create_game,
    evaluate_and_reveal_round,
    find_player_by_name,
    find_player_by_token,
    get_game,
    get_sanitized_player_view,
    is_player_admin,
    reset_game,
    save_game,
    start_game,
    submit_answer,
    toggle_answer_validity,
    update_settings,
)


@pytest.fixture(autouse=True)
def mock_redis_and_channels(monkeypatch, settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
    # Fast test evaluator avoiding outbound Ollama timeouts during tests
    def _fast_eval(prompt_text, answer, sample_answers=None, obscurity_examples=None, use_ai=True):
        clean_ans = clean_answer_key(answer)
        if not clean_ans:
            return {"valid": False, "is_obscure": False, "source": "empty", "reason": "Empty"}
        is_obs = bool(obscurity_examples and any(clean_answer_key(o) == clean_ans for o in obscurity_examples))
        return {
            "valid": True,
            "is_obscure": is_obs,
            "source": "fast_test_eval",
            "reason": "Test verified",
            "pending_host_review": False,
        }

    monkeypatch.setattr("dontsay.game_state.validate_player_answer", _fast_eval)


@pytest.mark.django_db
class TestDontSayViewsAndRoomIntegration(TestCase):
    def test_create_and_join_dontsay_room(self):
        client = Client()
        resp = client.post(
            reverse("gamerooms:room-create"),
            {
                "title": "Anti-Hivemind Night",
                "password": "",
                "game_type": "dontsay",
                "language": "en",
                "captcha_answer": "10",
                "captcha_expected": "10",
            },
        )
        self.assertEqual(resp.status_code, 302)
        room = Room.objects.get(title="Anti-Hivemind Night")
        self.assertEqual(room.game_type, "dontsay")

        # Room list shows Don't Say card and active room
        list_resp = client.get(reverse("gamerooms:room-list"))
        self.assertEqual(list_resp.status_code, 200)
        content = list_resp.content.decode()
        self.assertIn("Don't Say", content.replace("&#x27;", "'").replace("&#39;", "'"))
        self.assertIn("Anti-Hivemind Night", content)

        # Join room redirects to game URL
        join_resp = client.post(reverse("gamerooms:room-join", args=[room.code]), {"name": "HostMarco"})
        self.assertEqual(join_resp.status_code, 302)
        self.assertIn(f"/games/dontsay/{room.code}/HostMarco/", join_resp["Location"])

        # Game page renders 200
        game_resp = client.get(join_resp["Location"])
        self.assertEqual(game_resp.status_code, 200)
        self.assertIn("HostMarco", game_resp.content.decode())

    def test_seat_reclaim_prevents_ghost_clones(self):
        code = "TESTDS01"
        state = create_game(code, title="Seat Test")
        state, p1, is_new1 = add_player(state, name="Marco", is_admin=True)
        self.assertTrue(is_new1)
        self.assertEqual(p1["name"], "Marco")
        self.assertTrue(p1["is_admin"])

        # Second request with same name and same token reclaims seat
        state, p1_reconnected, is_new2 = add_player(state, name="Marco", token=p1["token"])
        self.assertFalse(is_new2)
        self.assertEqual(p1_reconnected["id"], p1["id"])
        self.assertEqual(p1_reconnected["name"], "Marco")

        # Session or host reconnecting without token in lobby reclaims seat without cloning "Marco 2"
        state, p1_host_reclaim, is_new3 = add_player(state, name="Marco", is_admin=True)
        self.assertFalse(is_new3)
        self.assertEqual(p1_host_reclaim["id"], p1["id"])
        self.assertEqual(p1_host_reclaim["name"], "Marco")


class TestPromptEngineAndFrames(TestCase):
    def test_semantic_frames_completeness(self):
        self.assertGreaterEqual(len(ALL_FRAMES), 6)
        for key, frame in ALL_FRAMES.items():
            self.assertTrue(len(frame.subjects) >= 4)
            self.assertTrue(len(frame.actions) >= 3)
            self.assertTrue(len(frame.targets) >= 4)
            self.assertTrue(len(frame.limiters) >= 3)

    def test_combinatorial_synthesis(self):
        for key, frame in ALL_FRAMES.items():
            synth = synthesize_prompt_from_frame(frame)
            self.assertTrue(bool(synth["text"]))
            self.assertTrue(synth["is_synthetic"])
            self.assertIn(synth["pack"], ALL_FRAMES)
            self.assertIn("pt", synth["translations"])
            self.assertIn("es", synth["translations"])

    def test_gold_prompt_deck_and_answer_cleaner(self):
        deck = get_curated_deck("mix")
        self.assertGreaterEqual(len(deck), 15)
        for p in deck:
            self.assertTrue(bool(p["text"]))
            self.assertGreaterEqual(len(p["sample_answers"]), 4)

        # Normalization and article stripping
        self.assertEqual(clean_answer_key("France"), "france")
        self.assertEqual(clean_answer_key("The France"), "france")
        self.assertEqual(clean_answer_key("  O Brasil  "), "brasil")
        self.assertEqual(clean_answer_key("A França"), "franca")
        self.assertEqual(clean_answer_key("El Salvador"), "salvador")

    def test_validate_player_answer_known_matches(self):
        prompt = "European country that borders at least 3 other countries"
        samples = ["France", "Germany", "Austria", "Switzerland", "Poland"]
        obscure = ["Liechtenstein", "Luxembourg"]

        # Sample match
        res_fr = validate_player_answer(prompt, "The France", samples, obscure, use_ai=False)
        self.assertTrue(res_fr["valid"])
        self.assertEqual(res_fr["source"], "curated_match")
        self.assertFalse(res_fr["is_obscure"])

        # Obscurity bonus match
        res_li = validate_player_answer(prompt, "liechtenstein", samples + obscure, obscure, use_ai=False)
        self.assertTrue(res_li["valid"])
        self.assertTrue(res_li["is_obscure"])

        # Empty answer
        res_empty = validate_player_answer(prompt, "   ", samples, obscure, use_ai=False)
        self.assertFalse(res_empty["valid"])


class TestDontSayGameFlowAndScoring(TestCase):
    def setUp(self):
        self.code = "DSFLOW01"
        self.state = create_game(self.code, title="Flow Match")
        self.state, self.alice, _ = add_player(self.state, name="Alice", is_admin=True)
        self.state, self.bob, _ = add_player(self.state, name="Bob")
        self.state, self.charlie, _ = add_player(self.state, name="Charlie")

    def test_full_round_collision_and_zero_spoiler_view(self):
        # 1. Start game
        start_game(self.state)
        self.assertEqual(self.state["phase"], "answering")
        self.assertEqual(self.state["round_num"], 1)
        self.assertIsNotNone(self.state["current_prompt"])

        # Override prompt for deterministic testing
        self.state["current_prompt"] = {
            "id": "test_p1",
            "text": "European country that borders at least 3 other countries",
            "sample_answers": ["France", "Germany", "Austria", "Switzerland", "Liechtenstein"],
            "obscurity_examples": ["Liechtenstein"],
        }
        save_game(self.code, self.state)

        # 2. Secret Submissions
        submit_answer(self.state, self.alice["id"], "France")
        submit_answer(self.state, self.bob["id"], "The France")  # Intentionally collides with Alice!

        # Zero-spoiler check for Charlie who hasn't submitted yet
        view_charlie = get_sanitized_player_view(self.state, self.charlie["token"])
        self.assertEqual(view_charlie["phase"], "answering")
        # Charlie must NOT see Alice or Bob's answers!
        self.assertNotIn("round_answers", view_charlie)
        for p in view_charlie["players"]:
            if p["id"] in (self.alice["id"], self.bob["id"]):
                self.assertTrue(p["has_submitted"])
                self.assertNotIn("my_answer", p)
                self.assertNotIn("revealed_answer", p)

        # Charlie submits unique obscure answer
        submit_answer(self.state, self.charlie["id"], "Liechtenstein")

        # Since all active players submitted, game should automatically evaluate and reveal
        self.assertEqual(self.state["phase"], "reveal")
        rr = self.state["round_results"]
        self.assertIsNotNone(rr)
        self.assertEqual(rr["total_clashes"], 1)

        # Alice and Bob clashed -> 0 pts
        alice_res = rr["player_results"][self.alice["id"]]
        bob_res = rr["player_results"][self.bob["id"]]
        charlie_res = rr["player_results"][self.charlie["id"]]

        self.assertEqual(alice_res["status"], "clash")
        self.assertEqual(alice_res["points_awarded"], 0)
        self.assertEqual(self.state["players"][self.alice["id"]]["score"], 0)

        self.assertEqual(bob_res["status"], "clash")
        self.assertEqual(bob_res["points_awarded"], 0)
        self.assertEqual(self.state["players"][self.bob["id"]]["score"], 0)

        # Charlie was unique + obscure bonus -> 150 pts
        self.assertEqual(charlie_res["status"], "unique")
        self.assertEqual(charlie_res["points_awarded"], 150)
        self.assertEqual(self.state["players"][self.charlie["id"]]["score"], 150)

        # In reveal view, answers ARE visible
        view_reveal = get_sanitized_player_view(self.state, self.alice["token"])
        self.assertEqual(view_reveal["phase"], "reveal")
        p_charlie = next(p for p in view_reveal["players"] if p["id"] == self.charlie["id"])
        self.assertEqual(p_charlie["revealed_answer"], "Liechtenstein")

    def test_host_arbitration_toggle_validity(self):
        start_game(self.state)
        self.state["current_prompt"] = {
            "id": "test_p2",
            "text": "European country that borders at least 3 other countries",
            "sample_answers": ["France", "Germany"],
        }
        submit_answer(self.state, self.alice["id"], "Atlantis")  # Invalid fantasy answer
        submit_answer(self.state, self.bob["id"], "Germany")
        submit_answer(self.state, self.charlie["id"], "France")

        evaluate_and_reveal_round(self.state)

        # Mark Alice as Invalid
        toggle_answer_validity(self.state, self.alice["id"], False)
        self.assertEqual(self.state["players"][self.alice["id"]]["score"], 0)
        self.assertEqual(self.state["round_results"]["player_results"][self.alice["id"]]["status"], "invalid")

        # Now Host changes mind and marks Alice as Valid
        toggle_answer_validity(self.state, self.alice["id"], True)
        self.assertEqual(self.state["players"][self.alice["id"]]["score"], 100)
        self.assertEqual(self.state["round_results"]["player_results"][self.alice["id"]]["status"], "unique")

    def test_match_advancement_and_game_over(self):
        update_settings(self.state, {"max_rounds": 2})
        start_game(self.state)
        self.assertEqual(self.state["round_num"], 1)

        # Round 1
        submit_answer(self.state, self.alice["id"], "A")
        submit_answer(self.state, self.bob["id"], "B")
        submit_answer(self.state, self.charlie["id"], "C")
        self.assertEqual(self.state["phase"], "reveal")

        # Advance to round 2
        advance_next_round(self.state)
        self.assertEqual(self.state["round_num"], 2)
        self.assertEqual(self.state["phase"], "answering")

        # Round 2
        submit_answer(self.state, self.alice["id"], "X")
        submit_answer(self.state, self.bob["id"], "Y")
        submit_answer(self.state, self.charlie["id"], "Z")
        self.assertEqual(self.state["phase"], "reveal")

        # Advance reaches game over
        advance_next_round(self.state)
        self.assertEqual(self.state["phase"], "gameover")

        # Reset game brings back to lobby
        reset_game(self.state)
        self.assertEqual(self.state["phase"], "lobby")
        self.assertEqual(self.state["round_num"], 0)
        self.assertEqual(self.state["players"][self.alice["id"]]["score"], 0)


def test_websocket_dontsay_round(db):
    code = "WSCONNT1"
    create_game(code, title="WS Match")

    async def _run():
        communicator_host = WebsocketCommunicator(application, f"/ws/dontsay/{code}/")
        connected_h, _ = await communicator_host.connect()
        assert connected_h

        communicator_guest = WebsocketCommunicator(application, f"/ws/dontsay/{code}/")
        connected_g, _ = await communicator_guest.connect()
        assert connected_g

        async def _recv_until(comm, predicate):
            for _ in range(20):
                msg = await comm.receive_json_from(timeout=2)
                if predicate(msg):
                    return msg
            raise AssertionError("Timed out waiting for expected WebSocket state")

        # Host joins
        await communicator_host.send_json_to({"action": "join", "name": "HostUser"})
        msg_h = await _recv_until(communicator_host, lambda m: m.get("viewer", {}).get("name") == "HostUser")
        assert msg_h["phase"] == "lobby"
        assert msg_h["viewer"]["is_admin"]

        # Guest joins
        await communicator_guest.send_json_to({"action": "join", "name": "GuestUser"})
        msg_g = await _recv_until(communicator_guest, lambda m: m.get("viewer", {}).get("name") == "GuestUser")
        assert msg_g["phase"] == "lobby"
        assert not msg_g["viewer"]["is_admin"]

        # Host starts game
        await communicator_host.send_json_to({"action": "start_game"})
        msg_started = await _recv_until(communicator_host, lambda m: m.get("phase") == "answering")
        assert msg_started["phase"] == "answering"

        # Both submit answers
        await communicator_host.send_json_to({"action": "submit_answer", "answer": "Paris"})
        await communicator_guest.send_json_to({"action": "submit_answer", "answer": "Paris"})

        # Since all active connected players submitted, game should reveal
        msg_rev = await _recv_until(communicator_host, lambda m: m.get("phase") == "reveal")
        assert msg_rev["phase"] == "reveal"
        assert msg_rev["round_results"]["total_clashes"] == 1

        await communicator_host.disconnect()
        await communicator_guest.disconnect()

    async_to_sync(_run)()

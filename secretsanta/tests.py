"""Comprehensive unit and integration tests for Secret Santa & Target Matcher."""

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import Client
from django.urls import reverse

from gamerooms.language_support import get_game_language_support
from gamerooms.models import Room
from secretsanta.game_state import (
    add_offline_player,
    add_player,
    change_player_color,
    create_game,
    delete_game,
    generate_matches,
    get_game,
    get_sanitized_player_view,
    reset_to_lobby,
    reveal_all_admin,
    solve_matching,
    update_settings,
    update_wishlist,
)
from website.asgi import application


class TestMatchingAlgorithm:
    """Test the derangement / Hamiltonian cycle matching engine."""

    def test_insufficient_players(self):
        ok, msg = solve_matching([], {})
        assert ok is False
        assert "At least 2" in msg

        ok, msg = solve_matching(["alice"], {})
        assert ok is False
        assert "At least 2" in msg

    def test_two_players_reciprocal(self):
        pids = ["p1", "p2"]
        ok, matches = solve_matching(pids, {})
        assert ok is True
        assert matches["p1"] == "p2"
        assert matches["p2"] == "p1"
        assert matches["p1"] != "p1"
        assert matches["p2"] != "p2"

    def test_three_players_cycle(self):
        pids = ["p1", "p2", "p3"]
        ok, matches = solve_matching(pids, {})
        assert ok is True
        assert len(matches) == 3
        # Everyone gives and receives exactly once
        assert set(matches.keys()) == set(pids)
        assert set(matches.values()) == set(pids)
        # No self matches
        for p in pids:
            assert matches[p] != p

    def test_larger_group_derangement(self):
        pids = [f"player_{i}" for i in range(12)]
        for _ in range(10):  # Run several times to test randomness
            ok, matches = solve_matching(pids, {})
            assert ok is True
            assert set(matches.keys()) == set(pids)
            assert set(matches.values()) == set(pids)
            for p in pids:
                assert matches[p] != p

    def test_exclusions_respected(self):
        pids = ["alice", "bob", "charlie", "david"]
        # Alice cannot give to Bob; Charlie cannot give to David
        exclusions = {
            "alice": ["bob"],
            "charlie": ["david"],
        }
        for _ in range(10):
            ok, matches = solve_matching(pids, exclusions)
            assert ok is True
            assert matches["alice"] != "bob"
            assert matches["charlie"] != "david"
            for p in pids:
                assert matches[p] != p

    def test_couples_cross_exclusions(self):
        # Two couples: {A, B} and {C, D}. Spouses cannot give to each other.
        pids = ["a", "b", "c", "d"]
        exclusions = {
            "a": ["b"],
            "b": ["a"],
            "c": ["d"],
            "d": ["c"],
        }
        ok, matches = solve_matching(pids, exclusions)
        assert ok is True
        assert matches["a"] in ("c", "d")
        assert matches["b"] in ("c", "d")
        assert matches["c"] in ("a", "b")
        assert matches["d"] in ("a", "b")
        for p in pids:
            assert matches[p] != p

    def test_impossible_exclusions(self):
        pids = ["alice", "bob", "charlie"]
        # Alice excludes all other players
        exclusions = {
            "alice": ["bob", "charlie"],
        }
        ok, msg = solve_matching(pids, exclusions)
        assert ok is False
        assert "excluded all available targets" in msg or "relax" in msg.lower()


class TestGameState:
    """Test game state transitions, player management, and settings."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        self.code = "SANTA1"
        delete_game(self.code)
        yield
        delete_game(self.code)

    def test_create_and_add_players(self):
        state = create_game(self.code, title="Holiday Gift Swap")
        assert state["code"] == self.code
        assert state["phase"] == "lobby"

        # Add admin
        state, p1, is_new1 = add_player(state, name="Alice", is_admin=True)
        assert is_new1 is True
        assert p1["name"] == "Alice"
        assert p1["is_admin"] is True

        # Add second player
        state, p2, is_new2 = add_player(state, name="Bob")
        assert is_new2 is True
        assert p2["name"] == "Bob"
        assert p2["is_admin"] is False

        # Add couch/offline player
        p3 = add_offline_player(state, name="Grandma", added_by_name="Alice")
        assert p3["name"] == "Grandma"
        assert p3["is_offline"] is True

        # Check total players
        reloaded = get_game(self.code)
        assert len(reloaded["players"]) == 3

    def test_wishlist_and_color_updates(self):
        state = create_game(self.code)
        state, p1, _ = add_player(state, name="Alice")

        # Update wishlist
        ok = update_wishlist(state, p1["id"], "Books, chocolate, warm socks")
        assert ok is True
        assert state["players"][p1["id"]]["wishlist"] == "Books, chocolate, warm socks"

        # Change color
        ok = change_player_color(state, p1["id"], "#ef4444")
        assert ok is True
        assert state["players"][p1["id"]]["color"] == "#ef4444"

    def test_theme_and_settings_update(self):
        state = create_game(self.code)
        update_settings(
            state,
            {
                "theme": "assassin",
                "budget": "No budget",
                "event_date": "Next Friday",
            },
        )
        assert state["settings"]["theme"] == "assassin"
        assert state["settings"]["custom_title"] == "Secret Assassin"
        assert state["settings"]["budget"] == "No budget"
        assert state["settings"]["event_date"] == "Next Friday"

    def test_matching_lifecycle(self):
        state = create_game(self.code)
        state, p1, _ = add_player(state, name="Alice", is_admin=True)
        state, p2, _ = add_player(state, name="Bob")
        state, p3, _ = add_player(state, name="Charlie")

        # Generate matches
        ok, msg = generate_matches(state)
        assert ok is True
        assert state["phase"] == "matched"
        assert len(state["matches"]) == 3

        # Verify each player has target_id assigned
        for pid in (p1["id"], p2["id"], p3["id"]):
            target_id = state["players"][pid]["target_id"]
            assert target_id is not None
            assert target_id != pid
            assert target_id in state["players"]

        # Reset to lobby
        reset_to_lobby(state)
        assert state["phase"] == "lobby"
        assert len(state["matches"]) == 0
        for pid in (p1["id"], p2["id"], p3["id"]):
            assert state["players"][pid]["target_id"] is None

    def test_master_reveal_permissions(self):
        state = create_game(self.code)
        state, p1, _ = add_player(state, name="Alice", is_admin=True)
        state, p2, _ = add_player(state, name="Bob", is_admin=False)
        generate_matches(state)

        # Non-admin cannot master reveal
        ok, res = reveal_all_admin(state, p2["id"])
        assert ok is False

        # Admin can master reveal
        ok, table = reveal_all_admin(state, p1["id"])
        assert ok is True
        assert len(table) == 2


class TestZeroSpoilerProjection:
    """Verify that client state projections NEVER leak matches or other players' targets."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        self.code = "SPOIL1"
        delete_game(self.code)
        yield
        delete_game(self.code)

    def test_zero_spoiler_guarantee(self):
        state = create_game(self.code)
        state, p1, _ = add_player(state, name="Alice", is_admin=True)
        state, p2, _ = add_player(state, name="Bob")
        state, p3, _ = add_player(state, name="Charlie")
        update_wishlist(state, p2["id"], "Bob's favorite comic books")

        generate_matches(state)

        # Get Alice's view
        alice_view = get_sanitized_player_view(state, viewer_id=p1["id"])

        # 1. matches dictionary MUST NOT exist in view
        assert "matches" not in alice_view

        # 2. Other players in the players list MUST NOT contain target_id
        for pub_player in alice_view["players"]:
            assert "target_id" not in pub_player
            assert "matches" not in pub_player

        # 3. Alice can see her own target
        assert alice_view["my_target"] is not None
        assert alice_view["my_target"]["id"] != p1["id"]
        assert alice_view["my_target"]["name"] in ("Bob", "Charlie")

        # 4. If Alice's target is Bob, she sees Bob's wishlist, but NOT Charlie's
        if alice_view["my_target"]["id"] == p2["id"]:
            assert alice_view["my_target"]["wishlist"] == "Bob's favorite comic books"

        # 5. Get unauthenticated/anonymous view
        anon_view = get_sanitized_player_view(state, viewer_id=None)
        assert anon_view["me"] is None
        assert anon_view["my_target"] is None
        assert "matches" not in anon_view


@pytest.mark.django_db
class TestSecretSantaViews:
    """Test HTTP endpoints for room listing, creation, and joining."""

    def test_language_support_registry(self):
        support = get_game_language_support("secretsanta", "en")
        assert support["content_supported"] is True
        assert support["mode"] == "full_content"

        support_pt = get_game_language_support("secretsanta", "pt")
        assert support_pt["content_supported"] is True

    def test_room_create_and_join(self, client: Client):
        # Create room via POST
        res = client.post(
            reverse("gamerooms:room-create"),
            {
                "title": "Family Gift Exchange",
                "game_type": "secretsanta",
                "language": "en",
                "captcha_answer": "4",
                "captcha_expected": "4",
            },
        )
        assert res.status_code == 302
        room = Room.objects.filter(game_type="secretsanta").first()
        assert room is not None
        assert room.title == "Family Gift Exchange"

        # Join room as Marco
        join_res = client.post(
            reverse("gamerooms:room-join", kwargs={"code": room.code}),
            {"name": "Marco"},
            follow=False,
        )
        assert join_res.status_code == 302
        assert f"/games/secretsanta/{room.code}/Marco/" in join_res["Location"]

        # Access game view
        game_res = client.get(join_res["Location"])
        assert game_res.status_code == 200
        assert b"Secret Santa" in game_res.content
        assert b"Family Gift Exchange" in game_res.content

        # Room listing displays Secret Santa room
        list_res = client.get(reverse("gamerooms:room-list"))
        assert list_res.status_code == 200
        assert b"Secret Santa" in list_res.content
        assert room.code.encode() in list_res.content

    def test_player_qr_and_reconnect(self, client: Client):
        room = Room.objects.create(title="QR Room", game_type="secretsanta", language="en")
        state = create_game(room.code)
        state, player, _ = add_player(state, name="David")

        # QR endpoint returns JSON with QR data
        qr_url = reverse("gamerooms:secretsanta:player-qr", kwargs={"code": room.code, "token": player["token"]})
        res = client.get(qr_url)
        assert res.status_code == 200
        data = res.json()
        assert "qr" in data
        assert data["player_name"] == "David"

        # Reconnect redirects to game view
        rec_url = reverse("gamerooms:secretsanta:reconnect", kwargs={"code": room.code, "token": player["token"]})
        rec_res = client.get(rec_url)
        assert rec_res.status_code == 302
        assert f"/games/secretsanta/{room.code}/David/" in rec_res["Location"]


@pytest.mark.django_db
def test_websocket_join_draw_and_zero_spoiler(db):
    """End-to-end WebSocket integration test for Secret Santa."""
    room = Room.objects.create(title="Holiday Secret Santa", game_type="secretsanta", language="en")
    code = room.code

    async def _run():
        # Host communicator
        host_comm = WebsocketCommunicator(application, f"/ws/secretsanta/{code}/")
        connected, _ = await host_comm.connect()
        assert connected is True

        # Host joins
        await host_comm.send_json_to(
            {
                "action": "join",
                "name": "Host Alice",
                "is_admin": True,
            }
        )
        resp = await host_comm.receive_json_from()
        assert resp["type"] == "state"
        assert resp["state"]["phase"] == "lobby"
        assert len(resp["state"]["players"]) == 1

        # Guest communicator
        guest_comm = WebsocketCommunicator(application, f"/ws/secretsanta/{code}/")
        g_connected, _ = await guest_comm.connect()
        assert g_connected is True

        # Guest joins
        await guest_comm.send_json_to(
            {
                "action": "join",
                "name": "Guest Bob",
                "is_admin": False,
            }
        )

        # Both receive updated state
        h_resp = await host_comm.receive_json_from()
        g_resp = await guest_comm.receive_json_from()
        assert len(h_resp["state"]["players"]) == 2
        assert len(g_resp["state"]["players"]) == 2

        # Host adds offline player "Grandma"
        await host_comm.send_json_to(
            {
                "action": "add_offline_player",
                "name": "Grandma",
            }
        )
        h_resp = await host_comm.receive_json_from()
        g_resp = await guest_comm.receive_json_from()
        assert len(h_resp["state"]["players"]) == 3
        assert len(g_resp["state"]["players"]) == 3

        # Guest updates wishlist
        await guest_comm.send_json_to(
            {
                "action": "update_wishlist",
                "wishlist": "Art supplies and peppermint tea",
            }
        )
        h_resp = await host_comm.receive_json_from()
        g_resp = await guest_comm.receive_json_from()

        # Host triggers secret match draw
        await host_comm.send_json_to({"action": "generate_matches"})
        h_matched = await host_comm.receive_json_from()
        g_matched = await guest_comm.receive_json_from()

        assert h_matched["state"]["phase"] == "matched"
        assert g_matched["state"]["phase"] == "matched"

        # Verify Zero-Spoiler Guarantee:
        # 1. "matches" dictionary is absent
        assert "matches" not in h_matched["state"]
        assert "matches" not in g_matched["state"]

        # 2. Guest Bob only sees his own target, not Alice's target
        assert g_matched["state"]["my_target"] is not None
        assert g_matched["state"]["my_target"]["name"] in ("Host Alice", "Grandma")

        # 3. Host Alice sees her own target
        assert h_matched["state"]["my_target"] is not None
        assert h_matched["state"]["my_target"]["name"] in ("Guest Bob", "Grandma")

        await host_comm.disconnect()
        await guest_comm.disconnect()
        delete_game(code)

    async_to_sync(_run)()

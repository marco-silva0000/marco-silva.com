"""Comprehensive tests for 'Rank It!' (ito cooperative party game).

Verifies game state lifecycle, distinct player color assignment, secret card drafting,
zero-spoiler view sanitization, ascending order validation, clash handling, lives subtraction,
and end-to-end WebSocket communication.
"""

import time

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator

from gamerooms.models import Room
from gamerooms.player_colors import PLAYER_PALETTE, get_player_initials
from rankit.game_state import (
    add_player,
    change_player_color,
    create_game,
    get_game,
    get_sanitized_player_view,
    play_again,
    play_card,
    set_card_clue,
    start_level,
    update_settings,
)
from website.asgi import application


@pytest.fixture(autouse=True)
def clean_redis_fallback():
    from rankit import game_state

    game_state._fallback_store.clear()
    yield
    game_state._fallback_store.clear()


def test_initials_extraction():
    assert get_player_initials("Marco Silva") == "MS"
    assert get_player_initials("Alice") == "A"
    assert get_player_initials("Bob John Dylan") == "BD"
    assert get_player_initials("p1") == "P"
    assert get_player_initials("") == "?"
    assert get_player_initials(None) == "?"


def test_create_and_get_game():
    state = create_game("TEST1", title="Rank It Room", language="en")
    assert state["code"] == "TEST1"
    assert state["phase"] == "lobby"
    assert state["level"] == 1
    assert state["lives"] == 3
    assert state["highest_played_number"] == 0
    assert len(state["players"]) == 0

    fetched = get_game("TEST1")
    assert fetched["title"] == "Rank It Room"


def test_distinct_color_assignment_and_admin_status():
    state = create_game("TEST2")
    state, p1, is_new1 = add_player(state, "Alice")
    assert is_new1 is True
    assert p1["is_admin"] is True  # First player becomes host
    assert p1["initials"] == "A"
    assert p1["color"] == PLAYER_PALETTE[0]["hex"]

    state, p2, is_new2 = add_player(state, "Bob")
    assert is_new2 is True
    assert p2["is_admin"] is False
    assert p2["initials"] == "B"
    assert p2["color"] == PLAYER_PALETTE[1]["hex"]
    assert p1["color"] != p2["color"]


def test_change_player_color_permissions():
    state = create_game("TEST3")
    state, p1, _ = add_player(state, "Host", is_admin=True)
    state, p2, _ = add_player(state, "Player2", is_admin=False)

    new_color = PLAYER_PALETTE[4]["hex"]

    # Player can change own color
    ok = change_player_color(
        state,
        target_player_id=p2["id"],
        new_color=new_color,
        requested_by_admin=False,
        requester_player_id=p2["id"],
    )
    assert ok is True
    assert state["players"][p2["id"]]["color"] == new_color

    # Non-admin cannot change another player's color
    denied = change_player_color(
        state,
        target_player_id=p1["id"],
        new_color="#ffffff",
        requested_by_admin=False,
        requester_player_id=p2["id"],
    )
    assert denied is False

    # Host/admin CAN change another player's color
    admin_ok = change_player_color(
        state,
        target_player_id=p2["id"],
        new_color=PLAYER_PALETTE[8]["hex"],
        requested_by_admin=True,
        requester_player_id=p1["id"],
    )
    assert admin_ok is True
    assert state["players"][p2["id"]]["color"] == PLAYER_PALETTE[8]["hex"]


def test_update_settings():
    state = create_game("TEST4")
    update_settings(
        state,
        {
            "cards_per_player": "2",
            "starting_lives": 4,
            "target_levels": 5,
            "pack": "superpowers",
            "allow_nsfw": True,
        },
    )
    s = state["settings"]
    assert s["cards_per_player"] == "2"
    assert s["starting_lives"] == 4
    assert s["target_levels"] == 5
    assert s["pack"] == "superpowers"
    assert s["allow_nsfw"] is True
    assert state["lives"] == 4


def test_start_level_card_drafting_and_no_duplicates():
    state = create_game("TEST5")
    state, p1, _ = add_player(state, "Alice", is_admin=True)
    state, p2, _ = add_player(state, "Bob", is_admin=False)
    state, p3, _ = add_player(state, "Charlie", is_admin=False)

    # Set 2 cards each
    update_settings(state, {"cards_per_player": "2"})

    ok = start_level(state, from_level=1)
    assert ok is True
    assert state["phase"] == "playing"
    assert state["current_prompt"] is not None
    assert state["round_countdown_until"] is not None
    assert state["round_countdown_until"] > time.time()

    all_drafted = []
    for pid, p in state["players"].items():
        assert len(p["hand"]) == 2
        for card in p["hand"]:
            assert 1 <= card["number"] <= 100
            assert card["played"] is False
            all_drafted.append(card["number"])

    # Strictly no duplicate cards among players
    assert len(all_drafted) == 6
    assert len(set(all_drafted)) == 6


def test_start_level_idempotency_and_debounce():
    state = create_game("TEST6")
    state, p1, _ = add_player(state, "Alice", is_admin=True)

    ok1 = start_level(state, from_level=1)
    assert ok1 is True

    # Immediate second click for the same level within 2.0s should be dropped (debounced)
    ok2 = start_level(state, from_level=1)
    assert ok2 is False

    # Stale request from previous level should be dropped
    ok3 = start_level(state, from_level=0)
    assert ok3 is False


def test_set_card_clue():
    state = create_game("TEST7")
    state, p1, _ = add_player(state, "Alice", is_admin=True)
    start_level(state, from_level=1)

    card_id = p1["hand"][0]["card_id"]
    ok = set_card_clue(state, p1["id"], card_id, "A sleepy kitten")
    assert ok is True
    assert p1["hand"][0]["clue"] == "A sleepy kitten"


def test_zero_spoiler_sanitized_player_view():
    state = create_game("TEST8")
    state, p1, _ = add_player(state, "Alice", is_admin=True)
    state, p2, _ = add_player(state, "Bob", is_admin=False)
    start_level(state, from_level=1)

    p1_card_num = p1["hand"][0]["number"]
    p2_card_num = p2["hand"][0]["number"]

    # View as Alice (p1)
    view_p1 = get_sanitized_player_view(state, viewer_id=p1["id"])
    assert view_p1["viewer"]["id"] == p1["id"]

    alice_view_p1 = [p for p in view_p1["players"] if p["id"] == p1["id"]][0]
    alice_view_p2 = [p for p in view_p1["players"] if p["id"] == p2["id"]][0]

    # Alice can see her own secret number
    assert alice_view_p1["hand"][0]["number"] == p1_card_num

    # Alice CANNOT see Bob's secret number! Zero spoiler guarantee!
    assert alice_view_p2["hand"][0]["number"] is None

    # Bob can see his own secret number
    view_p2 = get_sanitized_player_view(state, viewer_id=p2["id"])
    bob_view_p2 = [p for p in view_p2["players"] if p["id"] == p2["id"]][0]
    assert bob_view_p2["hand"][0]["number"] == p2_card_num


def test_play_card_ascending_order_and_level_success():
    state = create_game("TEST9")
    state, p1, _ = add_player(state, "Alice", is_admin=True)
    state, p2, _ = add_player(state, "Bob", is_admin=False)

    update_settings(state, {"cards_per_player": "1", "target_levels": 3})
    start_level(state, from_level=1)

    # Manually configure hands for deterministic test
    p1["hand"][0]["number"] = 25
    p2["hand"][0]["number"] = 75

    # 1. Alice plays 25 (valid ascending)
    ok1, msg1 = play_card(state, p1["id"], p1["hand"][0]["card_id"])
    assert ok1 is True
    assert state["highest_played_number"] == 25
    assert state["lives"] == 3
    assert len(state["timeline"]) == 1
    assert state["timeline"][0]["is_clash"] is False
    assert state["phase"] == "playing"

    # 2. Bob plays 75 (valid ascending: 75 > 25)
    ok2, msg2 = play_card(state, p2["id"], p2["hand"][0]["card_id"])
    assert ok2 is True
    assert state["highest_played_number"] == 75
    assert state["lives"] == 3
    assert len(state["timeline"]) == 2
    assert state["timeline"][1]["is_clash"] is False

    # All cards played! Should transition to level_success
    assert state["phase"] == "level_success"
    assert state["level"] == 2
    assert len(state["level_history"]) == 1


def test_play_card_clash_and_game_over():
    state = create_game("TEST10")
    state, p1, _ = add_player(state, "Alice", is_admin=True)
    state, p2, _ = add_player(state, "Bob", is_admin=False)

    update_settings(state, {"cards_per_player": "1", "starting_lives": 1})
    start_level(state, from_level=1)

    p1["hand"][0]["number"] = 80
    p2["hand"][0]["number"] = 30

    # 1. Alice plays 80
    play_card(state, p1["id"], p1["hand"][0]["card_id"])
    assert state["highest_played_number"] == 80
    assert state["lives"] == 1

    # 2. Bob plays 30 (30 < 80 => CLASH!)
    ok, msg = play_card(state, p2["id"], p2["hand"][0]["card_id"])
    assert ok is True
    assert state["timeline"][-1]["is_clash"] is True
    assert state["lives"] == 0
    assert state["phase"] == "gameover"

    # Reset
    play_again(state)
    assert state["phase"] == "lobby"
    assert state["level"] == 1
    assert state["lives"] == 1


def test_websocket_rankit_end_to_end(db):
    room = Room.objects.create(code="WSIT01", title="WebSocket Ito Test", game_type="rankit")

    async def _run():
        communicator = WebsocketCommunicator(
            application,
            f"/ws/rankit/{room.code}/",
        )
        connected, _ = await communicator.connect()
        assert connected

        # 1. Join room as host
        await communicator.send_json_to(
            {
                "action": "join",
                "name": "HostPlayer",
                "is_admin": True,
            }
        )
        res1 = await communicator.receive_json_from(timeout=3)
        assert res1["type"] == "state"
        assert res1["state"]["code"] == "WSIT01"
        assert len(res1["state"]["players"]) == 1
        p1 = res1["state"]["players"][0]
        assert p1["name"] == "HostPlayer"
        assert p1["is_admin"] is True
        assert p1["color"] == PLAYER_PALETTE[0]["hex"]

        # 2. Change color
        new_color = PLAYER_PALETTE[3]["hex"]
        await communicator.send_json_to(
            {
                "action": "change_color",
                "player_id": p1["id"],
                "color": new_color,
            }
        )
        res2 = await communicator.receive_json_from(timeout=3)
        assert res2["state"]["players"][0]["color"] == new_color

        # 3. Chat
        await communicator.send_json_to(
            {
                "action": "chat",
                "msg": "Hello team, let's rank!",
            }
        )
        res3 = await communicator.receive_json_from(timeout=3)
        assert any("Hello team" in e["text"] for e in res3["state"]["activity_log"])

        # 4. Suggest prompt
        await communicator.send_json_to(
            {
                "action": "suggest_prompt",
                "text": "Best Superheroes by Muscle",
                "low_desc": "Ant-Man without suit",
                "high_desc": "Incredible Hulk with cosmic rage",
                "pack": "superpowers",
            }
        )
        res4 = await communicator.receive_json_from(timeout=3)
        assert res4["type"] == "prompt_suggestion_ack"
        assert res4["success"] is True

        # 5. Start level 1
        await communicator.send_json_to(
            {
                "action": "start_level",
                "from_level": 1,
            }
        )
        res5 = await communicator.receive_json_from(timeout=3)
        assert res5["state"]["phase"] == "playing"
        assert res5["state"]["round_countdown_until"] is not None
        assert len(res5["state"]["viewer"]["hand"]) >= 1

        await communicator.disconnect()

    async_to_sync(_run)()

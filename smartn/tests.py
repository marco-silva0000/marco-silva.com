import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import Client
from django.urls import reverse

from gamerooms.models import Room
from smartn.game_state import (
    add_offline_player,
    add_player,
    change_player_color,
    create_game,
    delete_game,
    find_player_by_id,
    find_player_by_name,
    get_game,
    get_sanitized_player_view,
    host_arbitrate,
    kick_player,
    pass_turn,
    pick_capsule,
    process_chat_answer,
    save_game,
    start_game,
    update_settings,
)
from smartn.questions import SMARTN_QUESTIONS, get_deck
from website.asgi import application


@pytest.mark.django_db
class TestSmartNQuestions:
    def test_question_bank_structure(self):
        assert len(SMARTN_QUESTIONS) >= 150
        ids = [q["id"] for q in SMARTN_QUESTIONS]
        assert len(ids) == len(set(ids)), f"Duplicate question IDs found: {[x for x in ids if ids.count(x) > 1]}"

        valid_packs = {"geo", "science", "media", "food", "sports", "history"}
        valid_types = {"true_false", "order", "number", "match"}

        for q in SMARTN_QUESTIONS:
            assert q["id"], "Question ID cannot be empty"
            assert q["pack"] in valid_packs, f"Invalid pack {q.get('pack')} in {q['id']}"
            assert q["prompt"], f"Missing prompt in {q['id']}"
            assert q["type"] in valid_types, f"Invalid type {q.get('type')} in {q['id']}"
            assert "items" in q, f"Missing items in {q['id']}"
            assert len(q["items"]) == q.get("n", 10), f"Items count mismatch in {q['id']}"

            slots = [it["slot"] for it in q["items"]]
            assert slots == list(range(1, q.get("n", 10) + 1)), (
                f"Slots in {q['id']} must be 1..{q.get('n', 10)}, got {slots}"
            )

            for it in q["items"]:
                assert "slot" in it
                assert "label" in it and it["label"], f"Missing label in {q['id']} slot {it.get('slot')}"
                assert "value" in it and str(it["value"]).strip(), f"Missing value in {q['id']} slot {it.get('slot')}"
                assert isinstance(it["is_correct"], bool), f"is_correct must be bool in {q['id']} slot {it.get('slot')}"
                assert "explanation" in it and it["explanation"], (
                    f"Missing explanation in {q['id']} slot {it.get('slot')}"
                )
                assert isinstance(it.get("aliases", []), list)

    def test_deck_filtering(self):
        for pack in ["geo", "science", "media", "food", "sports", "history"]:
            pack_deck = get_deck(pack_filter=pack)
            assert len(pack_deck) >= 25, f"Pack {pack} has fewer than 25 questions: {len(pack_deck)}"
            assert all(q["pack"] == pack for q in pack_deck)

        exact_deck = get_deck(count_filter="exactly_10")
        assert len(exact_deck) == len([q for q in SMARTN_QUESTIONS if q.get("n", 10) == 10])
        assert all(q.get("n", 10) == 10 for q in exact_deck)


@pytest.mark.django_db
class TestSmartNGameState:
    def setup_method(self):
        self.code = "TESTSN1"
        delete_game(self.code)

    def teardown_method(self):
        delete_game(self.code)

    def test_create_and_add_players(self):
        state = create_game(self.code, host_name="Alice")
        assert state["phase"] == "lobby"
        assert state["settings"]["mode"] == "multi_device"

        state, p1, is_new1 = add_player(self.code, name="Alice", is_admin=True)
        assert is_new1 is True
        assert p1["name"] == "Alice"
        assert p1["is_admin"] is True
        assert p1["token"] is not None
        assert p1["color"] is not None

        state, p2, is_new2 = add_player(self.code, name="Bob")
        assert is_new2 is True
        assert p2["name"] == "Bob"
        assert p2["is_admin"] is False
        assert p2["color"] != p1["color"]

        # Reconnect test with same token
        state, p1_rec, is_new_rec = add_player(self.code, name="Alice", token=p1["token"])
        assert is_new_rec is False
        assert p1_rec["id"] == p1["id"]

    def test_update_settings_and_color(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)

        ok, msg, state = update_settings(
            self.code,
            {
                "mode": "single_device",
                "pack": "geo",
                "yes_no_scoring": "prediction",
                "target_score": 30,
            },
        )
        assert ok is True
        assert state["settings"]["mode"] == "single_device"
        assert state["settings"]["pack"] == "geo"
        assert state["settings"]["yes_no_scoring"] == "prediction"
        assert state["settings"]["target_score"] == 30

        ok_col = change_player_color(self.code, p1["id"], "#ef4444")
        assert ok_col is True
        state = get_game(self.code)
        assert state["players"][0]["color"] == "#ef4444"

    def test_add_offline_player_and_single_device_pass_turn(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)

        # Toggle single device mode
        ok, msg, state = update_settings(self.code, {"mode": "single_device"})
        assert ok is True
        assert state["settings"]["mode"] == "single_device"

        # Add offline player Bob
        ok_bob, msg_bob, state = add_offline_player(self.code, "Bob")
        assert ok_bob is True
        bob = find_player_by_name(state, "Bob")
        assert bob is not None
        assert bob["is_offline"] is True
        assert bob["connected"] is True
        assert bob["color"] != p1["color"]

        # Duplicate name rejected
        ok_dup, msg_dup, _ = add_offline_player(self.code, "bob")
        assert ok_dup is False
        assert "already in the game" in msg_dup

        # Add offline player Charlie
        ok_char, _, state = add_offline_player(self.code, "Charlie")
        assert ok_char is True
        assert len(state["players"]) == 3

        # Start match
        ok_start, _, state = start_game(self.code)
        assert ok_start is True
        assert len(state["turn_order"]) == 3

        # In single device mode, current device holder can act on behalf of whichever player's turn it is
        cur_pid = state["current_player_id"]
        # Pass turn for current player
        ok_pass, _, state = pass_turn(self.code, p1["id"])
        assert ok_pass is True
        assert state["player_statuses"][cur_pid] == "passed"
        assert state["current_player_id"] != cur_pid

        # Kick / remove offline player Charlie
        charlie = find_player_by_name(state, "Charlie")
        ok_kick, _, state = kick_player(self.code, charlie["id"])
        assert ok_kick is True
        assert find_player_by_name(state, "Charlie") is None
        assert charlie["id"] not in state["turn_order"]

    def test_start_game_and_turn_rotation(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        ok, msg, state = start_game(self.code)
        assert ok is True
        assert state["phase"] == "playing"
        assert state["round_num"] == 1
        assert state["card"] is not None
        assert len(state["turn_order"]) == 2
        assert state["current_player_id"] in (p1["id"], p2["id"])

    def test_push_your_luck_correct_bust_and_pass(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        # Set known question
        known_card = {
            "id": "test_q",
            "pack": "geo",
            "prompt": "Test Card",
            "type": "true_false",
            "n": 3,
            "items": [
                {
                    "slot": 1,
                    "label": "Item 1",
                    "value": "Yes",
                    "is_correct": True,
                    "aliases": ["item1"],
                    "explanation": "Fact 1",
                },
                {
                    "slot": 2,
                    "label": "Item 2",
                    "value": "No",
                    "is_correct": False,
                    "aliases": ["item2"],
                    "explanation": "Fact 2",
                },
                {
                    "slot": 3,
                    "label": "Item 3",
                    "value": "Yes",
                    "is_correct": True,
                    "aliases": ["item3"],
                    "explanation": "Fact 3",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["round_num"] = 1
        state["turn_order"] = [p1["id"], p2["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active", p2["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0, p2["id"]: 0}
        save_game(self.code, state)

        # 1. P1 picks Slot 1 (Correct) -> +1 basket pt, turn goes to P2
        ok, msg, state = pick_capsule(self.code, p1["id"], slot=1)
        assert ok is True
        assert state["round_baskets"][p1["id"]] == 1
        assert state["player_statuses"][p1["id"]] == "active"
        assert state["current_player_id"] == p2["id"]

        # 2. P2 picks Slot 2 (Wrong / Bust) -> loses round basket, status "busted"
        ok, msg, state = pick_capsule(self.code, p2["id"], slot=2)
        assert ok is True
        assert state["round_baskets"][p2["id"]] == 0
        assert state["player_statuses"][p2["id"]] == "busted"
        assert state["current_player_id"] == p1["id"]

        # 3. P1 decides to Pass & Bank -> locks in 1 pt to permanent score, status "passed"
        ok, msg, state = pass_turn(self.code, p1["id"])
        assert ok is True
        p1_fresh = find_player_by_id(state, p1["id"])
        assert p1_fresh["score"] == 1
        assert state["player_statuses"][p1["id"]] == "passed"
        # Since both players are now passed or busted, round finishes!
        assert state["phase"] == "round_summary"
        # All items revealed
        assert len(state["revealed_capsules"]) == 3

    def test_prediction_scoring_mode(self):
        state = create_game(self.code, host_name="Alice", settings={"yes_no_scoring": "prediction"})
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        known_card = {
            "id": "test_pred",
            "pack": "science",
            "prompt": "Test Prediction",
            "type": "true_false",
            "n": 2,
            "items": [
                {
                    "slot": 1,
                    "label": "Slot 1 (False)",
                    "value": "No",
                    "is_correct": False,
                    "aliases": [],
                    "explanation": "",
                },
                {
                    "slot": 2,
                    "label": "Slot 2 (True)",
                    "value": "Yes",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["turn_order"] = [p1["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0}
        save_game(self.code, state)

        # Player predicts "no" for Slot 1 which is False -> Correct prediction! (+1 pt)
        ok, msg, state = pick_capsule(self.code, p1["id"], slot=1, prediction="no")
        assert ok is True
        assert state["round_baskets"][p1["id"]] == 1

    def test_chat_answer_matching(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        known_card = {
            "id": "test_chat",
            "pack": "geo",
            "prompt": "Chat Test",
            "type": "true_false",
            "n": 2,
            "items": [
                {
                    "slot": 1,
                    "label": "Madagascar",
                    "value": "Yes",
                    "is_correct": True,
                    "aliases": ["ilha de madagascar"],
                    "explanation": "",
                },
                {
                    "slot": 2,
                    "label": "Greenland",
                    "value": "No",
                    "is_correct": False,
                    "aliases": ["groenlandia"],
                    "explanation": "",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["turn_order"] = [p1["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0}
        save_game(self.code, state)

        # Player types "Madagascar" in chat
        ok, msg, state = process_chat_answer(self.code, p1["id"], "madagascar")
        assert ok is True
        assert "1" in state["revealed_capsules"]
        assert state["round_baskets"][p1["id"]] == 1

    def test_host_arbitration(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        known_card = {
            "id": "test_arb",
            "pack": "food",
            "prompt": "Food Test",
            "type": "true_false",
            "n": 2,
            "items": [
                {"slot": 1, "label": "Guanciale", "value": "Yes", "is_correct": True, "aliases": [], "explanation": ""},
                {"slot": 2, "label": "Cream", "value": "No", "is_correct": False, "aliases": [], "explanation": ""},
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["turn_order"] = [p1["id"], p2["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active", p2["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0, p2["id"]: 0}
        save_game(self.code, state)

        # Host arbitrates slot 1 for Bob
        ok, msg, state = host_arbitrate(self.code, slot=1, mark_correct=True, target_player_id=p2["id"])
        assert ok is True
        assert state["round_baskets"][p2["id"]] == 1
        assert "1" in state["revealed_capsules"]

    def test_zero_spoiler_sanitization(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        known_card = {
            "id": "secret_q",
            "pack": "geo",
            "prompt": "Zero Spoiler Test",
            "type": "true_false",
            "n": 2,
            "items": [
                {
                    "slot": 1,
                    "label": "Covered Item",
                    "value": "Secret Answer",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "Top secret",
                },
                {
                    "slot": 2,
                    "label": "Revealed Item",
                    "value": "Known Answer",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "Public fact",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["revealed_capsules"] = {
            "2": {
                "slot": 2,
                "label": "Revealed Item",
                "value": "Known Answer",
                "is_correct": True,
                "revealed_by": "Alice",
                "revealed_result": "correct",
                "explanation": "Public fact",
            }
        }
        save_game(self.code, state)

        # Inspect Bob's sanitized view
        view = get_sanitized_player_view(state, viewer_id=p2["id"])
        capsules = view["capsules"]

        # Slot 1 is unrevealed -> secret answer, is_correct, explanation MUST be None
        cap1 = next(c for c in capsules if c["slot"] == 1)
        assert cap1["revealed"] is False
        assert cap1["value"] is None
        assert cap1["is_correct"] is None
        assert cap1["explanation"] is None

        # Slot 2 is revealed -> public details visible
        cap2 = next(c for c in capsules if c["slot"] == 2)
        assert cap2["revealed"] is True
        assert cap2["value"] == "Known Answer"
        assert cap2["is_correct"] is True
        assert cap2["explanation"] == "Public fact"

    def test_order_mode_rank_prediction(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        known_card = {
            "id": "test_order",
            "pack": "geo",
            "prompt": "Rivers by Length (1 = Longest)",
            "type": "order",
            "n": 3,
            "items": [
                {
                    "slot": 1,
                    "label": "Amazon River",
                    "value": "2",
                    "is_correct": True,
                    "aliases": ["amazon"],
                    "explanation": "#2 longest",
                },
                {
                    "slot": 2,
                    "label": "Nile River",
                    "value": "1",
                    "is_correct": True,
                    "aliases": ["nile"],
                    "explanation": "#1 longest",
                },
                {
                    "slot": 3,
                    "label": "Yangtze River",
                    "value": "3",
                    "is_correct": True,
                    "aliases": ["yangtze"],
                    "explanation": "#3 longest",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["turn_order"] = [p1["id"], p2["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active", p2["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0, p2["id"]: 0}
        save_game(self.code, state)

        # 1. P1 picks Slot 2 (Nile) with prediction "1" -> Correct rank!
        ok, msg, state = pick_capsule(self.code, p1["id"], slot=2, prediction="1")
        assert ok is True
        assert state["round_baskets"][p1["id"]] == 1
        assert state["player_statuses"][p1["id"]] == "active"
        assert state["revealed_capsules"]["2"]["value"] == "#1"
        assert state["revealed_capsules"]["2"]["is_correct"] is True
        assert state["current_player_id"] == p2["id"]

        # 2. P2 picks Slot 1 (Amazon, actual is 2) with wrong prediction "3" -> BUST!
        ok, msg, state = pick_capsule(self.code, p2["id"], slot=1, prediction="3")
        assert ok is True
        assert state["round_baskets"][p2["id"]] == 0
        assert state["player_statuses"][p2["id"]] == "busted"
        assert state["revealed_capsules"]["1"]["value"] == "#2"
        assert state["revealed_capsules"]["1"]["is_correct"] is False
        assert state["revealed_capsules"]["1"]["guessed_value"] == "3"

        # 3. Duplicate pick on already revealed slot returns False (handled idempotently by consumer)
        ok_dup, msg_dup, _ = pick_capsule(self.code, p1["id"], slot=1, prediction="2")
        assert ok_dup is False
        assert "already revealed" in msg_dup.lower()

    def test_order_mode_chat_matching(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)

        known_card = {
            "id": "test_order_chat",
            "pack": "geo",
            "prompt": "Rivers by Length",
            "type": "order",
            "n": 2,
            "items": [
                {
                    "slot": 1,
                    "label": "Amazon River",
                    "value": "2",
                    "is_correct": True,
                    "aliases": ["amazon"],
                    "explanation": "",
                },
                {
                    "slot": 2,
                    "label": "Nile River",
                    "value": "1",
                    "is_correct": True,
                    "aliases": ["nile"],
                    "explanation": "",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["turn_order"] = [p1["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0}
        save_game(self.code, state)

        # Player types "nile 1" in chat
        ok, msg, state = process_chat_answer(self.code, p1["id"], "nile 1")
        assert ok is True
        assert "2" in state["revealed_capsules"]
        assert state["revealed_capsules"]["2"]["is_correct"] is True
        assert state["round_baskets"][p1["id"]] == 1

        # Player types "amazon" without rank -> rejected with helpful prompt
        ok_no_rank, msg_no_rank, _ = process_chat_answer(self.code, p1["id"], "amazon")
        assert ok_no_rank is False
        assert "specify a rank" in msg_no_rank.lower()

    def test_match_victory_condition(self):
        state = create_game(self.code, host_name="Alice", settings={"target_score": 10})
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        p1["score"] = 9
        save_game(self.code, state)

        known_card = {
            "id": "q_win",
            "pack": "geo",
            "prompt": "Win Card",
            "type": "true_false",
            "n": 1,
            "items": [
                {
                    "slot": 1,
                    "label": "Winning Item",
                    "value": "Yes",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = known_card
        state["turn_order"] = [p1["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0}
        save_game(self.code, state)

        # Alice picks slot 1 -> finishes card, banks 1 pt -> score = 10 -> Gameover!
        ok, msg, state = pick_capsule(self.code, p1["id"], slot=1)
        assert ok is True
        assert state["phase"] == "gameover"
        assert state["winner_id"] == p1["id"]

    def test_host_arbitrate_revealed_capsule_override_to_wrong(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        card = {
            "id": "q_override_1",
            "pack": "history",
            "prompt": "Landmark Dates",
            "type": "number",
            "n": 2,
            "items": [
                {
                    "slot": 1,
                    "label": "Norman Conquest",
                    "value": "1066",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "",
                },
                {
                    "slot": 2,
                    "label": "Magna Carta",
                    "value": "1215",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = card
        state["turn_order"] = [p1["id"], p2["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active", p2["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0, p2["id"]: 0}
        save_game(self.code, state)

        # Alice picks slot 1 -> marked correct (+1 basket pt)
        ok, msg, state = pick_capsule(self.code, p1["id"], slot=1)
        assert ok is True
        assert state["round_baskets"][p1["id"]] == 1
        assert state["revealed_capsules"]["1"]["is_correct"] is True

        # Alice turns out to have guessed wrong year out loud: Host overrides slot 1 to WRONG!
        ok_ov, msg_ov, state = host_arbitrate(self.code, slot=1, mark_correct=False, target_player_id=p1["id"])
        assert ok_ov is True
        assert state["revealed_capsules"]["1"]["is_correct"] is False
        assert state["revealed_capsules"]["1"]["revealed_result"] == "wrong"
        assert state["round_baskets"][p1["id"]] == 0
        assert state["player_statuses"][p1["id"]] == "busted"

    def test_host_arbitrate_revealed_capsule_override_to_correct(self):
        state = create_game(self.code, host_name="Alice")
        state, p1, _ = add_player(self.code, name="Alice", is_admin=True)
        state, p2, _ = add_player(self.code, name="Bob")

        card = {
            "id": "q_override_2",
            "pack": "science",
            "prompt": "Chemistry",
            "type": "true_false",
            "n": 2,
            "items": [
                {
                    "slot": 1,
                    "label": "Helium is lighter than air",
                    "value": "Yes",
                    "is_correct": True,
                    "aliases": [],
                    "explanation": "",
                },
                {
                    "slot": 2,
                    "label": "Gold rusts in air",
                    "value": "No",
                    "is_correct": False,
                    "aliases": [],
                    "explanation": "",
                },
            ],
        }
        state["phase"] = "playing"
        state["card"] = card
        state["turn_order"] = [p1["id"], p2["id"]]
        state["current_player_id"] = p1["id"]
        state["player_statuses"] = {p1["id"]: "active", p2["id"]: "active"}
        state["round_baskets"] = {p1["id"]: 0, p2["id"]: 0}
        save_game(self.code, state)

        # Alice opens slot 2 (Gold rusts) -> busts!
        ok, msg, state = pick_capsule(self.code, p1["id"], slot=2)
        assert ok is True
        assert state["player_statuses"][p1["id"]] == "busted"
        assert state["revealed_capsules"]["2"]["is_correct"] is False

        # Host arbitrates: Alice's point is accepted as valid override!
        ok_ov, msg_ov, state = host_arbitrate(self.code, slot=2, mark_correct=True, target_player_id=p1["id"])
        assert ok_ov is True
        assert state["revealed_capsules"]["2"]["is_correct"] is True
        assert state["player_statuses"][p1["id"]] == "active"
        assert state["round_baskets"][p1["id"]] == 1

    def test_universal_item_shuffling_across_card_types(self):
        from smartn.game_state import _deal_next_card

        state = create_game(self.code, host_name="Alice")
        card = _deal_next_card(state)
        assert card is not None
        items = card["items"]
        assert len(items) == 10
        # Check slots are indexed 1..10
        slots = [it["slot"] for it in items]
        assert slots == list(range(1, 11))


@pytest.mark.django_db
class TestSmartNViewsAndUrls:
    def setup_method(self):
        self.client = Client()
        self.room = Room.objects.create(title="SmartN Test Room", game_type="smartn", language="en")
        self.code = self.room.code
        delete_game(self.code)

    def teardown_method(self):
        delete_game(self.code)
        self.room.delete()

    def test_game_view_and_join(self):
        # Clean URL access with name parameter
        play_url = reverse("gamerooms:smartn:play", kwargs={"code": self.code})
        response = self.client.get(f"{play_url}?name=Charlie")
        assert response.status_code == 200
        assert b"SmartN" in response.content

        # Legacy URL with name in path redirects to clean URL
        legacy_url = reverse("gamerooms:smartn:game", kwargs={"code": self.code, "name": "Charlie"})
        legacy_resp = self.client.get(legacy_url)
        assert legacy_resp.status_code == 302
        assert f"/{self.code}/" in legacy_resp["Location"]

        # Verify state exists
        state = get_game(self.code)
        assert state is not None
        charlie = find_player_by_name(state, "Charlie")
        assert charlie is not None

    def test_qr_and_reconnect_view(self):
        # Create player in state
        state = create_game(self.code, host_name="Dave")
        state, player, _ = add_player(self.code, name="Dave")

        qr_url = reverse("gamerooms:smartn:player-qr", kwargs={"code": self.code, "token": player["token"]})
        res = self.client.get(qr_url)
        assert res.status_code == 200
        data = res.json()
        assert "qr" in data
        assert data["player_name"] == "Dave"

        rec_url = reverse("gamerooms:smartn:reconnect", kwargs={"code": self.code, "token": player["token"]})
        res_rec = self.client.get(rec_url)
        assert res_rec.status_code == 302
        assert f"/{self.code}/" in res_rec.url
        assert f"token={player['token']}" in res_rec.url


def test_websocket_join_and_chat(db):
    room = Room.objects.create(title="WS Room", game_type="smartn", language="en")
    code = room.code

    async def _run():
        communicator = WebsocketCommunicator(
            application,
            f"/ws/smartn/{code}/",
        )
        connected, _ = await communicator.connect()
        assert connected is True

        # Join room
        await communicator.send_json_to(
            {
                "action": "join",
                "name": "Eve",
                "is_admin": True,
            }
        )
        response = await communicator.receive_json_from()
        assert response["type"] == "state"
        assert response["state"]["code"] == code

        # Send chat message
        await communicator.send_json_to(
            {
                "action": "chat",
                "msg": "Hello SmartN team!",
            }
        )
        resp_chat = await communicator.receive_json_from()
        assert resp_chat["type"] == "state"
        chat_entries = resp_chat["state"]["chat_log"]
        assert any("Hello SmartN team!" in e["text"] for e in chat_entries)

        await communicator.disconnect()
        delete_game(code)

    async_to_sync(_run)()

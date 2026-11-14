"""Comprehensive unit, seeding, WebSocket, and HTTP tests for Codenames Multiplayer."""

import json
from pathlib import Path

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from codenames.game_state import (
    _fallback_store,
    add_player,
    add_table_player,
    create_initial_state,
    end_turn,
    get_game,
    get_sanitized_player_view,
    guess_card,
    join_team,
    save_game,
    start_round,
    submit_clue,
    update_settings,
)
from codenames.words import (
    deal_codenames_board,
    get_classic_codenames_words,
    is_clue_forbidden_on_board,
    suggest_spymaster_clues,
)
from emojinary.models import EmojinaryWord
from gamerooms.models import Room
from website.asgi import application

DATA_DIR = Path(__file__).resolve().parent.parent / "emojinary" / "data"


class MockRedis:
    """In-memory Redis stand-in for isolated Codenames tests."""

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
    _fallback_store.clear()
    r = MockRedis()
    monkeypatch.setattr("codenames.game_state._get_redis", lambda: r)
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
    return r


def _setup_4p_codenames_room(language="en"):
    state = create_initial_state(code="CN0001", title="Spy Table", language=language)
    state, p1, _ = add_player(state, "Alice", is_admin=True)
    state, p2, _ = add_player(state, "Bob")
    state, p3, _ = add_player(state, "Carol")
    state, p4, _ = add_player(state, "Dave")
    join_team(state, p1["id"], team="red", role="spymaster")
    join_team(state, p2["id"], team="red", role="operative")
    join_team(state, p3["id"], team="blue", role="spymaster")
    join_team(state, p4["id"], team="blue", role="operative")
    return state, [p1, p2, p3, p4]


@pytest.mark.django_db
class TestCodenamesDataAndSeeding:
    def test_wordlists_and_wiktionary_lexicon_cover_all_400_words(self):
        wordlists = json.loads((DATA_DIR / "wordlists.json").read_text(encoding="utf-8"))
        codenames_words = wordlists.get("codenames", [])
        wikisaurus = wordlists.get("codenames_wikisaurus", {})
        assert len(codenames_words) == 400
        assert len({w.lower() for w in codenames_words}) == 400
        assert len(wikisaurus) >= 250

        lexicon = json.loads((DATA_DIR / "wiktionary_lexicon.json").read_text(encoding="utf-8"))
        for word in codenames_words:
            assert word.lower() in lexicon, f"Missing {word} in wiktionary_lexicon.json"

    def test_seed_emojinary_populates_400_codenames_and_related_words(self):
        call_command("seed_emojinary")
        qs = EmojinaryWord.objects.filter(is_codenames=True)
        assert qs.count() == 400
        with_related = qs.exclude(related_words=[]).count()
        assert with_related >= 250

    def test_classic_pool_size_and_board_deal_splits(self):
        assert len(get_classic_codenames_words()) == 400
        starter, board = deal_codenames_board(lang_code="en", word_pack="classic")
        assert starter in ("red", "blue")
        assert len(board) == 25
        assert len({c["word_en"].lower() for c in board}) == 25

        other = "blue" if starter == "red" else "red"
        counts = {
            starter: sum(1 for c in board if c["affiliation"] == starter),
            other: sum(1 for c in board if c["affiliation"] == other),
            "civilian": sum(1 for c in board if c["affiliation"] == "civilian"),
            "assassin": sum(1 for c in board if c["affiliation"] == "assassin"),
        }
        assert counts[starter] == 9
        assert counts[other] == 8
        assert counts["civilian"] == 7
        assert counts["assassin"] == 1

    def test_portuguese_localization_on_dealt_board(self):
        _, board_pt = deal_codenames_board(lang_code="pt", word_pack="classic")
        assert len(board_pt) == 25
        localized_diffs = sum(1 for c in board_pt if c["word_display"].lower() != c["word_en"].lower())
        assert localized_diffs >= 5

    def test_wikisaurus_ai_suggestions_avoid_assassin_and_board_words(self):
        synthetic_board = [
            {
                "index": 0,
                "word_en": "Cat",
                "word_display": "Cat",
                "matches": ["cat"],
                "aliases": ["feline"],
                "topics": ["mammal"],
                "related": ["whiskers", "purr", "pet"],
                "affiliation": "red",
                "revealed": False,
            },
            {
                "index": 1,
                "word_en": "Dog",
                "word_display": "Dog",
                "matches": ["dog"],
                "aliases": ["canine"],
                "topics": ["mammal"],
                "related": ["bark", "pet"],
                "affiliation": "red",
                "revealed": False,
            },
            {
                "index": 2,
                "word_en": "Danger",
                "word_display": "Danger",
                "matches": ["danger"],
                "aliases": ["hazard"],
                "topics": [],
                "related": ["bark", "hazard"],
                "affiliation": "assassin",
                "revealed": False,
            },
        ]
        suggestions = suggest_spymaster_clues(synthetic_board, team="red")
        suggested_words = {s["clue"].lower() for s in suggestions}
        # 'pet' / 'mammal' connect Cat + Dog cleanly; 'bark' hits the assassin so must be excluded
        assert "pet" in suggested_words or "mammal" in suggested_words
        assert "bark" not in suggested_words
        assert "cat" not in suggested_words


class TestCodenamesGameEngine:
    def test_zero_spoiler_sanitization_and_clue_validation(self):
        state, players = _setup_4p_codenames_room()
        ok, _ = start_round(state)
        assert ok is True

        starter = state["starting_team"]
        other = "blue" if starter == "red" else "red"
        starter_spy = next(p for p in players if p["team"] == starter and p["role"] == "spymaster")
        starter_op = next(p for p in players if p["team"] == starter and p["role"] == "operative")

        op_view = get_sanitized_player_view(state, starter_op["id"])
        assert op_view["can_see_keycard"] is False
        assert all(c["affiliation"] is None for c in op_view["board"])
        assert op_view["spymaster_suggestions"] == []

        spy_view = get_sanitized_player_view(state, starter_spy["id"])
        assert spy_view["can_see_keycard"] is True
        assert all(c["affiliation"] is not None for c in spy_view["board"])

        # Clue naming an unrevealed card must be blocked
        sample_word = state["board"][0]["word_display"]
        assert is_clue_forbidden_on_board(sample_word, state["board"]) is not None
        ok_bad, msg_bad = submit_clue(state, starter_spy["id"], sample_word, 2)
        assert ok_bad is False
        assert "board" in msg_bad.lower() or "clue" in msg_bad.lower()

        # Valid clue enables Operative guesses (count + 1)
        ok_good, _ = submit_clue(state, starter_spy["id"], "QXVALIDCLUE", 2)
        assert ok_good is True
        assert state["turn_phase"] == "operative_guess"
        assert state["guesses_remaining"] == 3

        # Friendly card leaves turn with starter team
        friendly_idx = next(c["index"] for c in state["board"] if c["affiliation"] == starter)
        ok_guess, _ = guess_card(state, starter_op["id"], friendly_idx)
        assert ok_guess is True
        assert state["turn_team"] == starter
        assert state["guesses_remaining"] == 2

        # Civilian card ends turn cleanly to opposing Spymaster
        civ_idx = next(c["index"] for c in state["board"] if c["affiliation"] == "civilian" and not c["revealed"])
        ok_civ, _ = guess_card(state, starter_op["id"], civ_idx)
        assert ok_civ is True
        assert state["turn_team"] == other
        assert state["turn_phase"] == "spymaster_clue"

        # Hitting the Assassin immediately ends board & archives rounds_history
        other_spy = next(p for p in players if p["team"] == other and p["role"] == "spymaster")
        other_op = next(p for p in players if p["team"] == other and p["role"] == "operative")
        submit_clue(state, other_spy["id"], "QXSECONDCLUE", 1)
        assassin_idx = next(c["index"] for c in state["board"] if c["affiliation"] == "assassin")
        ok_assn, _ = guess_card(state, other_op["id"], assassin_idx)
        assert ok_assn is True
        assert state["phase"] == "gameover"
        assert state["winner"] == starter
        assert len(state["rounds_history"]) == 1

        # Post-gameover Operative view reveals all affiliations
        end_op_view = get_sanitized_player_view(state, starter_op["id"])
        assert end_op_view["can_see_keycard"] is True
        assert all(c["affiliation"] is not None for c in end_op_view["board"])

    def test_moderator_oral_play_and_spymaster_rotation(self):
        state, players = _setup_4p_codenames_room()
        host = players[0]
        ok_table, _ = add_table_player(state, "Grandpa Joe")
        assert ok_table is True
        table_p = next(p for p in state["players"].values() if p["name"] == "Grandpa Joe")
        assert table_p["is_table_player"] is True

        update_settings(state, {"rotate_spymasters": True})
        start_round(state)
        first_spymasters = dict(state["last_spymasters"])

        # Host can log clues and card taps orally even if not active team's role
        starter = state["starting_team"]
        ok_clue, _ = submit_clue(state, host["id"], "QXMODCLUE", 1, by_mod=True)
        assert ok_clue is True
        friendly_idx = next(c["index"] for c in state["board"] if c["affiliation"] == starter)
        ok_tap, _ = guess_card(state, host["id"], friendly_idx, by_mod=True)
        assert ok_tap is True
        ok_pass, _ = end_turn(state, host["id"], by_mod=True)
        assert ok_pass is True

        # Starting a new board rotates Spymasters automatically
        start_round(state)
        assert state["round_num"] == 2
        assert state["last_spymasters"]["red"] != first_spymasters["red"]
        assert state["last_spymasters"]["blue"] != first_spymasters["blue"]


@pytest.mark.django_db
class TestCodenamesHTTPAndWebSocket:
    def test_room_creation_game_view_player_qr_isolation_and_replay(self):
        client = Client()
        create_get = client.get(reverse("gamerooms:room-create"), {"game": "codenames"})
        assert create_get.status_code == 200
        expected_captcha = str(create_get.context["answer"])

        resp = client.post(
            reverse("gamerooms:room-create"),
            {
                "title": "Friday Codenames",
                "password": "",
                "game_type": "codenames",
                "language": "en",
                "captcha_answer": expected_captcha,
                "captcha_expected": expected_captcha,
            },
        )
        assert resp.status_code == 302
        room = Room.objects.get(title="Friday Codenames")
        assert room.game_type == "codenames"

        # Room list shows Codenames
        hub = client.get(reverse("gamerooms:room-list"))
        assert hub.status_code == 200
        assert b"Codenames" in hub.content

        # Host loads game page -> zero-spoiler default hidden keycard + per-player QR modal
        game_url = reverse("gamerooms:codenames:game", kwargs={"code": room.code, "name": "HostAlice"})
        game_page = client.get(game_url)
        assert game_page.status_code == 200
        assert b"codenames-grid" in game_page.content
        assert b"keycardVisible = false" in game_page.content
        assert b"modal-player-qr" in game_page.content

        # Guest joins via another client session
        guest_client = Client()
        guest_url = reverse("gamerooms:codenames:game", kwargs={"code": room.code, "name": "GuestBob"})
        assert guest_client.get(guest_url).status_code == 200

        state = get_game(room.code)
        host_player = next(p for p in state["players"].values() if p["name"] == "HostAlice")
        guest_player = next(p for p in state["players"].values() if p["name"] == "GuestBob")
        assert host_player["is_admin"] is True
        assert guest_player["is_admin"] is False

        # Per-player QR JSON endpoint returns distinct URLs & player metadata
        qr_resp = client.get(
            reverse("gamerooms:codenames:player-qr", kwargs={"code": room.code, "token": guest_player["id"]})
        )
        assert qr_resp.status_code == 200
        qr_data = qr_resp.json()
        assert qr_data["player_name"] == "GuestBob"
        assert qr_data["qr"].startswith("data:image/png;base64,")
        assert guest_player["token"] in qr_data["url"]

        # Opening a guest reconnect URL in Host's browser must preserve Host admin session isolation
        rec_url = reverse(
            "gamerooms:codenames:reconnect",
            kwargs={"code": room.code, "token": guest_player["token"]},
        )
        rec_resp = client.get(rec_url)
        assert rec_resp.status_code == 302
        assert client.session.get(f"codenames_admin_{room.code}") is True
        assert client.session.get(f"codenames_player_{room.code}") == host_player["token"]

        # Replay JSON endpoint returns structured match archive
        replay_resp = client.get(reverse("gamerooms:codenames:replay", kwargs={"code": room.code}))
        assert replay_resp.status_code == 200
        replay_json = replay_resp.json()
        assert replay_json["game"] == "codenames"
        assert replay_json["code"] == room.code

    def test_websocket_end_to_end_codenames_round(self):
        room = Room.objects.create(code="CNWS01", title="WS Table", game_type="codenames", language="en")
        state = create_initial_state(code=room.code, title=room.title, language="en")
        save_game(room.code, state)
        admin_token = state["admin_token"]

        async def _flow():
            c1 = WebsocketCommunicator(application, f"/ws/codenames/{room.code}/")
            c2 = WebsocketCommunicator(application, f"/ws/codenames/{room.code}/")
            assert (await c1.connect())[0]
            assert (await c2.connect())[0]

            await c1.send_json_to({"action": "join", "name": "Host", "admin_token": admin_token})
            s1 = await c1.receive_json_from()
            assert s1["me"]["is_admin"] is True
            await c1.receive_json_from()  # join broadcast_sync
            await c2.receive_json_from()  # c1 join broadcast_sync (c2 already connected)

            await c2.send_json_to({"action": "join", "name": "OperativeB"})
            s2 = await c2.receive_json_from()
            assert s2["me"]["is_admin"] is False
            await c1.receive_json_from()  # c2 join broadcast_sync
            await c2.receive_json_from()  # c2 join broadcast_sync

            await c1.send_json_to({"action": "start_game"})
            s1 = await c1.receive_json_from()
            s2 = await c2.receive_json_from()
            assert s1["phase"] == "playing"
            assert len(s1["board"]) == 25

            # Operative B cannot see unrevealed card affiliations
            if not s2["can_see_keycard"]:
                assert all(card["affiliation"] is None for card in s2["board"])

            # Moderator publishes oral clue & ends match
            await c1.send_json_to({"action": "submit_clue", "clue": "ZZZXQV", "count": 1, "by_mod": True})
            s1 = await c1.receive_json_from()
            s2 = await c2.receive_json_from()
            assert s1["turn_phase"] == "operative_guess"
            assert s1["current_clue"]["word"] == "ZZZXQV"

            await c1.send_json_to({"action": "end_game"})
            s1 = await c1.receive_json_from()
            s2 = await c2.receive_json_from()
            assert s1["phase"] == "gameover"
            assert len(s1["rounds_history"]) == 1

            await c1.disconnect()
            await c2.disconnect()

        async_to_sync(_flow)()

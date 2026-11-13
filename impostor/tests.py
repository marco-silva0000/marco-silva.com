"""Comprehensive unit and async WebSocket tests for Advanced Word Impostor."""

import json

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import Client
from django.urls import reverse

from gamerooms.models import Room
from impostor.game_state import (
    _fallback_store,
    add_custom_pair,
    add_player,
    cast_vote,
    create_initial_state,
    get_sanitized_player_view,
    start_round,
    submit_clue,
    submit_steal_guess,
    update_settings,
)
from impostor.word_pairs import (
    CURATED_IMPOSTOR_PAIRS,
    localize_impostor_pair,
    normalize_text,
    text_matches_term,
)
from website.asgi import application


class MockRedis:
    """In-memory mock Redis store for isolated tests."""

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
    monkeypatch.setattr("impostor.game_state._get_redis", lambda: r)
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
    return r


def _build_4p_room(poison_mode="undercover_blind", enable_lethal=True, language="en"):
    state = create_initial_state(code="IMP001", title="Spy Lounge", language=language)
    update_settings(
        state,
        {
            "poison_mode": poison_mode,
            "enable_lethal_word": enable_lethal,
            "clue_loops": 1,
            "steal_timer": 15,
            "max_rounds": 3,
        },
    )
    state, p1, _ = add_player(state, "Alice", is_admin=True)  # Participating Game Master
    state, p2, _ = add_player(state, "Bob")
    state, p3, _ = add_player(state, "Carol")
    state, p4, _ = add_player(state, "Dave")
    return state, [p1, p2, p3, p4]


class TestWordPairsAndLocalization:
    def test_curated_bank_integrity(self):
        assert len(CURATED_IMPOSTOR_PAIRS) >= 80
        for citizen, poison, lethal, cat in CURATED_IMPOSTOR_PAIRS:
            assert citizen and poison and lethal and cat
            assert normalize_text(citizen) != normalize_text(poison)
            assert normalize_text(citizen) != normalize_text(lethal)

    def test_wiktionary_localization_and_matching(self):
        pair_pt = localize_impostor_pair("Coffee", "Tea", "Caffeine", "food", lang_code="pt")
        # Both localized form & canonical English form match accents-insensitively
        assert text_matches_term("coffee", pair_pt["citizen_matches"])
        assert text_matches_term(pair_pt["citizen_display"], pair_pt["citizen_matches"])
        if pair_pt["citizen_display"].lower() != "coffee":
            # Expect Portuguese Wiktionary translation (e.g. café / cafe)
            assert text_matches_term("cafe", pair_pt["citizen_matches"])


class TestPoisonModesAndParticipatingGM:
    def test_undercover_blind_hides_role_labels_and_spoilers_from_gm(self):
        state, players = _build_4p_room(poison_mode="undercover_blind")
        ok, _ = start_round(state)
        assert ok is True
        gm_id = players[0]["id"]

        for p in players:
            view = get_sanitized_player_view(state, p["id"])
            assert view["reveal"] is None
            assert view["my_card"]["role_revealed"] is False
            assert view["my_card"]["word"] in (
                state["current_pair"]["citizen_display"],
                state["current_pair"]["poison_display"],
            )
            assert "impostor_id" not in view
            assert "current_pair" not in view

        # Even Participating GM cannot see citizen_word/lethal_word in sanitized JSON during clue phase
        gm_view = get_sanitized_player_view(state, gm_id)
        assert gm_view["me"]["is_admin"] is True
        assert gm_view["can_blind_redraw"] is True
        dumped = json.dumps(gm_view)
        assert state["current_pair"]["lethal_display"] not in dumped

    def test_blind_redraw_swaps_words_before_clues(self):
        state, _ = _build_4p_room(poison_mode="undercover_informed")
        start_round(state)
        first_key = state["current_pair"]["pair_key"]
        ok, _ = start_round(state, is_redraw=True)
        assert ok is True
        assert state["round_num"] == 1
        assert state["current_pair"]["pair_key"] != first_key

    def test_undercover_informed_and_classic_blank_cards(self):
        state, players = _build_4p_room(poison_mode="undercover_informed")
        start_round(state)
        imp_id = state["impostor_id"]
        for p in players:
            card = get_sanitized_player_view(state, p["id"])["my_card"]
            assert card["role_revealed"] is True
            if p["id"] == imp_id:
                assert card["role_type"] == "impostor"
                assert card["word"] == state["current_pair"]["poison_display"]
            else:
                assert card["role_type"] == "citizen"
                assert card["word"] == state["current_pair"]["citizen_display"]

        # Switch to classic_blank on next round
        update_settings(state, {"poison_mode": "classic_blank"})
        start_round(state)
        imp_card = get_sanitized_player_view(state, state["impostor_id"])["my_card"]
        assert imp_card["word"] is None
        assert imp_card["role_type"] == "impostor"

    def test_poisoned_citizen_drunk_mode_indistinguishable_from_citizen(self):
        state, players = _build_4p_room(poison_mode="poisoned_citizen")
        start_round(state)
        drunk_id = state["poisoned_citizen_id"]
        imp_id = state["impostor_id"]
        assert drunk_id and drunk_id != imp_id

        regular_citizen = next(p for p in players if p["id"] not in (imp_id, drunk_id))
        reg_card = get_sanitized_player_view(state, regular_citizen["id"])["my_card"]
        drunk_card = get_sanitized_player_view(state, drunk_id)["my_card"]
        imp_card = get_sanitized_player_view(state, imp_id)["my_card"]

        assert drunk_card["role_label"] == reg_card["role_label"]
        assert drunk_card["role_revealed"] is False
        assert drunk_card["word"] == state["current_pair"]["poison_display"]
        assert reg_card["word"] == state["current_pair"]["citizen_display"]
        assert imp_card["word"] is None


class TestLethalWordCustomDeckAndVoting:
    def test_citizen_spoiler_rejected_and_lethal_word_eliminates_impostor(self):
        state, players = _build_4p_room(poison_mode="undercover_blind", enable_lethal=True)
        # Queue known pair for deterministic check
        add_custom_pair(state, players[0], "Espresso", "Matcha", lethal_word="Caffeine", category="drink")
        # 5th player? With 4 players, author Alice becomes round_director and 3 players play!
        start_round(state)
        assert state["round_director_id"] == players[0]["id"]
        director_view = get_sanitized_player_view(state, players[0]["id"])
        assert director_view["me"]["is_director"] is True
        assert "Citizens: Espresso" in director_view["my_card"]["word"]

        first_pid = state["turn_order"][0]
        # Trying to say Citizen word verbatim is blocked cleanly
        ok, err = submit_clue(state, first_pid, "hot espresso shot")
        assert ok is False
        assert "secret Citizen word" in err

        # If Impostor steps on the Lethal Taboo Poison Word -> immediate Citizens win
        while state["phase"] == "clue":
            cur_pid = state["turn_order"][state["turn_index"]]
            if cur_pid == state["impostor_id"]:
                ok, _ = submit_clue(state, cur_pid, "caffeine")
                assert ok is True
                break
            else:
                ok, _ = submit_clue(state, cur_pid, "roasted")
                assert ok is True

        assert state["phase"] == "reveal"
        assert state["round_outcome"] == "impostor_poisoned"

    def test_voting_ejection_triggers_last_chance_steal_and_reveal(self):
        state, players = _build_4p_room(poison_mode="classic_blank", enable_lethal=True)
        start_round(state)
        assert len(state["round_participants"]) == 4

        # All 4 speak out loud
        for pid in state["turn_order"]:
            ok, _ = submit_clue(state, pid, spoken=True)
            assert ok is True
        assert state["phase"] == "voting"

        imp_id = state["impostor_id"]
        citizens = [pid for pid in state["round_participants"] if pid != imp_id]
        for c_pid in citizens:
            ok, _ = cast_vote(state, c_pid, imp_id)
            assert ok is True
        ok, _ = cast_vote(state, imp_id, citizens[0])
        assert ok is True

        # Impostor caught -> Last-Chance Steal open!
        assert state["phase"] == "last_chance"
        assert get_sanitized_player_view(state, imp_id)["can_steal"] is True
        assert get_sanitized_player_view(state, citizens[0])["can_steal"] is False

        # Non-impostor cannot steal
        ok, _ = submit_steal_guess(state, citizens[0], state["current_pair"]["citizen_display"])
        assert ok is False

        # Impostor guesses Citizen Word accurately -> HEIST!
        ok, _ = submit_steal_guess(state, imp_id, state["current_pair"]["citizen_display"])
        assert ok is True
        assert state["phase"] == "reveal"
        assert state["round_outcome"] == "impostor_steal"
        assert state["players"][imp_id]["score"] == 3


class TestImpostorHttpAndWebsocket:
    def test_game_view_and_reconnect_http(self, db):
        Room.objects.create(title="Cafe Mystery", code="IMPHTTP1", game_type="impostor", language="pt")
        client = Client()
        resp = client.get(reverse("gamerooms:impostor:game", kwargs={"code": "IMPHTTP1", "name": "Marco"}))
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "Cafe Mystery" in html
        assert "Poison Word Mode" in html
        assert "Portuguese" in html or "🇵🇹" in html

    def test_full_websocket_round_and_failed_steal(self, db):
        Room.objects.create(title="WS Spy Table", code="IMPWS001", game_type="impostor", language="en")

        async def _run():
            c1 = WebsocketCommunicator(application, "/ws/impostor/IMPWS001/")
            c2 = WebsocketCommunicator(application, "/ws/impostor/IMPWS001/")
            c3 = WebsocketCommunicator(application, "/ws/impostor/IMPWS001/")
            for comm in (c1, c2, c3):
                ok, _ = await comm.connect()
                assert ok is True

            await c1.send_json_to({"action": "join", "name": "HostPlayer"})
            s1 = await c1.receive_json_from()
            assert s1["me"]["is_admin"] is True

            await c2.send_json_to({"action": "join", "name": "PlayerTwo"})
            s2 = await c2.receive_json_from()
            await c3.send_json_to({"action": "join", "name": "PlayerThree"})
            s3 = await c3.receive_json_from()

            async def _recv_until(comm, predicate):
                for _ in range(15):
                    msg = await comm.receive_json_from(timeout=2)
                    if predicate(msg):
                        return msg
                raise AssertionError("Timed out waiting for expected WebSocket state")

            s1 = await _recv_until(c1, lambda m: len(m.get("players", [])) == 3)
            s2 = await _recv_until(c2, lambda m: len(m.get("players", [])) == 3)
            s3 = await _recv_until(c3, lambda m: len(m.get("players", [])) == 3)

            # Host starts round
            await c1.send_json_to({"action": "start_game"})
            s1 = await _recv_until(c1, lambda m: m.get("phase") == "clue")
            s2 = await _recv_until(c2, lambda m: m.get("phase") == "clue")
            s3 = await _recv_until(c3, lambda m: m.get("phase") == "clue")
            assert s1["my_card"] is not None

            # Play all spoken turns
            comms = {s1["me"]["id"]: c1, s2["me"]["id"]: c2, s3["me"]["id"]: c3}
            latest_map = {s1["me"]["id"]: s1, s2["me"]["id"]: s2, s3["me"]["id"]: s3}
            for step in range(5):
                cur_state = next(iter(latest_map.values()))
                if cur_state["phase"] != "clue":
                    break
                cur_pid = cur_state["current_player_id"]
                await comms[cur_pid].send_json_to({"action": "spoken_clue"})
                expected_clues = step + 1
                for pid, comm in comms.items():
                    latest_map[pid] = await _recv_until(
                        comm,
                        lambda m, n=expected_clues: len(m.get("clues", [])) >= n,
                    )

            assert next(iter(latest_map.values()))["phase"] == "voting"

            from impostor.game_state import get_game

            raw_state = get_game("IMPWS001")
            imp_pid = raw_state["impostor_id"]
            cit_pids = [pid for pid in raw_state["round_participants"] if pid != imp_pid]

            for c_pid in cit_pids:
                await comms[c_pid].send_json_to({"action": "cast_vote", "target_id": imp_pid})
            await comms[imp_pid].send_json_to({"action": "cast_vote", "target_id": cit_pids[0]})

            imp_view = await _recv_until(comms[imp_pid], lambda m: m.get("phase") == "last_chance")
            assert imp_view["can_steal"] is True

            # Impostor makes a wrong steal guess -> Citizens win +2 pts!
            await comms[imp_pid].send_json_to({"action": "submit_steal_guess", "guess": "definitelywrongwordxyz"})
            final_view = await _recv_until(comms[imp_pid], lambda m: m.get("phase") == "reveal")
            assert final_view["reveal"]["outcome"] == "citizens_win"
            assert final_view["reveal"]["steal_success"] is False

            await c1.disconnect()
            await c2.disconnect()
            await c3.disconnect()

        async_to_sync(_run)()

"""Comprehensive unit and async WebSocket tests for Advanced Word Impostor."""

import json

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import Client
from django.urls import reverse

from gamerooms.models import Room
from impostor.game_state import (
    DEFAULT_SETTINGS,
    _fallback_store,
    add_custom_pair,
    add_player,
    add_table_player,
    cast_vote,
    create_initial_state,
    get_sanitized_player_view,
    start_round,
    start_voting_phase,
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

    def test_new_game_redraws_distinct_impostor_and_preserves_last_impostor(self):
        state = create_initial_state("IMPRDR01")
        state, p1, _ = add_player(state, "Alice", is_admin=True)
        state, p2, _ = add_player(state, "Bob")
        assert {p1["id"], p2["id"]} == set(state["players"].keys())

        start_round(state)
        prev_imp = state["impostor_id"]
        assert state["last_impostor_id"] == prev_imp

        # With 2 active participants, every subsequent start_round must swap to the other player
        for _ in range(8):
            start_round(state)
            assert state["impostor_id"] != prev_imp
            assert state["last_impostor_id"] == state["impostor_id"]
            prev_imp = state["impostor_id"]

        # Simulating play_again (clearing impostor_id while keeping last_impostor_id)
        state["impostor_id"] = None
        state["phase"] = "lobby"
        start_round(state)
        assert state["impostor_id"] != prev_imp


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
        assert "let cardBlurred = true;" in html
        assert "Show Role &amp; Word" in html or "Show Role & Word" in html
        assert "imp-secret-word blurred" in html
        assert "imp-secret-role blurred" in html

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

            # Play all spoken turns across default 2 clue cycles
            comms = {s1["me"]["id"]: c1, s2["me"]["id"]: c2, s3["me"]["id"]: c3}
            latest_map = {s1["me"]["id"]: s1, s2["me"]["id"]: s2, s3["me"]["id"]: s3}
            for step in range(10):
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

    def test_moderator_oral_clue_submission_and_table_players(self, db):
        Room.objects.create(title="Couch Spy Night", code="IMPMOD01", game_type="impostor", language="en")

        state = create_initial_state(code="IMPMOD01", title="Couch Spy Night", language="en")
        state, gm, _ = add_player(state, "ModHost", is_admin=True)
        ok, _ = add_table_player(state, "CouchBob")
        assert ok is True
        ok, _ = add_table_player(state, "CouchCarol")
        assert ok is True
        assert sum(1 for p in state["players"].values() if p.get("is_table_player")) == 2

        add_custom_pair(state, gm, "Espresso", "Matcha", lethal_word="Caffeine", category="drink")
        # 3 players total -> gm is NOT excluded as director so 3 participants play
        ok, _ = start_round(state)
        assert ok is True
        assert len(state["round_participants"]) == 3

        # Pick an active non-host speaker who is the impostor and make Mod log their lethal oral word
        imp_id = state["impostor_id"]
        other_pid = next(pid for pid in state["round_participants"] if pid != gm["id"] and pid != imp_id)
        # First, Mod logs a normal oral clue for other_pid explicitly via target_player_id
        ok, _ = submit_clue(state, gm["id"], clue_text="warm", target_player_id=other_pid)
        assert ok is True
        assert state["clues"][-1]["player_id"] == other_pid
        assert state["clues"][-1]["by_mod"] is True

        # Non-admin cannot submit on behalf of another player via target_player_id (always attributed to caller)
        ok, _ = submit_clue(state, other_pid, clue_text="morning", target_player_id=imp_id)
        assert ok is True
        assert state["clues"][-1]["player_id"] == other_pid
        assert state["clues"][-1]["by_mod"] is False

        # Mod logs lethal word spoken orally by the Impostor -> eliminates the Impostor!
        ok, msg = submit_clue(state, gm["id"], clue_text="caffeine", target_player_id=imp_id)
        assert ok is True
        assert "Impostor eliminated" in msg
        assert state["phase"] == "reveal"
        assert state["round_outcome"] == "impostor_poisoned"
        assert imp_id in state["poisoned_ids"]

    def test_websocket_mod_table_player_and_oral_clue(self, db):
        Room.objects.create(title="WS Oral Room", code="IMPMODWS", game_type="impostor", language="en")

        async def _run():
            c1 = WebsocketCommunicator(application, "/ws/impostor/IMPMODWS/")
            ok, _ = await c1.connect()
            assert ok is True

            await c1.send_json_to({"action": "join", "name": "GameMod"})

            async def _recv_until(comm, predicate):
                for _ in range(20):
                    msg = await comm.receive_json_from(timeout=2)
                    if predicate(msg):
                        return msg
                raise AssertionError("Timed out waiting for expected WebSocket state")

            s = await _recv_until(c1, lambda m: m.get("me", {}).get("is_admin") is True)
            mod_id = s["me"]["id"]

            await c1.send_json_to({"action": "add_table_player", "name": "OralAlice"})
            await c1.send_json_to({"action": "add_table_player", "name": "OralBob"})
            s = await _recv_until(c1, lambda m: len(m.get("players", [])) == 3)

            await c1.send_json_to({"action": "start_game"})
            s = await _recv_until(c1, lambda m: m.get("phase") == "clue")
            assert len(s.get("round_participant_list", [])) == 3

            # Mod records oral text clue for current speaker (even when not Mod's turn)
            non_mod = next(p for p in s["round_participant_list"] if p["id"] != mod_id)
            await c1.send_json_to({"action": "submit_clue", "clue": "subtle", "target_player_id": non_mod["id"]})
            s = await _recv_until(c1, lambda m: len(m.get("clues", [])) == 1)
            assert s["clues"][0]["player_id"] == non_mod["id"]
            assert s["clues"][0]["by_mod"] is True
            assert s["clues"][0]["text"] == "subtle"

            await c1.disconnect()

        async_to_sync(_run)()

    def test_untimed_default_settings_and_moderator_table_votes(self, db):
        assert DEFAULT_SETTINGS["turn_timer"] == 0
        assert DEFAULT_SETTINGS["vote_timer"] == 0
        assert DEFAULT_SETTINGS["steal_timer"] == 0
        assert DEFAULT_SETTINGS["clue_loops"] == 2
        assert DEFAULT_SETTINGS["enable_steal"] is True

        state = create_initial_state(code="IMPNTM", title="Casual Couch")
        state, gm, _ = add_player(state, "ModHost", is_admin=True)
        add_table_player(state, "TableBob")
        add_table_player(state, "TableCarol")

        update_settings(state, {"clue_loops": 3})
        start_round(state)
        assert len(state["turn_order"]) == 3 * len(state["round_participants"])
        assert state["timer_duration"] == 0
        assert state["timer_ends_at"] is None

        # Open voting manually (untimed)
        start_voting_phase(state)
        assert state["phase"] == "voting"
        assert state["timer_duration"] == 0

        imp_id = state["impostor_id"]
        non_imps = [pid for pid in state["round_participants"] if pid != imp_id]
        non_admins = [pid for pid in state["round_participants"] if pid != gm["id"]]
        other_voter = non_admins[0]
        spoof_voter = non_admins[1]

        # Non-admin cannot forge another voter's ballot via on_behalf_of
        ok, _ = cast_vote(state, other_voter, gm["id"], on_behalf_of=spoof_voter, auto_tally=False)
        assert ok is True
        assert state["votes"].get(other_voter) == gm["id"]
        assert spoof_voter not in state["votes"]
        state["votes"].clear()

        # Moderator assigns votes on behalf of table players to eject Impostor
        ok, _ = cast_vote(state, gm["id"], imp_id, on_behalf_of=non_imps[0], auto_tally=False)
        assert ok is True
        ok, _ = cast_vote(state, gm["id"], imp_id, on_behalf_of=non_imps[1], auto_tally=False)
        assert ok is True
        view = get_sanitized_player_view(state, gm["id"])
        assert len(view["votes"]) == 2
        assert len(view["eligible_voter_ids"]) == 3

        # Final vote with auto_tally=True ejects Impostor -> untimed Last-Chance Steal!
        ok, _ = cast_vote(state, gm["id"], non_imps[0], on_behalf_of=imp_id, auto_tally=True)
        assert ok is True
        assert state["phase"] == "last_chance"
        assert state["timer_duration"] == 0
        assert state["timer_ends_at"] is None

        # Non-admin non-impostor cannot submit steal guess even with by_mod=True
        non_imp_non_admin = next(pid for pid in non_admins if pid != imp_id)
        ok, _ = submit_steal_guess(state, non_imp_non_admin, state["current_pair"]["citizen_display"], by_mod=True)
        assert ok is False

        # Moderator can submit caught Impostor's oral steal guess via by_mod=True
        ok, _ = submit_steal_guess(state, gm["id"], state["current_pair"]["citizen_display"], by_mod=True)
        assert ok is True
        assert state["phase"] == "reveal"
        assert state["round_outcome"] == "impostor_steal"

    def test_websocket_mod_assigns_table_votes(self, db):
        Room.objects.create(title="WS Table Vote", code="IMPTBVT1", game_type="impostor", language="en")

        async def _run():
            c1 = WebsocketCommunicator(application, "/ws/impostor/IMPTBVT1/")
            ok, _ = await c1.connect()
            assert ok is True
            await c1.send_json_to({"action": "join", "name": "TableMod"})

            async def _recv_until(comm, predicate):
                for _ in range(20):
                    msg = await comm.receive_json_from(timeout=2)
                    if predicate(msg):
                        return msg
                raise AssertionError("Timed out waiting for expected WebSocket state")

            await _recv_until(c1, lambda m: m.get("me", {}).get("is_admin") is True)
            await c1.send_json_to({"action": "add_table_player", "name": "TableOne"})
            await c1.send_json_to({"action": "add_table_player", "name": "TableTwo"})
            await _recv_until(c1, lambda m: len(m.get("players", [])) == 3)

            await c1.send_json_to({"action": "start_game"})
            s = await _recv_until(c1, lambda m: m.get("phase") == "clue")
            assert s["timer"]["duration"] == 0

            await c1.send_json_to({"action": "start_voting"})
            s = await _recv_until(c1, lambda m: m.get("phase") == "voting")
            p0, p1 = s["eligible_voter_ids"][0], s["eligible_voter_ids"][1]

            await c1.send_json_to({"action": "cast_vote", "voter_id": p0, "target_id": p1, "auto_tally": False})
            s = await _recv_until(c1, lambda m: m.get("votes", {}).get(p0) == p1)
            assert s["phase"] == "voting"

            await c1.disconnect()

        async_to_sync(_run)()

    def test_player_qr_and_reconnect_http(self, db):
        from urllib.parse import urlparse

        Room.objects.create(title="QR Spy Table", code="IMPQR001", game_type="impostor", language="en")

        async def _setup_players():
            c1 = WebsocketCommunicator(application, "/ws/impostor/IMPQR001/")
            c2 = WebsocketCommunicator(application, "/ws/impostor/IMPQR001/")
            assert (await c1.connect())[0] is True
            assert (await c2.connect())[0] is True
            await c1.send_json_to({"action": "join", "name": "HostAlice"})
            s1 = await c1.receive_json_from()
            await c2.send_json_to({"action": "join", "name": "GuestBob"})
            s2 = await c2.receive_json_from()
            await c1.disconnect()
            await c2.disconnect()
            return s1["me"], s2["me"]

        host_me, guest_me = async_to_sync(_setup_players)()
        assert host_me["is_admin"] is True
        assert guest_me["is_admin"] is False

        client = Client()
        game_resp = client.get(reverse("gamerooms:impostor:game", kwargs={"code": "IMPQR001", "name": "HostAlice"}))
        assert game_resp.status_code == 200
        html = game_resp.content.decode()
        assert "modal-player-qr" in html
        assert "showPlayerQR" in html
        assert "mod-voter-select" in html
        assert "mod-target-select" in html
        assert "submitModVote" in html
        assert "version_counter" in html
        assert "Spoke Out Loud" not in html

        qr_url = reverse("gamerooms:impostor:player-qr", kwargs={"code": "IMPQR001", "token": guest_me["id"]})
        qr_resp = client.get(qr_url)
        assert qr_resp.status_code == 200
        payload = qr_resp.json()
        assert payload["qr"].startswith("data:image/png;base64,")
        assert payload["player_id"] == guest_me["id"]
        assert payload["player_name"] == "GuestBob"
        assert "/games/impostor/IMPQR001/reconnect/" in payload["url"]

        phone_client = Client()
        reconnect_path = urlparse(payload["url"]).path
        rec_resp = phone_client.get(reconnect_path, follow=True)
        assert rec_resp.status_code == 200
        assert rec_resp.context["player_name"] == "GuestBob"
        assert rec_resp.context["admin_token"] == ""

"""Unit tests for Lupus game rules, state machine, and views."""

import pytest
from django.urls import reverse

from gamerooms.models import Room
from lupus.game_state import (
    add_player,
    check_win_condition,
    create_initial_state,
    deal_roles,
    get_game,
    get_gm_view,
    get_sanitized_player_view,
    guess_angel_in_limbo,
    resolve_night,
    return_to_lobby,
    set_manual_player_role,
    set_player_status,
    start_game,
    submit_night_action,
)
from lupus.qr import generate_qr_data_uri
from lupus.roles import (
    ROLE_REGISTRY,
    generate_preset_deck,
    get_role_info,
)


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
def mock_redis(monkeypatch):
    r = MockRedis()
    monkeypatch.setattr("lupus.game_state.get_redis_client", lambda: r)
    return r


class TestLupusRoles:
    def test_role_registry_integrity(self):
        assert "villager" in ROLE_REGISTRY
        assert "werewolf" in ROLE_REGISTRY
        assert "detective" in ROLE_REGISTRY
        assert "doctor" in ROLE_REGISTRY
        assert "sniper" in ROLE_REGISTRY
        assert "angel" in ROLE_REGISTRY
        assert "mayor" in ROLE_REGISTRY
        assert "silencer" in ROLE_REGISTRY
        assert "cupid" in ROLE_REGISTRY

    def test_theme_translations(self):
        wolf_role = get_role_info("werewolf", theme="werewolf")
        assert wolf_role["name"] == "Werewolf"

        mafia_role = get_role_info("werewolf", theme="mafia")
        assert mafia_role["name"] == "Mafioso"

        cop_role = get_role_info("detective", theme="mafia")
        assert cop_role["name"] == "Detective / Cop"

    def test_generate_preset_deck(self):
        # 5 players simple (pure wolves vs villagers, no powers)
        deck_5_simple = generate_preset_deck(5, "simple")
        assert len(deck_5_simple) == 5
        assert deck_5_simple.count("werewolf") == 1
        assert deck_5_simple.count("villager") == 4

        # 7 players simple (2 wolves, 5 villagers)
        deck_7_simple = generate_preset_deck(7, "simple")
        assert len(deck_7_simple) == 7
        assert deck_7_simple.count("werewolf") == 2
        assert deck_7_simple.count("villager") == 5

        # 7 players standard
        deck_7_std = generate_preset_deck(7, "standard")
        assert len(deck_7_std) == 7
        assert deck_7_std.count("werewolf") == 2
        assert "detective" in deck_7_std
        assert "doctor" in deck_7_std
        assert "villager" in deck_7_std


class TestLupusEngine:
    def test_init_game_and_add_players(self):
        state = create_initial_state("TEST1", "My Room", password="secret", theme="werewolf")
        assert state["code"] == "TEST1"
        assert state["phase"] == "lobby"

        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob", is_offline=True)

        assert len(state["players"]) == 2
        assert p1["name"] == "Alice"
        assert p2["is_offline"] is True

    def test_deal_roles(self):
        state = create_initial_state("TEST2", "Role Test")
        for name in ["P1", "P2", "P3", "P4", "P5"]:
            state, _ = add_player(state, name)

        state = deal_roles(state, ["werewolf", "detective", "doctor", "villager", "villager"])
        roles = [p["role"] for p in state["players"].values()]
        assert "werewolf" in roles
        assert "detective" in roles
        assert "doctor" in roles
        assert roles.count("villager") == 2

    def test_start_game_and_return_to_lobby(self):
        state = create_initial_state("TEST_LOBBY", "Lobby Test")
        assert state["phase"] == "lobby"
        assert state["round_number"] == 0

        for name in ["P1", "P2", "P3", "P4", "P5"]:
            state, _ = add_player(state, name)

        # Start game
        state = start_game(state, ["werewolf", "detective", "doctor", "villager", "villager"])
        assert state["phase"] == "night"
        assert state["round_number"] == 1
        for p in state["players"].values():
            assert p["role"] is not None

        # Return to lobby
        state = return_to_lobby(state)
        assert state["phase"] == "lobby"
        assert state["round_number"] == 0
        assert len(state["players"]) == 5
        for p in state["players"].values():
            assert p["role"] is None
            assert p["status"] == "alive"

    def test_gm_overrides_and_kick(self):
        state = create_initial_state("TEST_OVR", "Overrides Test")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")

        # Kick Bob in lobby
        from lupus.game_state import remove_player, set_broadcast_message, set_round_number
        state = remove_player(state, p2["id"])
        assert len(state["players"]) == 1
        assert p2["id"] not in state["players"]

        # Direct kill Alice
        state = set_player_status(state, p1["id"], "dead")
        assert state["players"][p1["id"]]["status"] == "dead"

        # Direct revive Alice
        state = set_player_status(state, p1["id"], "alive")
        assert state["players"][p1["id"]]["status"] == "alive"

        # Broadcast
        state = set_broadcast_message(state, "Dinner is ready!")
        assert state["broadcast_message"] == "Dinner is ready!"

        # Round number
        state = set_round_number(state, 4)
        assert state["round_number"] == 4

    def test_detective_inspection(self):
        state = create_initial_state("TEST3", "Det Test")
        state, p_det = add_player(state, "Sherlock")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_alpha = add_player(state, "AlphaWolfie")

        set_manual_player_role(state, p_det["id"], "detective")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_alpha["id"], "alpha_wolf")

        # Inspect regular wolf
        ok, msg = submit_night_action(state, p_det["id"], "inspect", p_wolf["id"])
        assert ok is True
        assert "Evil / Enemy" in msg

        # Inspect alpha wolf (should appear innocent!)
        ok2, msg2 = submit_night_action(state, p_det["id"], "inspect", p_alpha["id"])
        assert ok2 is True
        assert "Good / Innocent" in msg2

    def test_staggering_doctor_protection(self):
        state = create_initial_state("TEST4", "Doc Test", settings={"staggering_doctor": True})
        state, p_doc = add_player(state, "Doctor")
        state, p_target = add_player(state, "Patient")

        set_manual_player_role(state, p_doc["id"], "doctor")
        set_manual_player_role(state, p_target["id"], "villager")

        # Night 1: guard patient
        ok, _ = submit_night_action(state, p_doc["id"], "protect", p_target["id"])
        assert ok is True

        state = resolve_night(state)
        # Doctor's last_guarded_id should be set to patient
        assert state["players"][p_doc["id"]]["last_guarded_id"] == p_target["id"]

        # Night 2: attempting to guard patient again should fail due to staggering rule
        ok2, err2 = submit_night_action(state, p_doc["id"], "protect", p_target["id"])
        assert ok2 is False
        assert "Staggering Doctor rule" in err2

    def test_sniper_danger_bullet_mechanics(self):
        opts = {"sniper_bullet_type": "danger", "limbo_enabled": False}
        state = create_initial_state("TEST5", "Sniper Test", settings=opts)
        state, p_sniper = add_player(state, "Sniper")
        state, p_innocent = add_player(state, "Innocent")
        state, p_wolf = add_player(state, "Wolf")

        set_manual_player_role(state, p_sniper["id"], "sniper")
        set_manual_player_role(state, p_innocent["id"], "villager")
        set_manual_player_role(state, p_wolf["id"], "werewolf")

        # Sniper shoots innocent with danger bullet
        submit_night_action(state, p_sniper["id"], "shoot", p_innocent["id"], extra={"bullet_type": "danger"})
        state = resolve_night(state)

        # Both the target and the sniper die!
        assert state["players"][p_innocent["id"]]["status"] == "dead"
        assert state["players"][p_sniper["id"]]["status"] == "dead"

    def test_limbo_and_angel_revival(self):
        state = create_initial_state("TEST6", "Limbo Test", settings={"limbo_enabled": True})
        state, p_angel = add_player(state, "Angelina")
        state, p_victim = add_player(state, "Victim")
        state, p_wolf = add_player(state, "Wolf")

        set_manual_player_role(state, p_angel["id"], "angel")
        set_manual_player_role(state, p_victim["id"], "villager")
        set_manual_player_role(state, p_wolf["id"], "werewolf")

        # Wolves attack victim
        submit_night_action(state, p_wolf["id"], "kill", p_victim["id"])
        state = resolve_night(state)

        # Victim enters Limbo instead of dying
        assert state["players"][p_victim["id"]]["status"] == "limbo"
        assert state["players"][p_victim["id"]]["used_limbo"] is True

        # Correct Angel guess revives them
        success, msg = guess_angel_in_limbo(state, p_victim["id"], p_angel["id"])
        assert success is True
        assert state["players"][p_victim["id"]]["status"] == "alive"

    def test_cupid_lovers_broken_heart(self):
        state = create_initial_state("TEST7", "Cupid Test")
        state, p1 = add_player(state, "Romeo")
        state, p2 = add_player(state, "Juliet")

        state["players"][p1["id"]]["lover_id"] = p2["id"]
        state["players"][p2["id"]]["lover_id"] = p1["id"]

        # If Romeo dies, Juliet dies too!
        set_player_status(state, p1["id"], "dead")
        assert state["players"][p1["id"]]["status"] == "dead"
        assert state["players"][p2["id"]]["status"] == "dead"

    def test_sanitized_player_view_privacy(self):
        state = create_initial_state("TEST8", "Privacy Test")
        state, p_villager = add_player(state, "VillagerJoe")
        state, p_wolf = add_player(state, "SecretWolf")

        set_manual_player_role(state, p_villager["id"], "villager")
        set_manual_player_role(state, p_wolf["id"], "werewolf")

        # Villager perspective
        v_view = get_sanitized_player_view(state, p_villager["id"])
        wolf_in_view = next(p for p in v_view["players"] if p["id"] == p_wolf["id"])

        # The wolf's role should be None to the villager!
        assert wolf_in_view["role"] is None

        # GM perspective sees everything
        gm_view = get_gm_view(state)
        wolf_in_gm = next(p for p in gm_view["players"] if p["id"] == p_wolf["id"])
        assert wolf_in_gm["role"]["id"] == "werewolf"

    def test_bodyguard_sacrifice(self):
        state = create_initial_state("BGTEST", "Bodyguard Test")
        state, p_bg = add_player(state, "Hero")
        state, p_target = add_player(state, "Innocent")
        state, p_wolf = add_player(state, "BigBadWolf")

        set_manual_player_role(state, p_bg["id"], "bodyguard")
        set_manual_player_role(state, p_target["id"], "villager")
        set_manual_player_role(state, p_wolf["id"], "werewolf")

        # Bodyguard protects target; wolf attacks target
        submit_night_action(state, p_bg["id"], "guard_bodyguard", p_target["id"])
        submit_night_action(state, p_wolf["id"], "kill", p_target["id"])

        state = resolve_night(state)

        # Target should be saved (alive), but Bodyguard sacrifices themselves (dead)
        assert state["players"][p_target["id"]]["status"] == "alive"
        assert state["players"][p_bg["id"]]["status"] == "dead"
        assert any("Bodyguard" in r and "sacrificed" in r for r in state["night_report"])

    def test_framer_inspection(self):
        state = create_initial_state("FRAMETEST", "Framer Test")
        state, p_framer = add_player(state, "FramerFrank")
        state, p_det = add_player(state, "Sherlock")
        state, p_town = add_player(state, "CleanVillager")

        set_manual_player_role(state, p_framer["id"], "framer")
        set_manual_player_role(state, p_det["id"], "detective")
        set_manual_player_role(state, p_town["id"], "villager")

        # Framer frames the clean villager
        submit_night_action(state, p_framer["id"], "frame", p_town["id"])
        # Detective investigates framed villager
        submit_night_action(state, p_det["id"], "inspect", p_town["id"])

        query = state["night_actions"]["detective_query"]
        assert query["result"] == "Evil / Enemy"

    def test_serial_killer_night_action_and_win(self):
        state = create_initial_state("SKTEST", "SK Test")
        state, p_sk = add_player(state, "Dexter")
        state, p_victim = add_player(state, "Victim")

        set_manual_player_role(state, p_sk["id"], "serial_killer")
        set_manual_player_role(state, p_victim["id"], "villager")

        # SK eliminates victim at night
        submit_night_action(state, p_sk["id"], "solo_kill", p_victim["id"])
        state = resolve_night(state)

        assert state["players"][p_victim["id"]]["status"] == "dead"
        assert state["players"][p_sk["id"]]["status"] == "alive"
        # Win condition: Serial Killer is last survivor standing
        winner = check_win_condition(state)
        assert winner == "serial_killer"
        assert state["phase"] == "gameover"


class TestLupusQR:
    def test_generate_qr_data_uri(self):
        uri = generate_qr_data_uri("https://marco-silva.com/games/lupus/ROOM123/join/?pwd=test")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100


@pytest.mark.django_db
class TestLupusViews:
    def test_create_room_get(self, client):
        res = client.get(reverse("gamerooms:lupus:create"))
        assert res.status_code == 200
        assert "Create Lupus / Werewolf Room" in res.content.decode()

    def test_create_room_post(self, client):
        res = client.post(
            reverse("gamerooms:lupus:create"),
            {
                "title": "Party Game",
                "password": "fun",
                "theme": "werewolf",
                "discussion_timer": 180,
                "defense_timer": 30,
                "staggering_doctor": "1",
                "limbo_enabled": "1",
            },
        )
        assert res.status_code == 302
        room = Room.objects.filter(game_type="lupus").first()
        assert room is not None
        assert room.title == "Party Game"

    def test_gm_dashboard_unauthorized(self, client):
        room = Room.objects.create(code="AUTHROOM", title="Auth Room", game_type="lupus")
        create_initial_state(room.code, room.title)
        res = client.get(reverse("gamerooms:lupus:gm", kwargs={"code": "AUTHROOM"}))
        assert res.status_code == 403

    def test_player_join_and_reconnect(self, client):
        room = Room.objects.create(code="JOINROOM", title="Join Room", game_type="lupus")
        create_initial_state(room.code, room.title)

        # Join with name
        res = client.post(reverse("gamerooms:lupus:join", kwargs={"code": "JOINROOM"}), {"name": "Carlos"})
        assert res.status_code == 302

        updated_state = get_game("JOINROOM")
        player = next(p for p in updated_state["players"].values() if p["name"] == "Carlos")
        assert player is not None

        # Reconnect via secret token
        res_reconnect = client.get(
            reverse("gamerooms:lupus:reconnect", kwargs={"code": "JOINROOM", "token": player["token"]})
        )
        assert res_reconnect.status_code == 302
        assert "play" in res_reconnect.url

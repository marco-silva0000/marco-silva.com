"""Unit tests for Lupus game rules, state machine, and views."""

import pytest
from django.urls import reverse

from gamerooms.models import Room
from lupus.game_state import (
    DEMO_PLAYER_NAMES,
    add_player,
    adjust_timer,
    approve_ghost_message,
    approve_news_bulletin,
    assign_midgame_role,
    auto_assign_roles_from_names,
    cast_final_vote,
    check_win_condition,
    clear_gm_night_action,
    create_initial_state,
    deal_roles,
    dismiss_pending_gameover,
    get_game,
    get_gm_view,
    get_night_stages,
    get_nomination_threshold,
    get_ordered_players,
    get_sanitized_player_view,
    get_voting_view,
    guess_angel_in_limbo,
    move_player,
    proceed_to_defense,
    proceed_to_final_vote,
    record_gm_final_vote_tally,
    record_gm_night_action,
    remove_player,
    rename_player,
    reorder_players,
    resolve_night,
    return_to_lobby,
    return_to_nominations,
    reveal_detective_to_player,
    set_deck,
    set_manual_player_role,
    set_night_stage_index,
    set_player_status,
    set_preassigned_role,
    setup_demo_room,
    should_autofill_demo,
    start_game,
    start_timer,
    start_voting_session,
    submit_ghost_message,
    submit_news_bulletin,
    submit_night_action,
    tally_and_resolve_vote,
    toggle_nomination_vote,
    toggle_official_nomination,
    toggle_player_silence,
    trigger_game_over,
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
        from lupus.game_state import set_broadcast_message, set_round_number

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

    def test_adjust_timer(self):
        state = create_initial_state("TIMERTEST", "Timer Test")
        state["timer"]["duration"] = 300
        state["timer"]["remaining"] = 300
        state["timer"]["paused"] = True

        # Add 60s while paused
        adjust_timer(state, 60)
        assert state["timer"]["remaining"] == 360
        assert state["timer"]["duration"] == 360

        # Subtract 120s while paused
        adjust_timer(state, -120)
        assert state["timer"]["remaining"] == 240

        # Running timer test
        start_timer(state, 180, "Discussion")
        assert state["timer"]["paused"] is False
        old_ends = state["timer"]["ends_at"]
        adjust_timer(state, 60)
        assert state["timer"]["ends_at"] == pytest.approx(old_ends + 60, abs=1)

        # Subtracting more than remaining clamps to 0
        adjust_timer(state, -500)
        assert state["timer"]["remaining"] == 0

    def test_toggle_player_silence(self):
        state = create_initial_state("SILENCETEST", "Silence Test")
        state, p = add_player(state, "Noisy")
        assert p["is_silenced"] is False

        ok, msg = toggle_player_silence(state, p["id"])
        assert ok is True
        assert state["players"][p["id"]]["is_silenced"] is True

        ok, msg = toggle_player_silence(state, p["id"])
        assert ok is True
        assert state["players"][p["id"]]["is_silenced"] is False

        # Nonexistent player returns False
        ok, msg = toggle_player_silence(state, "nonexistent")
        assert ok is False

    def test_return_to_nominations(self):
        state = create_initial_state("RETNOMTEST", "Return Nom Test")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")
        start_voting_session(state, "two_stage_50pct")

        # Manually nominate Bob
        toggle_official_nomination(state, p2["id"])
        assert p2["id"] in state["voting"]["nominated_player_ids"]

        # Move to defense
        proceed_to_defense(state, p2["id"])
        assert state["voting"]["stage"] == "defense"
        assert state["voting"]["defense_player_id"] == p2["id"]

        # Return to nominations: stage should become nomination, defense cleared, but Bob stays nominated!
        return_to_nominations(state)
        assert state["voting"]["stage"] == "nomination"
        assert state["voting"]["defense_player_id"] is None
        assert p2["id"] in state["voting"]["nominated_player_ids"]
        assert state["timer"]["label"] == "Nominations"

    def test_rename_player(self):
        state = create_initial_state("RENAMETEST", "Rename Test")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")

        # 1. Successful rename
        ok, msg = rename_player(state, p1["id"], "Alicia")
        assert ok is True
        assert state["players"][p1["id"]]["name"] == "Alicia"
        assert any("Alicia" in event["message"] for event in state["events_log"])

        # 2. Duplicate name rejected (case-insensitive)
        ok, msg = rename_player(state, p1["id"], "bob")
        assert ok is False
        assert "already taken" in msg.lower()
        assert state["players"][p1["id"]]["name"] == "Alicia"

        # 3. Empty or whitespace-only name rejected
        ok, msg = rename_player(state, p1["id"], "   ")
        assert ok is False
        assert "cannot be empty" in msg.lower()

        # 4. Nonexistent player returns False
        ok, msg = rename_player(state, "nonexistent_pid", "Ghost")
        assert ok is False
        assert "not found" in msg.lower()

        # 5. Long name truncated to 24 chars cleanly
        ok, msg = rename_player(state, p1["id"], "A" * 50)
        assert ok is True
        assert len(state["players"][p1["id"]]["name"]) == 24

    def test_version_counter_and_commit_hash(self):
        from website.version import get_commit_count, get_git_commit_hash, get_version_info

        info = get_version_info()
        assert "version" in info
        assert "commit" in info
        assert "display" in info
        assert info["version"].startswith("v")
        assert len(info["commit"]) >= 7
        assert f"{info['version']} ({info['commit']})" == info["display"]

        # Check raw functions
        hash_val = get_git_commit_hash()
        assert len(hash_val) >= 7
        count_val = get_commit_count()
        assert count_val > 0

    def test_never_cache_headers(self):
        from django.http import HttpResponse
        from django.views.decorators.cache import never_cache

        @never_cache
        def dummy_view(request):
            return HttpResponse("ok")

        from django.test import RequestFactory

        res = dummy_view(RequestFactory().get("/"))
        cache_hdr = res.headers.get("Cache-Control", "")
        assert "no-cache" in cache_hdr
        assert "no-store" in cache_hdr

    def test_room_force_refresh_consumer(self):
        import asyncio

        from lupus.consumers import LupusConsumer

        consumer = LupusConsumer()
        sent = []

        async def fake_send_json(data):
            sent.append(data)

        consumer.send_json = fake_send_json
        consumer.is_gm = False
        asyncio.run(
            consumer.room_force_refresh({"type": "room.force.refresh", "target": "all", "message": "Host refreshed."})
        )
        assert len(sent) == 1
        assert sent[0]["type"] == "force_refresh"
        assert sent[0]["message"] == "Host refreshed."

        # Target players only skips GM
        consumer.is_gm = True
        sent.clear()
        asyncio.run(
            consumer.room_force_refresh(
                {"type": "room.force.refresh", "target": "players", "message": "Host refreshed."}
            )
        )
        assert len(sent) == 0

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

        # Danger bullet backfires: innocent target survives unharmed, shooter dies of guilt!
        assert state["players"][p_innocent["id"]]["status"] == "alive"
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

    def test_citizen_lovers_role_mechanics(self):
        # 1. Role definition verification
        from lupus.roles import FACTION_TOWN, ROLE_REGISTRY

        assert "lover" in ROLE_REGISTRY
        lover_def = ROLE_REGISTRY["lover"]
        assert lover_def["faction"] == FACTION_TOWN
        assert lover_def["night_action"] is None

        # 2. Dealing roles with 2 lovers binds them automatically
        state = create_initial_state("LOVETEST", "Lovers Test")
        state, p1 = add_player(state, "Romeo")
        state, p2 = add_player(state, "Juliet")
        state, p3 = add_player(state, "Wolfie")
        state, p4 = add_player(state, "Sherlock")

        # Deal with exactly 2 lovers
        deck = ["lover", "lover", "werewolf", "detective"]
        deal_roles(state, deck)

        # Both players who received lover must be bound
        lovers = [p for p in state["players"].values() if p["role"] == "lover"]
        assert len(lovers) == 2
        l1, l2 = lovers[0], lovers[1]
        assert l1["faction"] == FACTION_TOWN
        assert l2["faction"] == FACTION_TOWN
        assert l1["lover_id"] == l2["id"]
        assert l2["lover_id"] == l1["id"]

        # 3. Private perspective: each lover knows their partner from turn 1
        pv1 = get_sanitized_player_view(state, l1["id"])
        assert pv1["me"]["lover_name"] == l2["name"]
        assert pv1["me"]["role"]["id"] == "lover"
        # Table shows lover indicator only for the partner
        l2_in_view = next(p for p in pv1["players"] if p["id"] == l2["id"])
        assert l2_in_view["is_lover"] is True

        # Non-lover perspective: wolf does NOT see lover bond
        wolf_p = next(p for p in state["players"].values() if p["role"] == "werewolf")
        wolf_pv = get_sanitized_player_view(state, wolf_p["id"])
        assert wolf_pv["me"]["lover_name"] is None
        assert not any(p["is_lover"] for p in wolf_pv["players"])

        # 4. Night 1 stage director has Lovers Awaken step
        stages = get_night_stages(state)
        stage_ids = [s["id"] for s in stages]
        assert "lovers_meet" in stage_ids

        # 5. Wolves 2-for-1 kill: wolves attack one lover at night
        submit_night_action(state, wolf_p["id"], "kill", l1["id"])
        state = resolve_night(state)
        assert state["players"][l1["id"]]["status"] == "dead"
        assert state["players"][l2["id"]]["status"] == "dead"
        # Night report contains both casualties
        assert f"🪦 {l1['name']} was slain in the night." in state["night_report"]
        assert f"🪦 {l2['name']} was slain in the night." in state["night_report"]

    def test_solitary_lover_conversion_on_odd_deck(self):
        state = create_initial_state("ODDTEST", "Odd Lovers Test")
        state, p1 = add_player(state, "Lover1")
        state, p2 = add_player(state, "Wolfie")
        state, p3 = add_player(state, "Doc")

        # 1 lover in deck (odd count)
        deck = ["lover", "werewolf", "doctor"]
        deal_roles(state, deck)

        # Unpaired lover reverts to plain citizen
        lovers = [p for p in state["players"].values() if p["role"] == "lover"]
        assert len(lovers) == 0
        p1_state = state["players"][p1["id"]]
        assert p1_state["role"] in ("villager", "werewolf", "doctor")
        assert p1_state["lover_id"] is None

    def test_sanitized_player_view_privacy(self):
        state = create_initial_state("TEST8", "Privacy Test")
        state, p_villager = add_player(state, "VillagerJoe")
        state, p_bob = add_player(state, "VillagerBob")
        state, p_charlie = add_player(state, "VillagerCharlie")
        state, p_wolf = add_player(state, "SecretWolf")

        set_manual_player_role(state, p_villager["id"], "villager")
        set_manual_player_role(state, p_bob["id"], "villager")
        set_manual_player_role(state, p_charlie["id"], "villager")
        set_manual_player_role(state, p_wolf["id"], "werewolf")

        # Villager perspective
        v_view = get_sanitized_player_view(state, p_villager["id"])
        wolf_in_view = next(p for p in v_view["players"] if p["id"] == p_wolf["id"])
        me_in_view = next(p for p in v_view["players"] if p["id"] == p_villager["id"])

        # The wolf's role should be None to the villager!
        assert wolf_in_view["role"] is None
        # On the public table roster, own role is None to prevent table leaks,
        # but present on v_view['me']['role'] for the private card!
        assert me_in_view["role"] is None
        assert v_view["me"]["role"]["id"] == "villager"

        # Dead players do NOT reveal their roles to the town while game is active!
        set_player_status(state, p_bob["id"], "dead")
        assert state["phase"] != "gameover"
        v_view_after_death = get_sanitized_player_view(state, p_villager["id"])
        dead_bob_in_view = next(p for p in v_view_after_death["players"] if p["id"] == p_bob["id"])
        assert dead_bob_in_view["role"] is None

        # Even when dead, roles are not revealed during active play
        assert dead_bob_in_view["role"] is None
        assert wolf_in_view["role"] is None

        # When game is over (phase == 'gameover'), all roles are revealed to players
        state["phase"] = "gameover"
        v_view_gameover = get_sanitized_player_view(state, p_villager["id"])
        gameover_bob = next(p for p in v_view_gameover["players"] if p["id"] == p_bob["id"])
        gameover_wolf = next(p for p in v_view_gameover["players"] if p["id"] == p_wolf["id"])
        assert gameover_bob["role"]["id"] == "villager"
        assert gameover_wolf["role"]["id"] == "werewolf"

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
        # Casualties announced generically without revealing role or sacrifice
        assert any("Hero" in r and "slain" in r for r in state["night_report"])
        assert not any("Bodyguard" in r for r in state["night_report"])
        assert not any("sacrificed" in r for r in state["night_report"])

    def test_night_actions_concealed_in_night_report(self):
        """Verify that sniper shots, doctor saves, etc. are unknown in night_report, while Mayor veto is revealed."""
        opts = {"limbo_enabled": False}
        state = create_initial_state("SECRET1", "Secret Actions Test", settings=opts)
        state, p_sniper = add_player(state, "SniperSam")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_doc = add_player(state, "DrHouse")
        state, p_innocent = add_player(state, "InnocentIan")
        state, p_mayor = add_player(state, "MayorMike")
        state, p_past_lynch = add_player(state, "WronglyLynched")

        set_manual_player_role(state, p_sniper["id"], "sniper")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_doc["id"], "doctor")
        set_manual_player_role(state, p_innocent["id"], "villager")
        set_manual_player_role(state, p_mayor["id"], "mayor")

        # Set up past lynched player
        p_past_lynch["status"] = "dead"
        state["last_lynched_id"] = p_past_lynch["id"]

        # Sniper shoots wolf (hit mark)
        submit_night_action(state, p_sniper["id"], "shoot", p_wolf["id"], extra={"bullet_type": "danger"})
        # Wolf attacks innocent; Doctor protects innocent (save)
        submit_night_action(state, p_wolf["id"], "kill", p_innocent["id"])
        submit_night_action(state, p_doc["id"], "protect", p_innocent["id"])
        # Mayor uses veto
        submit_night_action(state, p_mayor["id"], "veto")

        state = resolve_night(state)

        # 1. Wolf is dead from sniper
        assert state["players"][p_wolf["id"]]["status"] == "dead"
        # 2. Innocent is saved by doctor
        assert state["players"][p_innocent["id"]]["status"] == "alive"
        # 3. Past lynched player pardoned by Mayor
        assert state["players"][p_past_lynch["id"]]["status"] == "alive"

        # 4. Check night_report contents:
        report_text = " ".join(state["night_report"])
        # Wolf death is reported neutrally:
        assert any("Wolfie" in r and "slain" in r for r in state["night_report"])
        # No mention of sniper or hit mark or evil!
        assert "sniper" not in report_text.lower()
        assert "mark" not in report_text.lower()
        assert "evil" not in report_text.lower()
        # No mention of doctor or protection shielding!
        assert "doctor" not in report_text.lower()
        assert "shielded" not in report_text.lower()
        assert "protection" not in report_text.lower()
        # Mayor veto IS explicitly announced as requested
        assert any("Mayor exercised official veto" in r and "WronglyLynched" in r for r in state["night_report"])

    def test_dead_roles_still_called_in_night_stages(self):
        """Dead roles must still appear in night stages so the GM calls them, keeping casualties secret."""
        state = create_initial_state("DEADSTAGES", "Dead Stages Test")
        state, p_doc = add_player(state, "DrDead")
        state, p_snip = add_player(state, "SniperDead")
        state, p_may = add_player(state, "MayorDead")
        state, p_wolf = add_player(state, "LivingWolf")
        state, p_town = add_player(state, "LivingTown")

        set_manual_player_role(state, p_doc["id"], "doctor")
        set_manual_player_role(state, p_snip["id"], "sniper")
        set_manual_player_role(state, p_may["id"], "mayor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_town["id"], "villager")

        # Kill the doctor, sniper, and mayor
        p_doc["status"] = "dead"
        p_snip["status"] = "dead"
        p_may["status"] = "dead"

        stages = get_night_stages(state)
        stage_ids = [s["id"] for s in stages]

        # Verify all 3 dead roles STILL appear in the night stages list
        assert "doctor" in stage_ids
        assert "sniper" in stage_ids
        assert "mayor" in stage_ids

        # Verify stage flags: is_alive is False, but is_complete is True (does not block GM)
        doc_stage = next(s for s in stages if s["id"] == "doctor")
        snip_stage = next(s for s in stages if s["id"] == "sniper")
        may_stage = next(s for s in stages if s["id"] == "mayor")

        assert doc_stage["is_alive"] is False
        assert doc_stage["is_complete"] is True

        assert snip_stage["is_alive"] is False
        assert snip_stage["is_complete"] is True

        assert may_stage["is_alive"] is False
        assert may_stage["is_complete"] is True

    def test_gm_mayor_night_stage_and_veto(self):
        """Mayor stage must prompt the GM and successfully record and execute a pardon veto."""
        state = create_initial_state("MAYORSTAGE", "Mayor Stage Test")
        state, p_mayor = add_player(state, "MayorLiving")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_victim = add_player(state, "LynchedPlayer")

        set_manual_player_role(state, p_mayor["id"], "mayor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_victim["id"], "villager")

        p_victim["status"] = "dead"
        state["last_lynched_id"] = p_victim["id"]

        stages = get_night_stages(state)
        mayor_stage = next((s for s in stages if s["id"] == "mayor"), None)
        assert mayor_stage is not None
        assert mayor_stage["is_alive"] is True
        assert mayor_stage["has_veto"] is True
        assert mayor_stage["last_lynched_id"] == p_victim["id"]
        assert mayor_stage["last_lynched_name"] == "LynchedPlayer"

        # GM toggles Mayor veto
        ok, msg = record_gm_night_action(state, "mayor", extra={"veto": True})
        assert ok is True
        assert state["night_actions"]["mayor_veto"] is True

        state = resolve_night(state)

        # Victim should be returned to alive, and veto marked as used
        assert state["players"][p_victim["id"]]["status"] == "alive"
        assert state["mayor_used_veto"] is True
        assert any("Mayor exercised official veto" in r and "LynchedPlayer" in r for r in state["night_report"])

        # Subsequent night: Mayor stage should indicate veto already used
        next_stages = get_night_stages(state)
        next_mayor = next(s for s in next_stages if s["id"] == "mayor")
        assert next_mayor["has_veto"] is False

    def test_dead_doctor_cannot_protect(self):
        """A dead doctor cannot save a player even if a protect action was submitted."""
        state = create_initial_state("DEADDOCTOR", "Dead Doctor Test")
        state, p_doc = add_player(state, "DrGhost")
        state, p_wolf = add_player(state, "Wolf")
        state, p_town = add_player(state, "TargetTown")

        set_manual_player_role(state, p_doc["id"], "doctor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_town["id"], "villager")

        p_doc["status"] = "dead"

        # GM or leftover action tries to protect TargetTown
        record_gm_night_action(state, "doctor", target_id=p_town["id"])
        record_gm_night_action(state, "wolves", target_id=p_town["id"])

        state = resolve_night(state)
        # TargetTown must die because Doctor is dead
        assert state["players"][p_town["id"]]["status"] == "dead"

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
        assert state.get("pending_gameover", {}).get("winner") == "serial_killer"
        assert state["phase"] != "gameover"

        # Host triggers Game Over
        trigger_game_over(state)
        assert state["phase"] == "gameover"
        assert state["winner"] == "serial_killer"

    def test_host_controlled_gameover_flow(self):
        state = create_initial_state("HCTEST", "Host Control Test")
        state, p_wolf = add_player(state, "Wolf")
        state, p_v1 = add_player(state, "Villager 1")
        state, p_v2 = add_player(state, "Villager 2")

        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_v1["id"], "villager")
        set_manual_player_role(state, p_v2["id"], "villager")

        state["phase"] = "day_discussion"

        # Eliminate the only wolf
        set_player_status(state, p_wolf["id"], "dead")

        # Win condition is met (all evil vanquished), but phase must NOT be gameover automatically!
        assert state["phase"] == "day_discussion"
        assert state["pending_gameover"] is not None
        assert state["pending_gameover"]["winner"] == "town"
        assert state["winner"] is None

        # GM view contains pending_gameover
        gm_view = get_gm_view(state)
        assert gm_view["pending_gameover"]["winner"] == "town"

        # Player view conceals roles while active
        pv_before = get_sanitized_player_view(state, p_v1["id"])
        assert pv_before["players"][0]["role"] is None
        assert pv_before["winner"] is None

        # Test GM dismissing warning
        dismiss_pending_gameover(state)
        assert state["pending_gameover"] is None
        assert state["pending_gameover_dismissed"] is True

        # Now GM explicitly triggers Game Over
        trigger_game_over(state, winner="town")
        assert state["phase"] == "gameover"
        assert state["winner"] == "town"
        assert state["pending_gameover"] is None

        # Player view now reveals all roles
        pv_after = get_sanitized_player_view(state, p_v1["id"])
        assert pv_after["winner"] == "town"
        wolf_in_view = next(p for p in pv_after["players"] if p["id"] == p_wolf["id"])
        v2_in_view = next(p for p in pv_after["players"] if p["id"] == p_v2["id"])
        assert wolf_in_view["role"]["id"] == "werewolf"
        assert v2_in_view["role"]["id"] == "villager"

    def test_night_stage_system_flow(self):
        state = create_initial_state("STAGETEST", "Stage System Test")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_silencer = add_player(state, "MuteMike")
        state, p_det = add_player(state, "Sherlock")
        state, p_doc = add_player(state, "DoctorDan")
        state, p_town = add_player(state, "CitizenChris")

        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_silencer["id"], "silencer")
        set_manual_player_role(state, p_det["id"], "detective")
        set_manual_player_role(state, p_doc["id"], "doctor")
        set_manual_player_role(state, p_town["id"], "villager")

        state["phase"] = "night"
        state["round_number"] = 1

        # 1. Test get_night_stages: should include wolves, silencer, detective, doctor, review
        stages = get_night_stages(state)
        stage_ids = [s["id"] for s in stages]
        assert stage_ids == ["wolves", "silencer", "detective", "doctor", "review"]

        # 2. Test GM recording wolf target
        ok, msg = record_gm_night_action(state, "wolves", p_town["id"])
        assert ok is True
        assert state["night_actions"]["wolf_target"] == p_town["id"]

        # 3. Test GM recording silencer target
        ok, msg = record_gm_night_action(state, "silencer", p_doc["id"])
        assert ok is True
        assert state["night_actions"]["silencer_target"] == p_doc["id"]

        # 4. Test GM recording detective target (inspecting Wolfie -> Evil)
        ok, msg = record_gm_night_action(state, "detective", p_wolf["id"])
        assert ok is True
        assert "Evil" in msg
        query = state["night_actions"]["detective_query"]
        assert query["result"] == "Evil / Enemy"
        assert query["is_evil"] is True

        # 5. Test reveal_detective_to_player: only Detective sees the revealed inspect
        reveal_detective_to_player(state)
        det_view = get_sanitized_player_view(state, p_det["id"])
        assert det_view["revealed_inspect"] is not None
        assert det_view["revealed_inspect"]["result"] == "Evil / Enemy"

        town_view = get_sanitized_player_view(state, p_town["id"])
        assert town_view["revealed_inspect"] is None  # Civilians cannot see!

        wolf_view = get_sanitized_player_view(state, p_wolf["id"])
        assert wolf_view["revealed_inspect"] is None  # Wolves cannot see!

        # 6. Test clear action
        clear_gm_night_action(state, "silencer")
        assert "silencer_target" not in state["night_actions"]

        # 7. Test stage navigation
        set_night_stage_index(state, 2)
        assert state["night_stage_index"] == 2

    def test_physical_seating_order_and_reorder(self):
        state = create_initial_state("SEATTEST", "Seating Test")
        state, p_alice = add_player(state, "Alice")
        state, p_bob = add_player(state, "Bob")
        state, p_charlie = add_player(state, "Charlie")

        # Initial order matches join order
        ordered = get_ordered_players(state)
        assert [p["name"] for p in ordered] == ["Alice", "Bob", "Charlie"]

        # GM view has seat numbers
        gm_view = get_gm_view(state)
        assert gm_view["players"][0]["seat_number"] == 1
        assert gm_view["players"][0]["name"] == "Alice"
        assert gm_view["players"][1]["seat_number"] == 2
        assert gm_view["players"][2]["seat_number"] == 3

        # Move Charlie up (swap with Bob)
        moved = move_player(state, p_charlie["id"], "up")
        assert moved is True
        ordered_after = get_ordered_players(state)
        assert [p["name"] for p in ordered_after] == ["Alice", "Charlie", "Bob"]

        # Full reorder (e.g. reverse circle)
        reordered = reorder_players(state, [p_bob["id"], p_charlie["id"], p_alice["id"]])
        assert reordered is True
        gm_view_updated = get_gm_view(state)
        assert [p["name"] for p in gm_view_updated["players"]] == ["Bob", "Charlie", "Alice"]
        assert gm_view_updated["players"][0]["seat_number"] == 1

        # Sanitized player view also reflects physical seating order
        p_view = get_sanitized_player_view(state, p_alice["id"])
        assert [p["name"] for p in p_view["players"]] == ["Bob", "Charlie", "Alice"]

    def test_vigilante_sniper_bad_factions_and_safe_silver_bullets(self):
        """Vigilante kills bad factions (Wolves, SK, Saboteur, Disgruntled Ghost).
        Shooting innocents/Jester with danger bullet backfires. Silver bullets are safe.
        Holding fire for 2 rounds awards a silver bullet.
        """
        opts = {"sniper_bullet_type": "danger", "limbo_enabled": False}
        state = create_initial_state("VIGTEST", "Vigilante Test", settings=opts)
        state, p_vig = add_player(state, "Vigilante")
        state, p_wolf = add_player(state, "Wolf")
        state, p_sk = add_player(state, "SerialKiller")
        state, p_sab = add_player(state, "Saboteur")
        state, p_dg = add_player(state, "DisgruntledGhost")
        state, p_jester = add_player(state, "Jester")
        state, p_cit = add_player(state, "Citizen")

        set_manual_player_role(state, p_vig["id"], "sniper")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_sk["id"], "serial_killer")
        set_manual_player_role(state, p_sab["id"], "saboteur_wolf")
        set_manual_player_role(state, p_dg["id"], "disgruntled_ghost")
        set_manual_player_role(state, p_jester["id"], "jester")
        set_manual_player_role(state, p_cit["id"], "villager")

        # 1. Vigilante shoots Serial Killer (evil neutral threat): SK dies, Vigilante survives
        submit_night_action(state, p_vig["id"], "shoot", p_sk["id"], extra={"bullet_type": "danger"})
        state = resolve_night(state)
        assert state["players"][p_sk["id"]]["status"] == "dead"
        assert state["players"][p_vig["id"]]["status"] == "alive"

        # 2. Vigilante shoots Jester with danger bullet: Jester survives, gun backfires, Vigilante dies!
        state["phase"] = "night"
        submit_night_action(state, p_vig["id"], "shoot", p_jester["id"], extra={"bullet_type": "danger"})
        state = resolve_night(state)
        assert state["players"][p_jester["id"]]["status"] == "alive"
        assert state["players"][p_vig["id"]]["status"] == "dead"

        # Revive Vigilante for silver bullet test
        state["players"][p_vig["id"]]["status"] = "alive"
        state["players"][p_vig["id"]]["sniper_silver_bullets"] = 1

        # 3. Vigilante shoots Citizen with safe silver bullet: Neither dies!
        state["phase"] = "night"
        submit_night_action(state, p_vig["id"], "shoot", p_cit["id"], extra={"bullet_type": "silver"})
        state = resolve_night(state)
        assert state["players"][p_cit["id"]]["status"] == "alive"
        assert state["players"][p_vig["id"]]["status"] == "alive"

        # 4. Holding fire for 2 consecutive rounds earns +1 silver bullet
        vig = state["players"][p_vig["id"]]
        vig["sniper_nights_held"] = 0
        vig["sniper_silver_bullets"] = 0
        # Round 1 hold
        state["phase"] = "night"
        state = resolve_night(state)
        assert state["players"][p_vig["id"]]["sniper_nights_held"] == 1
        assert state["players"][p_vig["id"]]["sniper_silver_bullets"] == 0
        # Round 2 hold -> awards silver bullet!
        state["phase"] = "night"
        state = resolve_night(state)
        assert state["players"][p_vig["id"]]["sniper_nights_held"] == 0
        assert state["players"][p_vig["id"]]["sniper_silver_bullets"] == 1

    def test_bodyguard_interceptions_wolf_sk_and_sniper(self):
        """Bodyguard intercepts any attack (Wolf, SK, Sniper).
        If guarding evil from Vigilante: Bodyguard dies, evil lives.
        If guarding citizen from Vigilante danger bullet: gun backfires, citizen and BG survive!
        """
        opts = {"limbo_enabled": False}
        state = create_initial_state("BGTEST", "Bodyguard Test", settings=opts)
        state, p_bg = add_player(state, "Bodyguard")
        state, p_vig = add_player(state, "Vigilante")
        state, p_wolf = add_player(state, "Wolf")
        state, p_cit = add_player(state, "Citizen")

        set_manual_player_role(state, p_bg["id"], "bodyguard")
        set_manual_player_role(state, p_vig["id"], "sniper")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_cit["id"], "villager")

        # 1. Bodyguard guards evil wolf from Vigilante: BG dies, wolf survives!
        submit_night_action(state, p_bg["id"], "guard_bodyguard", p_wolf["id"])
        submit_night_action(state, p_vig["id"], "shoot", p_wolf["id"], extra={"bullet_type": "danger"})
        state = resolve_night(state)
        assert state["players"][p_bg["id"]]["status"] == "dead"
        assert state["players"][p_wolf["id"]]["status"] == "alive"

        # 2. Bodyguard guards Citizen from Vigilante danger bullet:
        # Danger bullet backfires; both Citizen and Bodyguard survive!
        state["players"][p_bg["id"]]["status"] = "alive"
        state["phase"] = "night"
        submit_night_action(state, p_bg["id"], "guard_bodyguard", p_cit["id"])
        submit_night_action(state, p_vig["id"], "shoot", p_cit["id"], extra={"bullet_type": "danger"})
        state = resolve_night(state)
        assert state["players"][p_cit["id"]]["status"] == "alive"
        assert state["players"][p_bg["id"]]["status"] == "alive"
        assert state["players"][p_vig["id"]]["status"] == "dead"

    def test_sniper_shooting_detective_with_danger_bullet_backfires_and_detective_survives(self):
        """When Vigilante shoots innocent Detective with danger bullet, gun backfires.
        Vigilante dies of guilt, but Detective survives unharmed!
        """
        opts = {"sniper_bullet_type": "danger", "limbo_enabled": False}
        state = create_initial_state("SNIPER_DET", "Sniper Det Test", settings=opts)
        state, p_vig = add_player(state, "Vigilante")
        state, p_det = add_player(state, "Detective")
        set_manual_player_role(state, p_vig["id"], "sniper")
        set_manual_player_role(state, p_det["id"], "detective")

        record_gm_night_action(state, "sniper", p_det["id"], extra={"bullet_type": "danger"})
        resolve_night(state)

        # Vigilante died of backfire/guilt; Detective is alive!
        assert state["players"][p_vig["id"]]["status"] == "dead"
        assert state["players"][p_det["id"]]["status"] == "alive"

    def test_mayor_veto_once_per_person_and_public_double_vote(self):
        """Mayor veto is once per person! Public Mayor setting grants 2x voting power."""
        opts = {"limbo_enabled": False, "public_mayor": True}
        state = create_initial_state("MAYORPER", "Mayor Per Person", settings=opts)
        state, p_mayor = add_player(state, "Mayor")
        state, p_wolf = add_player(state, "Wolf")
        state, p_a = add_player(state, "PlayerA")
        state, p_b = add_player(state, "PlayerB")

        set_manual_player_role(state, p_mayor["id"], "mayor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_a["id"], "villager")
        set_manual_player_role(state, p_b["id"], "villager")

        # 1. Player A executed -> Mayor vetoes -> Player A pardoned and lives
        p_a["status"] = "dead"
        state["last_lynched_id"] = p_a["id"]
        ok, msg = record_gm_night_action(state, "mayor", extra={"veto": True})
        assert ok is True
        state = resolve_night(state)
        assert state["players"][p_a["id"]]["status"] == "alive"
        assert p_a["id"] in state["mayor_vetoed_ids"]

        # 2. Player A executed again -> Mayor cannot veto Player A a second time!
        state["phase"] = "night"
        p_a["status"] = "dead"
        state["last_lynched_id"] = p_a["id"]
        ok, msg = record_gm_night_action(state, "mayor", extra={"veto": True})
        assert ok is False
        assert "limit 1 veto per person" in msg

        # 3. Player B executed -> Mayor CAN veto Player B!
        state["last_lynched_id"] = p_b["id"]
        ok, msg = record_gm_night_action(state, "mayor", extra={"veto": True})
        assert ok is True
        state = resolve_night(state)
        assert state["players"][p_b["id"]]["status"] == "alive"
        assert p_b["id"] in state["mayor_vetoed_ids"]

        # 4. Public Mayor 2x vote weight
        state = start_voting_session(state, "two_stage_50pct")
        toggle_nomination_vote(state, p_mayor["id"], p_wolf["id"])
        # Mayor's vote has weight 2!
        view = get_voting_view(state)
        wolf_cand = next(c for c in view["nomination_candidates"] if c["id"] == p_wolf["id"])
        assert wolf_cand["vote_count"] == 2

    def test_silencer_can_vote_and_staggered_rule(self):
        """Silenced player can vote! Silencer cannot silence same person twice in a row."""
        state = create_initial_state("SILENCETEST", "Silence Test")
        state, p_sil = add_player(state, "Silencer")
        state, p_victim = add_player(state, "Victim")
        state, p_other = add_player(state, "Other")

        set_manual_player_role(state, p_sil["id"], "silencer")
        set_manual_player_role(state, p_victim["id"], "villager")
        set_manual_player_role(state, p_other["id"], "villager")

        # Night 1: Silencer silences Victim
        ok, msg = record_gm_night_action(state, "silencer", p_victim["id"])
        assert ok is True
        state = resolve_night(state)
        assert state["players"][p_victim["id"]]["is_silenced"] is True

        # Silenced player CAN vote in nomination and final vote!
        state = start_voting_session(state, "two_stage_50pct")
        ok_v, _ = toggle_nomination_vote(state, p_victim["id"], p_other["id"])
        assert ok_v is True

        # Night 2: Silencer attempts to silence Victim again -> rejected!
        state["phase"] = "night"
        ok_repeat, msg_repeat = record_gm_night_action(state, "silencer", p_victim["id"])
        assert ok_repeat is False
        assert "two nights in a row" in msg_repeat

    def test_witch_alive_check_no_self_heal(self):
        """Witch cannot self-heal if attacked tonight."""
        state = create_initial_state("WITCHTEST", "Witch Test", settings={"limbo_enabled": False})
        state, p_witch = add_player(state, "Witch")
        state, p_wolf = add_player(state, "Wolf")
        state, p_target = add_player(state, "Target")

        set_manual_player_role(state, p_witch["id"], "witch")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_target["id"], "villager")

        # Wolves attack Witch, and Witch attempts to revive herself
        record_gm_night_action(state, "wolves", p_witch["id"])
        record_gm_night_action(state, "witch", extra={"revive": True, "kill_target": p_target["id"]})
        state = resolve_night(state)

        # Witch dies and potions fail because she was attacked tonight!
        assert state["players"][p_witch["id"]]["status"] == "dead"
        assert state["players"][p_target["id"]]["status"] == "alive"

    def test_serial_killer_instant_win_when_wolves_perish(self):
        """If all wolves die and SK is alive, SK wins instant solo victory!"""
        state = create_initial_state("SKTEST", "SK Test")
        state, p_sk = add_player(state, "Dexter")
        state, p_wolf = add_player(state, "BadWolf")
        state, p_c1 = add_player(state, "Cit1")
        state, p_c2 = add_player(state, "Cit2")

        set_manual_player_role(state, p_sk["id"], "serial_killer")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_c1["id"], "villager")
        set_manual_player_role(state, p_c2["id"], "villager")

        # Wolf dies (executed)
        set_player_status(state, p_wolf["id"], "dead")
        winner = check_win_condition(state)
        assert winner == "serial_killer"
        assert state["pending_gameover"]["winner"] == "serial_killer"

    def test_watson_and_traveler_and_ghost_mechanics(self):
        """Watson sees Detective. Traveler is confirmed good. Ghost sends spectral clues."""
        state = create_initial_state("NEWROLESTEST", "New Roles Test")
        state, p_watson = add_player(state, "Watson")
        state, p_det = add_player(state, "Sherlock")
        state, p_trav = add_player(state, "Traveler")
        state, p_ghost = add_player(state, "Casper")

        set_manual_player_role(state, p_watson["id"], "watson")
        set_manual_player_role(state, p_det["id"], "detective")
        assign_midgame_role(state, p_trav["id"], "traveler")
        assign_midgame_role(state, p_ghost["id"], "ghost")

        # 1. Watson sanitized view sees Detective identity
        w_view = get_sanitized_player_view(state, p_watson["id"])
        assert w_view["me"]["watson_detective_name"] == "Sherlock"

        # 2. Traveler has confirmed good flag
        trav_entry = next(p for p in w_view["players"] if p["id"] == p_trav["id"])
        assert trav_entry["is_traveler"] is True

        # 3. Ghost can submit spectral message and GM approves it
        ok, msg = submit_ghost_message(state, p_ghost["id"], "Watch Player 3!")
        assert ok is True
        msg_id = state["ghost_messages"][0]["id"]
        ok_appr, _ = approve_ghost_message(state, msg_id, approved=True)
        assert ok_appr is True
        # At dawn, message appears in night report
        state["phase"] = "night"
        state = resolve_night(state)
        assert any("Watch Player 3!" in r for r in state["night_report"])

    def test_disgruntled_ghost_and_saboteur_wolf_suppression(self):
        """Disgruntled Ghost and Saboteur Wolf suppress targets' night abilities."""
        state = create_initial_state("SUPPTEST", "Suppression Test")
        state, p_dg = add_player(state, "DisgruntledGhost")
        state, p_sab = add_player(state, "Saboteur")
        state, p_doc = add_player(state, "Doctor")
        state, p_wolf = add_player(state, "Wolf")
        state, p_victim = add_player(state, "Victim")

        set_manual_player_role(state, p_dg["id"], "disgruntled_ghost")
        set_manual_player_role(state, p_sab["id"], "saboteur_wolf")
        set_manual_player_role(state, p_doc["id"], "doctor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_victim["id"], "villager")

        # Disgruntled ghost suppresses Doctor
        record_gm_night_action(state, "disgruntled_ghost", p_doc["id"])
        # Doctor tries to protect Victim
        record_gm_night_action(state, "doctor", p_victim["id"])
        # Wolves attack Victim
        record_gm_night_action(state, "wolves", p_victim["id"])

        state = resolve_night(state)
        # Doctor was suppressed, so Victim dies!
        assert state["players"][p_victim["id"]]["status"] in ("limbo", "dead")


class TestLupusVoting:
    def _create_room_with_players(self, count=6):
        state = create_initial_state("VOTEROOM", "Voting Room")
        players = []
        for i in range(count):
            state, p = add_player(state, f"Player_{i + 1}")
            p["role"] = "villager"
            p["faction"] = "town"
            players.append(p)
        return state, players

    def test_nomination_threshold_calculation(self):
        state, players = self._create_room_with_players(6)
        # 6 living players at 50% = 3
        assert get_nomination_threshold(state) == 3

        # 5 living players at 50% = ceil(2.5) = 3
        set_player_status(state, players[0]["id"], "dead")
        assert get_nomination_threshold(state) == 3

        # 4 living players at 50% = 2
        set_player_status(state, players[1]["id"], "dead")
        assert get_nomination_threshold(state) == 2

        # 7 living players at 50% = ceil(3.5) = 4
        state, _ = self._create_room_with_players(7)
        assert get_nomination_threshold(state) == 4

    def test_nomination_multi_voting_and_threshold(self):
        state, players = self._create_room_with_players(6)
        start_voting_session(state, "two_stage_50pct")
        assert state["voting"]["stage"] == "nomination"
        threshold = get_nomination_threshold(state)
        assert threshold == 3

        p1, p2, p3 = players[0], players[1], players[2]
        cand_a, cand_b = players[4], players[5]

        # Multi-vote: P1 votes for BOTH Cand A and Cand B
        success, _ = toggle_nomination_vote(state, p1["id"], cand_a["id"])
        assert success
        success, _ = toggle_nomination_vote(state, p1["id"], cand_b["id"])
        assert success

        # P2 votes for Cand A
        toggle_nomination_vote(state, p2["id"], cand_a["id"])

        # Cand A has 2 votes (< 3 threshold) -> Not yet nominated
        assert cand_a["id"] not in state["voting"]["nominated_player_ids"]

        # P3 votes for Cand A -> Reaches 3 votes (>= 3 threshold) -> Officially nominated!
        toggle_nomination_vote(state, p3["id"], cand_a["id"])
        assert cand_a["id"] in state["voting"]["nominated_player_ids"]

        # Cand B only has 1 vote (< 3 threshold)
        assert cand_b["id"] not in state["voting"]["nominated_player_ids"]

        # View check
        view = get_voting_view(state, is_gm=True, player_id=p1["id"])
        c_a_view = next(c for c in view["nomination_candidates"] if c["id"] == cand_a["id"])
        assert c_a_view["vote_count"] == 3
        assert c_a_view["is_nominated"] is True
        assert c_a_view["has_my_vote"] is True

    def test_proceed_to_defense_and_final_vote(self):
        state, players = self._create_room_with_players(6)
        start_voting_session(state)
        cand_a = players[4]

        # Trying to go to final vote with 0 nominees fails
        success, msg = proceed_to_final_vote(state)
        assert not success
        assert "No players were nominated" in msg

        # GM manually forces nomination
        toggle_official_nomination(state, cand_a["id"])
        assert cand_a["id"] in state["voting"]["nominated_player_ids"]

        # Proceed to defense
        proceed_to_defense(state, cand_a["id"])
        assert state["voting"]["stage"] == "defense"
        assert state["voting"]["defense_player_id"] == cand_a["id"]

        # Proceed to final vote
        success, _ = proceed_to_final_vote(state)
        assert success
        assert state["voting"]["stage"] == "final_vote"
        assert state["voting"]["ballot_locked"] is True

    def test_final_single_vote_and_override(self):
        state, players = self._create_room_with_players(6)
        start_voting_session(state)
        cand_a, cand_b = players[4], players[5]
        toggle_official_nomination(state, cand_a["id"])
        toggle_official_nomination(state, cand_b["id"])
        proceed_to_final_vote(state)

        voter = players[0]
        # Voter casts for Cand A
        success, _ = cast_final_vote(state, voter["id"], cand_a["id"])
        assert success
        assert state["voting"]["final_votes"][voter["id"]] == cand_a["id"]

        # Voter changes vote to Cand B -> Overwrites single vote!
        success, _ = cast_final_vote(state, voter["id"], cand_b["id"])
        assert success
        assert state["voting"]["final_votes"][voter["id"]] == cand_b["id"]
        assert len(state["voting"]["final_votes"]) == 1

        # Voting for non-ballot candidate fails
        success, msg = cast_final_vote(state, voter["id"], players[1]["id"])
        assert not success
        assert "not on the ballot" in msg

        # Dead player trying to vote fails
        set_player_status(state, players[2]["id"], "dead")
        success, msg = cast_final_vote(state, players[2]["id"], cand_a["id"])
        assert not success
        assert "Only living players" in msg

    def test_tie_breaker_first_tie_initiates_runoff(self):
        state, players = self._create_room_with_players(6)
        start_voting_session(state)
        cand_a, cand_b = players[4], players[5]
        toggle_official_nomination(state, cand_a["id"])
        toggle_official_nomination(state, cand_b["id"])
        proceed_to_final_vote(state)

        # 3 votes for Cand A, 3 votes for Cand B
        cast_final_vote(state, players[0]["id"], cand_a["id"])
        cast_final_vote(state, players[1]["id"], cand_a["id"])
        cast_final_vote(state, players[2]["id"], cand_a["id"])

        cast_final_vote(state, players[3]["id"], cand_b["id"])
        cast_final_vote(state, players[4]["id"], cand_b["id"])
        cast_final_vote(state, players[5]["id"], cand_b["id"])

        result, msg = tally_and_resolve_vote(state)
        assert result == "revote"
        assert "TIE" in msg
        assert state["voting"]["stage"] == "revote"
        assert state["voting"]["tie_count"] == 1
        assert set(state["voting"]["revote_candidates"]) == {cand_a["id"], cand_b["id"]}
        assert state["voting"]["final_votes"] == {}  # Cleared for revote

    def test_tie_breaker_second_tie_spares_everyone(self):
        state, players = self._create_room_with_players(6)
        start_voting_session(state)
        cand_a, cand_b = players[4], players[5]
        toggle_official_nomination(state, cand_a["id"])
        toggle_official_nomination(state, cand_b["id"])
        proceed_to_final_vote(state)

        # 1st tie
        record_gm_final_vote_tally(state, cand_a["id"], 2)
        record_gm_final_vote_tally(state, cand_b["id"], 2)
        res1, _ = tally_and_resolve_vote(state)
        assert res1 == "revote"
        assert state["voting"]["tie_count"] == 1

        # 2nd tie during revote
        record_gm_final_vote_tally(state, cand_a["id"], 2)
        record_gm_final_vote_tally(state, cand_b["id"], 2)
        res2, msg = tally_and_resolve_vote(state)

        # Second tie: NO ONE gets eliminated!
        assert res2 == "spared_on_tie"
        assert "NO ONE gets eliminated today" in msg
        assert state["voting"]["stage"] == "completed"
        assert state["voting"]["eliminated_player_id"] is None
        assert state["voting"]["elimination_result"] == "spared_on_tie"

        # Check players are still alive
        assert state["players"][cand_a["id"]]["status"] == "alive"
        assert state["players"][cand_b["id"]]["status"] == "alive"

    def test_execution_with_limbo_when_angel_alive(self):
        state, players = self._create_room_with_players(5)
        # One player is Angel
        players[0]["role"] = "angel"
        players[0]["status"] = "alive"
        state["settings"]["limbo_enabled"] = True

        victim = players[4]
        start_voting_session(state)
        toggle_official_nomination(state, victim["id"])
        proceed_to_final_vote(state)

        # Vote for victim
        record_gm_final_vote_tally(state, victim["id"], 3)
        res, msg = tally_and_resolve_vote(state)

        assert res == "eliminated"
        assert state["voting"]["elimination_result"] == "limbo"
        assert state["players"][victim["id"]]["status"] == "limbo"
        assert state["players"][victim["id"]]["used_limbo"] is True

    def test_execution_dead_when_angel_dead(self):
        state, players = self._create_room_with_players(5)
        players[0]["role"] = "angel"
        players[0]["status"] = "dead"  # Angel is dead!
        state["settings"]["limbo_enabled"] = True

        victim = players[4]
        start_voting_session(state)
        toggle_official_nomination(state, victim["id"])
        proceed_to_final_vote(state)

        record_gm_final_vote_tally(state, victim["id"], 3)
        res, msg = tally_and_resolve_vote(state)

        assert res == "eliminated"
        assert state["voting"]["elimination_result"] == "dead"
        assert state["players"][victim["id"]]["status"] == "dead"

    def test_jester_execution_solo_win(self):
        state, players = self._create_room_with_players(5)
        jester = players[4]
        jester["role"] = "jester"

        start_voting_session(state)
        toggle_official_nomination(state, jester["id"])
        proceed_to_final_vote(state)

        record_gm_final_vote_tally(state, jester["id"], 4)
        res, msg = tally_and_resolve_vote(state)

        assert res == "jester_win"
        assert "SOLO VICTORY" in msg
        assert state.get("pending_gameover", {}).get("winner") == "jester"
        assert state["phase"] != "gameover"

        # Host triggers Game Over
        trigger_game_over(state)
        assert state["winner"] == "jester"
        assert state["phase"] == "gameover"


class TestLupusQR:
    def test_generate_qr_data_uri(self):
        uri = generate_qr_data_uri("https://marco-silva.com/games/lupus/ROOM123/join/?pwd=test")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100


class TestLupusNotepadTemplate:
    def test_player_template_renders_notepad(self):
        from django.template.loader import render_to_string

        context = {
            "code": "TESTROOM",
            "player": {"id": "p1", "token": "tok1", "name": "Alice"},
            "state": {
                "title": "Test Room",
                "phase": "lobby",
                "round_number": 1,
                "players": [{"id": "p1", "name": "Alice", "status": "alive", "is_me": True}],
                "me": {"id": "p1", "name": "Alice", "status": "alive"},
                "timer": {"label": "Discussion", "remaining": 120, "paused": True},
            },
            "roles_catalogue": [
                {"id": "werewolf", "name": "Werewolf", "emoji": "🐺", "faction": "wolves"},
                {"id": "detective", "name": "Detective", "emoji": "🔍", "faction": "town"},
            ],
        }
        rendered = render_to_string("lupus/player.html", context)
        assert "Investigation Notepad" in rendered
        assert "player-notes-textarea" in rendered
        assert "notes-autocomplete-dropdown" in rendered
        assert "notes-role-chips" in rendered
        assert "notes-player-chips" in rendered
        assert "👥 Roster" in rendered
        assert "Roles in Play" in rendered
        assert "🗳️ Voted" in rendered
        assert "⏱️ Delayed Vote" in rendered
        assert "🤫 Quiet" in rendered
        assert "😰 Nervous" in rendered
        assert "floating-notes-pill" in rendered
        assert "🗞️ Town Gazette" in rendered
        assert "gazette-message-input" in rendered
        assert "successor-waiting-card" in rendered
        assert "heartbreak-warning-banner" in rendered

    def test_sanitized_view_roles_in_play(self, monkeypatch):
        mock_redis = MockRedis()
        monkeypatch.setattr("lupus.game_state.get_redis_client", lambda: mock_redis)

        state = create_initial_state("ROLESINPLAY", "Roles Room")
        state, p_a = add_player(state, "Alice")
        state, p_b = add_player(state, "Bob")
        set_deck(state, ["werewolf", "detective", "doctor", "villager"])

        view = get_sanitized_player_view(state, p_a["id"])
        assert "roles_in_play" in view
        role_ids = [r["id"] for r in view["roles_in_play"]]
        assert "werewolf" in role_ids
        assert "detective" in role_ids
        assert "doctor" in role_ids
        assert "villager" in role_ids

    def test_should_autofill_demo(self):
        # Matching triggers
        assert should_autofill_demo("test", "marco") is True
        assert should_autofill_demo("TEST", "Marco") is True
        assert should_autofill_demo("test123", "Marco Silva") is True
        assert should_autofill_demo("demo", "marco") is True
        assert should_autofill_demo("  test  ", "  Marco GM  ") is True

        # Non-matching triggers
        assert should_autofill_demo("secret", "marco") is False
        assert should_autofill_demo("test", "Alice") is False
        assert should_autofill_demo("", "marco") is False
        assert should_autofill_demo("test", "") is False
        assert should_autofill_demo(None, None) is False

    def test_setup_demo_room(self, monkeypatch):
        mock_redis = MockRedis()
        monkeypatch.setattr("lupus.game_state.get_redis_client", lambda: mock_redis)

        state = create_initial_state("DEMOROOM", "Demo Game", password="test", gm_name="Marco")
        assert len(state["players"]) == 0

        # Trigger demo room setup
        setup_demo_room(state)

        # Verify 10 players added
        assert len(state["players"]) == 10
        assert len(state["player_order"]) == 10

        names = [p["name"] for p in state["players"].values()]
        for expected_name in DEMO_PLAYER_NAMES:
            assert expected_name in names

        # Verify each player has proper alive status, token, and id
        for p in state["players"].values():
            assert p["status"] == "alive"
            assert len(p["token"]) > 0
            assert len(p["id"]) > 0
            assert p["is_offline"] is False

        # Deck should be adjusted to 10 cards (e.g. full_10)
        assert len(state["deck"]) == 10

        # Deal roles: each player named as their role gets their preassigned role!
        deal_roles(state)
        for p in state["players"].values():
            if p["name"] == "Werewolf":
                assert p["role"] == "werewolf"
            elif p["name"] == "Alpha Wolf":
                assert p["role"] == "alpha_wolf"
            elif p["name"] == "Detective":
                assert p["role"] == "detective"
            elif p["name"] == "Doctor":
                assert p["role"] == "doctor"
            elif p["name"] == "Vigilante":
                assert p["role"] == "sniper"
            elif p["name"] == "Mayor":
                assert p["role"] == "mayor"

        # Idempotency check: calling again does not duplicate players
        setup_demo_room(state)
        assert len(state["players"]) == 10
        assert len(state["player_order"]) == 10

    def test_preassign_role_and_deal(self):
        state = create_initial_state("PREASSIGN1", "Preassign Room")
        state, p_alice = add_player(state, "Alice")
        state, p_bob = add_player(state, "Bob")
        state, p_charlie = add_player(state, "Charlie")
        state, p_dave = add_player(state, "Dave")

        # GM pre-assigns Alice -> doctor, Bob -> werewolf
        ok, _ = set_preassigned_role(state, p_alice["id"], "doctor")
        assert ok
        ok, _ = set_preassigned_role(state, p_bob["id"], "werewolf")
        assert ok

        # Charlie and Dave have no preassigned role
        assert state["players"][p_charlie["id"]]["preassigned_role"] is None

        # Deal roles with 4 cards in deck
        deck = ["doctor", "werewolf", "villager", "villager"]
        deal_roles(state, deck)

        # Alice must be Doctor, Bob must be Werewolf
        assert state["players"][p_alice["id"]]["role"] == "doctor"
        assert state["players"][p_bob["id"]]["role"] == "werewolf"

        # Charlie and Dave must get the remaining villager cards
        assert state["players"][p_charlie["id"]]["role"] == "villager"
        assert state["players"][p_dave["id"]]["role"] == "villager"

        # Test clearing preassigned role
        ok, _ = set_preassigned_role(state, p_alice["id"], "clear")
        assert ok
        assert state["players"][p_alice["id"]]["preassigned_role"] is None

    def test_auto_assign_roles_from_names(self):
        state = create_initial_state("AUTOASSIGN1", "Autoassign Room")
        state, p1 = add_player(state, "Doctor John")
        state, p2 = add_player(state, "Werewolf Alpha")
        state, p3 = add_player(state, "Sherlock")
        state, p4 = add_player(state, "Vigilante")
        state, p5 = add_player(state, "Citizen Joe")
        state, p6 = add_player(state, "Random Person")

        matched = auto_assign_roles_from_names(state)
        assert matched == 5

        assert state["players"][p1["id"]]["preassigned_role"] == "doctor"
        assert state["players"][p2["id"]]["preassigned_role"] == "alpha_wolf"
        assert state["players"][p3["id"]]["preassigned_role"] == "detective"
        assert state["players"][p4["id"]]["preassigned_role"] == "sniper"
        assert state["players"][p5["id"]]["preassigned_role"] == "villager"
        assert state["players"][p6["id"]]["preassigned_role"] is None

        # Deal roles
        deal_roles(state)
        assert state["players"][p1["id"]]["role"] == "doctor"
        assert state["players"][p2["id"]]["role"] == "alpha_wolf"
        assert state["players"][p3["id"]]["role"] == "detective"
        assert state["players"][p4["id"]]["role"] == "sniper"
        assert state["players"][p5["id"]]["role"] == "villager"


    def test_successor_inherits_on_death(self):
        state = create_initial_state("TEST_SUCC1", "Successor Room")
        state, p_wolf = add_player(state, "Wolf Alpha")
        state, p_succ = add_player(state, "Waiting Understudy")
        set_manual_player_role(state, p_wolf["id"], "alpha_wolf")

        # Assign successor role mid-game
        ok, msg = assign_midgame_role(state, p_succ["id"], "successor")
        assert ok is True
        assert state["players"][p_succ["id"]]["status"] == "waiting"
        assert state["players"][p_succ["id"]]["is_successor"] is True

        # When wolf dies, waiting successor inherits the role & faction!
        set_player_status(state, p_wolf["id"], "dead")
        succ_state = state["players"][p_succ["id"]]
        assert succ_state["status"] == "alive"
        assert succ_state["role"] == "alpha_wolf"
        assert succ_state["faction"] == "wolves"
        assert succ_state["is_successor"] is False
        assert succ_state["inherited_from_name"] == "Wolf Alpha"

    def test_successor_saves_lover_from_heartbreak(self):
        state = create_initial_state("TEST_SUCC2", "Successor Lover Room")
        state, p_l1 = add_player(state, "Romeo")
        state, p_l2 = add_player(state, "Juliet")
        state, p_succ = add_player(state, "Paris Understudy")

        set_manual_player_role(state, p_l1["id"], "villager")
        set_manual_player_role(state, p_l2["id"], "villager")
        state["players"][p_l1["id"]]["lover_id"] = p_l2["id"]
        state["players"][p_l2["id"]]["lover_id"] = p_l1["id"]
        state["players"][p_l1["id"]]["lover_type"] = "innocent"
        state["players"][p_l2["id"]]["lover_type"] = "innocent"

        assign_midgame_role(state, p_succ["id"], "successor")
        assert state["players"][p_succ["id"]]["status"] == "waiting"

        # Romeo dies: instead of Juliet dying of heartbreak, Successor Paris steps in as new lover!
        set_player_status(state, p_l1["id"], "dead")
        assert state["players"][p_l1["id"]]["status"] == "dead"
        assert state["players"][p_l2["id"]]["status"] == "alive"  # Juliet is SAVED!
        assert state["players"][p_succ["id"]]["status"] == "alive"
        assert state["players"][p_succ["id"]]["lover_id"] == p_l2["id"]
        assert state["players"][p_l2["id"]]["lover_id"] == p_succ["id"]

    def test_lover_voted_out_staggered_heartbreak(self):
        state = create_initial_state("TEST_STAG1", "Staggered Heartbreak")
        state["settings"]["limbo_enabled"] = False  # Skip limbo for direct death test
        state, p_l1 = add_player(state, "Romeo")
        state, p_l2 = add_player(state, "Juliet")
        state, p_v = add_player(state, "Voter")

        state["players"][p_l1["id"]]["lover_id"] = p_l2["id"]
        state["players"][p_l2["id"]]["lover_id"] = p_l1["id"]

        state["phase"] = "day_voting"
        state["voting"] = {
            "stage": "final_vote",
            "system": "two_stage_50pct",
            "nomination_votes": {},
            "nominated_player_ids": [p_l1["id"]],
            "final_votes": {"v1": p_l1["id"], "v2": p_l1["id"]},
            "tie_count": 0,
            "revote_candidates": [],
            "defense_player_id": None,
            "eliminated_player_id": None,
            "elimination_result": None,
            "ballot_locked": False,
        }

        # Vote out Romeo
        outcome, msg = tally_and_resolve_vote(state)
        assert outcome == "eliminated"
        assert state["players"][p_l1["id"]]["status"] == "dead"
        # Staggered heartbreak: Juliet survives the day!
        assert state["players"][p_l2["id"]]["status"] == "alive"
        assert state["players"][p_l2["id"]]["pending_heartbreak"] is True

        # When night resolves, Juliet succumbs at dawn!
        # Test concealed cause first (default public_heartbreak_cause = False)
        state["settings"]["public_heartbreak_cause"] = False
        resolve_night(state)
        assert state["players"][p_l2["id"]]["status"] == "dead"
        assert "🪦 Juliet was found dead at dawn." in state["night_report"]

    def test_news_bulletin_limits_and_gm_approval(self):
        state = create_initial_state("TEST_NEWS", "Gazette Test")
        state, p_alive = add_player(state, "Living Journalist")
        state, p_dead = add_player(state, "Ghost Inquirer")
        set_player_status(state, p_dead["id"], "dead")

        # 1. Living player posts news
        ok, msg = submit_news_bulletin(state, p_alive["id"], "I saw someone suspicious near the fountain!", anonymous=False)
        assert ok is True
        assert len(state["news_bulletins"]) == 1

        # Living player tries posting second time on same day -> rejected (1 per day)
        ok2, msg2 = submit_news_bulletin(state, p_alive["id"], "Another scoop!", anonymous=False)
        assert ok2 is False
        assert "one news bulletin per day" in msg2

        # 2. Dead player posts news (anonymous)
        ok_d, msg_d = submit_news_bulletin(state, p_dead["id"], "Watch out for player #3...", anonymous=True)
        assert ok_d is True
        assert len(state["news_bulletins"]) == 2

        # Dead player tries posting a second time -> rejected (1 lifetime post)
        ok_d2, msg_d2 = submit_news_bulletin(state, p_dead["id"], "Second whisper", anonymous=True)
        assert ok_d2 is False
        assert "only submit one news bulletin total" in msg_d2

        # 3. GM approves both bulletins
        b_alive_id = state["news_bulletins"][0]["id"]
        b_dead_id = state["news_bulletins"][1]["id"]
        approve_news_bulletin(state, b_alive_id, approved=True)
        approve_news_bulletin(state, b_dead_id, approved=True)

        assert len(state["approved_news_bulletins"]) == 2

        # 4. Resolve night -> morning report includes Gazette bulletins!
        resolve_night(state)
        report = state["night_report"]
        assert any("Living Journalist writes: \"I saw someone suspicious near the fountain!\"" in r for r in report)
        assert any("Anonymous Informant writes: \"Watch out for player #3...\"" in r for r in report)


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

    def test_lupus_hub_get_empty(self, client):
        res = client.get(reverse("gamerooms:lupus:hub"))
        assert res.status_code == 200
        content = res.content.decode()
        assert "Lupus in Tabula" in content
        assert "Active Lupus Rooms" in content
        assert "No Active Lupus Games Right Now" in content

    def test_lupus_hub_lists_active_rooms(self, client):
        lupus_room = Room.objects.create(code="WOLF1234", title="Wolf Pack Night", game_type="lupus")
        create_initial_state(lupus_room.code, lupus_room.title, gm_name="Chief Wolf")
        Room.objects.create(code="EMOJI999", title="Emojinary Fun", game_type="emojinary")

        res = client.get(reverse("gamerooms:lupus:hub"))
        assert res.status_code == 200
        content = res.content.decode()
        assert "Wolf Pack Night" in content
        assert "WOLF1234" in content
        assert "Chief Wolf" in content
        # Emojinary room should NOT appear in Lupus-specific hub
        assert "Emojinary Fun" not in content

    def test_lupus_hub_code_redirect(self, client):
        room = Room.objects.create(code="FASTJOIN", title="Fast Room", game_type="lupus")
        create_initial_state(room.code, room.title)

        # POST code
        res_post = client.post(reverse("gamerooms:lupus:hub"), {"code": "fastjoin"})
        assert res_post.status_code == 302
        assert reverse("gamerooms:lupus:join", kwargs={"code": "FASTJOIN"}) in res_post.url

        # GET ?code=...
        res_get = client.get(f"{reverse('gamerooms:lupus:hub')}?code=fastjoin")
        assert res_get.status_code == 302
        assert reverse("gamerooms:lupus:join", kwargs={"code": "FASTJOIN"}) in res_get.url

    def test_lupus_hub_invalid_code_error(self, client):
        res = client.post(reverse("gamerooms:lupus:hub"), {"code": "NOTFOUND"})
        assert res.status_code == 200
        assert "Room code &#x27;NOTFOUND&#x27; was not found" in res.content.decode() or "not found" in res.content.decode()

    def test_lupus_root_redirect(self, client):
        res_slash = client.get("/lupus/")
        assert res_slash.status_code == 302
        assert res_slash.url == "/games/lupus/"

        res_no_slash = client.get("/lupus")
        assert res_no_slash.status_code == 302
        assert res_no_slash.url == "/games/lupus/"


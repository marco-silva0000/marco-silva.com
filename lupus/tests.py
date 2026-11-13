"""Unit tests for Lupus game rules, state machine, and views."""

import pytest
from django.urls import reverse

from gamerooms.models import Room
from lupus.game_state import (
    DEMO_PLAYER_NAMES,
    add_player,
    adjust_timer,
    advance_circular_turn,
    advance_to_night,
    approve_ghost_message,
    approve_news_bulletin,
    assign_midgame_role,
    auto_assign_roles_from_names,
    build_round_timeline,
    cast_final_vote,
    check_win_condition,
    clear_gm_night_action,
    create_initial_state,
    deal_roles,
    dismiss_pending_gameover,
    export_game_replay,
    get_game,
    get_gm_view,
    get_living_players,
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
    set_martyrdom_target,
    set_night_stage_index,
    set_player_status,
    set_preassigned_role,
    set_turn_order_direction,
    setup_demo_room,
    should_autofill_demo,
    start_circular_turn_order,
    start_game,
    start_timer,
    start_voting_session,
    stop_circular_turn_order,
    submit_ghost_message,
    submit_news_bulletin,
    submit_night_action,
    tally_and_resolve_vote,
    toggle_hand_raise,
    toggle_nomination_vote,
    toggle_official_nomination,
    toggle_player_gazette_mute,
    toggle_player_silence,
    trigger_game_over,
    trigger_martyrdom_detonation,
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
        assert state["round_number"] == 0
        assert state["is_night_zero"] is True
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
        assert "Evil" in msg

        # Inspect alpha wolf (should appear innocent!)
        ok2, msg2 = submit_night_action(state, p_det["id"], "inspect", p_alpha["id"])
        assert ok2 is True
        assert "Good" in msg2

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
        assert query["result"] == "Evil"

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
        assert query["result"] == "Evil"
        assert query["is_evil"] is True

        # 5. Test reveal_detective_to_player: only Detective sees the revealed inspect
        reveal_detective_to_player(state)
        det_view = get_sanitized_player_view(state, p_det["id"])
        assert det_view["revealed_inspect"] is not None
        assert det_view["revealed_inspect"]["result"] == "Evil"

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
        """Witch cannot self-heal if attacked tonight, but her recorded powers still work."""
        state = create_initial_state("WITCHTEST", "Witch Test", settings={"limbo_enabled": False})
        state, p_witch = add_player(state, "Witch")
        state, p_wolf = add_player(state, "Wolf")
        state, p_target = add_player(state, "Target")

        set_manual_player_role(state, p_witch["id"], "witch")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_target["id"], "villager")

        # Wolves attack Witch, and Witch attempts to revive herself and poison Target
        record_gm_night_action(state, "wolves", p_witch["id"])
        record_gm_night_action(state, "witch", extra={"revive": True, "kill_target": p_target["id"]})
        state = resolve_night(state)

        # Witch cannot self-heal from wolf attack, so she dies:
        assert state["players"][p_witch["id"]]["status"] == "dead"
        # BUT her recorded poison potion still resolves simultaneously, killing Target!
        assert state["players"][p_target["id"]]["status"] == "dead"
        assert state["witch_used_kill"] is True

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

        # Verify demo players added (all 22 roles)
        assert len(state["players"]) == len(DEMO_PLAYER_NAMES)
        assert len(state["player_order"]) == len(DEMO_PLAYER_NAMES)

        names = [p["name"] for p in state["players"].values()]
        for expected_name in DEMO_PLAYER_NAMES:
            assert expected_name in names

        # Verify each player has proper alive status, token, and id
        for p in state["players"].values():
            assert p["status"] == "alive"
            assert len(p["token"]) > 0
            assert len(p["id"]) > 0
            assert p["is_offline"] is False

        # Deck should be adjusted to all 22 demo cards
        assert len(state["deck"]) == len(DEMO_PLAYER_NAMES)

        # Deal roles: each player named as their role gets their preassigned role!
        deal_roles(state)
        for p in state["players"].values():
            if p["name"] == "Lobisomem":
                assert p["role"] == "werewolf"
            elif p["name"] == "Lobo Alfa":
                assert p["role"] == "alpha_wolf"
            elif p["name"] == "Vidente":
                assert p["role"] == "detective"
            elif p["name"] == "Médico":
                assert p["role"] == "doctor"
            elif p["name"] == "Vigilante":
                assert p["role"] == "sniper"
            elif p["name"] == "Presidente":
                assert p["role"] == "mayor"

        # Idempotency check: calling again does not duplicate players
        setup_demo_room(state)
        assert len(state["players"]) == len(DEMO_PLAYER_NAMES)
        assert len(state["player_order"]) == len(DEMO_PLAYER_NAMES)

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
        ok, msg = submit_news_bulletin(
            state, p_alive["id"], "I saw someone suspicious near the fountain!", anonymous=False
        )
        assert ok is True
        assert len(state["news_bulletins"]) == 1

        # Living player tries posting second time while first is still pending -> rejected (only 1 pending at a time)
        ok2, msg2 = submit_news_bulletin(state, p_alive["id"], "Another scoop!", anonymous=False)
        assert ok2 is False
        assert "waiting for Game Master review" in msg2

        # 2. Dead player posts news (anonymous)
        ok_d, msg_d = submit_news_bulletin(state, p_dead["id"], "Watch out for player #3...", anonymous=True)
        assert ok_d is True
        assert len(state["news_bulletins"]) == 2

        # Dead player tries posting a second time while first is pending -> rejected
        ok_d2, msg_d2 = submit_news_bulletin(state, p_dead["id"], "Second whisper", anonymous=True)
        assert ok_d2 is False
        assert "waiting for Game Master review" in msg_d2

        # 3. GM approves both bulletins
        b_alive_id = state["news_bulletins"][0]["id"]
        b_dead_id = state["news_bulletins"][1]["id"]
        approve_news_bulletin(state, b_alive_id, approved=True)
        approve_news_bulletin(state, b_dead_id, approved=True)

        assert len(state["approved_news_bulletins"]) == 2

        # 4. Now that prior bulletin was approved, player can post another bulletin!
        ok3, msg3 = submit_news_bulletin(state, p_alive["id"], "Second breaking scoop!", anonymous=False)
        assert ok3 is True
        assert len(state["news_bulletins"]) == 3

        # 5. Resolve night -> morning report includes Gazette bulletins!
        resolve_night(state)
        report = state["night_report"]
        assert any('Living Journalist writes: "I saw someone suspicious near the fountain!"' in r for r in report)
        assert any('Anonymous Informant writes: "Watch out for player #3..."' in r for r in report)


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
        assert (
            "Room code &#x27;NOTFOUND&#x27; was not found" in res.content.decode()
            or "not found" in res.content.decode()
        )

    def test_lupus_root_redirect(self, client):
        res_slash = client.get("/lupus/")
        assert res_slash.status_code == 302
        assert res_slash.url == "/games/lupus/"

        res_no_slash = client.get("/lupus")
        assert res_no_slash.status_code == 302
        assert res_no_slash.url == "/games/lupus/"


class TestLupusNewFeaturesV114:
    """Unit tests for v114 feature set:

    - Night 0 / Day 0 sequence with voting locks
    - Death Angel role & Angel dependency demotion
    - Wolf Hunter role (hunting wolves vs guilt backfire on innocent)
    - Quantified role reveal levels on death-death
    - Real-time player finger pointing and dawn clearance
    - Coroner autopsy report Gazette leaks
    """

    def test_night0_and_day0_sequence_and_voting_lock(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_night_stages,
            record_gm_night_action,
            resolve_night,
            start_game,
            start_voting_session,
        )

        state = create_initial_state("N0TEST", "Night 0 Flow")
        for name in ["Alice", "Bob", "Charlie", "David", "Eve"]:
            state, _ = add_player(state, name)

        deck = ["werewolf", "hacker", "detective", "villager", "villager"]
        state = start_game(state, deck)

        # 1. Starts at Night 0
        assert state["phase"] == "night"
        assert state["round_number"] == 0
        assert state["is_night_zero"] is True

        # Night 0 stages have weapons holstered
        n0_stages = get_night_stages(state)
        n0_stage_ids = [s["id"] for s in n0_stages]
        assert "wolves" not in n0_stage_ids  # lethal wolves hunt is NOT in Night 0
        assert "wolves_meet" in n0_stage_ids  # wolves only awaken to see each other
        assert "hacker" in n0_stage_ids

        # Hacker scans 2 players during Night 0
        c_id = next(p["id"] for p in state["players"].values() if p["name"] == "Charlie")
        d_id = next(p["id"] for p in state["players"].values() if p["name"] == "David")
        record_gm_night_action(state, "hacker", c_id)
        record_gm_night_action(state, "hacker", d_id)

        # 2. Resolve Night 0 -> transitions to Day 0
        state = resolve_night(state)
        assert state["phase"] == "day_discussion"
        assert state["round_number"] == 0
        assert state["is_night_zero"] is False
        assert state["is_day_zero"] is True
        assert any("Day 0" in r for r in state["night_report"])

        # Voting is strictly locked on Day 0
        start_voting_session(state)
        assert state["voting"]["stage"] == "none"

    def test_death_angel_and_angel_dependency(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            deal_roles,
            record_gm_night_action,
            resolve_night,
            set_player_status,
        )

        # 1. Death Angel standalone: remains death_angel even without Angel dealt!
        state = create_initial_state("DATEST1", "Death Angel Test")
        for name in ["P1", "P2", "P3", "P4"]:
            state, _ = add_player(state, name)

        deck_no_angel = ["death_angel", "werewolf", "villager", "villager"]
        deal_roles(state, deck_no_angel)
        # Standalone role: not demoted, keeps death_angel!
        assert any(p["role"] == "death_angel" for p in state["players"].values())
        da_player = next(p for p in state["players"].values() if p["role"] == "death_angel")
        assert da_player["death_angel_strikes"] == 1

        # 2. Death Angel with Angel dealt -> kept as death_angel!
        state2 = create_initial_state("DATEST2", "Death Angel with Angel")
        for name in ["P1", "P2", "P3", "P4"]:
            state2, _ = add_player(state2, name)

        deck_with_angel = ["death_angel", "angel", "werewolf", "villager"]
        deal_roles(state2, deck_with_angel)
        p_da = next(p for p in state2["players"].values() if p["role"] == "death_angel")
        p_target = next(p for p in state2["players"].values() if p["role"] == "villager")
        assert p_da is not None
        assert p_da["death_angel_strikes"] == 1

        # Put target in Limbo
        set_player_status(state2, p_target["id"], "limbo")
        assert p_target["status"] == "limbo"

        # Death Angel strikes target in Limbo
        ok, msg = record_gm_night_action(state2, "death_angel", p_target["id"])
        assert ok is True
        state2 = resolve_night(state2)

        # Target in Limbo is struck to eternal death!
        assert state2["players"][p_target["id"]]["status"] == "dead"
        assert state2["death_angel_used"] is True
        assert any("Death Angel struck" in r for r in state2["night_report"])

    def test_wolf_hunter_mechanics(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            record_gm_night_action,
            resolve_night,
            set_manual_player_role,
        )

        # 1. Wolf Hunter shoots a Werewolf -> Werewolf dies
        state = create_initial_state("WHTEST1", "Wolf Hunter Win")
        state, p_hunter = add_player(state, "Hunter")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_innocent = add_player(state, "Innocent")

        set_manual_player_role(state, p_hunter["id"], "wolf_hunter")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_innocent["id"], "villager")

        record_gm_night_action(state, "wolf_hunter", p_wolf["id"])
        state = resolve_night(state)
        assert state["players"][p_wolf["id"]]["status"] == "dead"
        assert state["players"][p_hunter["id"]]["status"] == "alive"

        # 2. Wolf Hunter shoots non-wolf -> Hunter dies of guilt, innocent unharmed!
        state2 = create_initial_state("WHTEST2", "Wolf Hunter Backfire")
        state2, p_hunter2 = add_player(state2, "Hunter2")
        state2, p_wolf2 = add_player(state2, "Wolfie2")
        state2, p_innocent2 = add_player(state2, "Innocent2")

        set_manual_player_role(state2, p_hunter2["id"], "wolf_hunter")
        set_manual_player_role(state2, p_wolf2["id"], "werewolf")
        set_manual_player_role(state2, p_innocent2["id"], "villager")

        record_gm_night_action(state2, "wolf_hunter", p_innocent2["id"])
        state2 = resolve_night(state2)
        assert state2["players"][p_innocent2["id"]]["status"] == "alive"
        assert state2["players"][p_hunter2["id"]]["status"] == "dead"

    def test_quantified_death_reveals(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            set_manual_player_role,
            set_player_status,
        )

        # Level 1: Alignment (GOOD / EVIL)
        s1 = create_initial_state("REV1", "Rev 1", settings={"reveal_roles_on_death": 1})
        s1, p_good = add_player(s1, "GoodDoc")
        s1, p_evil = add_player(s1, "BadWolf")
        set_manual_player_role(s1, p_good["id"], "doctor")
        set_manual_player_role(s1, p_evil["id"], "werewolf")

        # In Limbo: reveal suppressed!
        set_player_status(s1, p_good["id"], "limbo")
        assert s1["players"][p_good["id"]]["death_reveal"] is None

        # Death Death: reveal computed!
        set_player_status(s1, p_good["id"], "dead")
        assert s1["players"][p_good["id"]]["death_reveal"] == "Alignment: GOOD"

        set_player_status(s1, p_evil["id"], "dead")
        assert s1["players"][p_evil["id"]]["death_reveal"] == "Alignment: EVIL"

        # Level 3: Full Role
        s3 = create_initial_state("REV3", "Rev 3", settings={"reveal_roles_on_death": 3})
        s3, p_doc = add_player(s3, "Medic")
        set_manual_player_role(s3, p_doc["id"], "doctor")
        set_player_status(s3, p_doc["id"], "dead")
        assert "Doctor" in s3["players"][p_doc["id"]]["death_reveal"]

    def test_player_pointing_and_clearing(self):
        from lupus.game_state import (
            add_player,
            clear_all_player_points,
            create_initial_state,
            get_sanitized_player_view,
            point_at_player,
            resolve_night,
        )

        state = create_initial_state("POINTTEST", "Pointing Test")
        state, p_alice = add_player(state, "Alice")
        state, p_bob = add_player(state, "Bob")

        # Alice points at Bob
        point_at_player(state, p_alice["id"], p_bob["id"])
        assert state["player_points"][p_alice["id"]] == p_bob["id"]

        pv = get_sanitized_player_view(state, p_alice["id"])
        assert pv["my_point_target_id"] == p_bob["id"]

        # Alice unpoints
        point_at_player(state, p_alice["id"], None)
        assert p_alice["id"] not in state["player_points"]

        # Clear all
        point_at_player(state, p_alice["id"], p_bob["id"])
        clear_all_player_points(state)
        assert len(state["player_points"]) == 0

        # Auto-clear on dawn
        point_at_player(state, p_alice["id"], p_bob["id"])
        resolve_night(state)
        assert len(state["player_points"]) == 0

    def test_coroner_leak_to_gazette(self):
        from lupus.game_state import (
            add_player,
            coroner_leak_to_gazette,
            create_initial_state,
            set_manual_player_role,
            set_player_status,
        )

        state = create_initial_state("CORONERTEST", "Coroner Test")
        state, p_dead = add_player(state, "Deceased")
        set_manual_player_role(state, p_dead["id"], "werewolf")
        set_player_status(state, p_dead["id"], "dead")

        # Leak alignment
        ok, msg = coroner_leak_to_gazette(state, p_dead["id"], "alignment")
        assert ok is True
        assert len(state["approved_news_bulletins"]) == 1
        bulletin = state["approved_news_bulletins"][0]
        assert "Coroner's Report" in bulletin["message"]
        assert "confirms alignment: EVIL" in bulletin["message"]

        # Leak role
        ok2, msg2 = coroner_leak_to_gazette(state, p_dead["id"], "role")
        assert ok2 is True
        assert len(state["approved_news_bulletins"]) == 2
        bulletin2 = state["approved_news_bulletins"][1]
        assert "Werewolf" in bulletin2["message"]

    def test_public_mayor_immunity_from_town_lynch(self):
        """Public Mayor holds executive immunity and CANNOT be voted out by town execution."""
        from lupus.game_state import (
            add_player,
            cast_final_vote,
            create_initial_state,
            get_voter_weight,
            proceed_to_final_vote,
            set_manual_player_role,
            start_voting_session,
            tally_and_resolve_vote,
            toggle_official_nomination,
        )

        state = create_initial_state("PUBMAYOR", "Public Mayor Room", settings={"mayor_type": "public"})
        state, p_mayor = add_player(state, "MayorDan")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_v1 = add_player(state, "Villager1")

        state["phase"] = "day_discussion"
        set_manual_player_role(state, p_mayor["id"], "mayor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_v1["id"], "villager")

        # Public Mayor has 2x vote weight
        assert get_voter_weight(state, p_mayor["id"]) == 2

        # Start voting and nominate Mayor
        state = start_voting_session(state, "two_stage_50pct")
        toggle_official_nomination(state, p_mayor["id"])
        proceed_to_final_vote(state)

        # Both wolf and villager vote to execute Mayor
        cast_final_vote(state, p_wolf["id"], p_mayor["id"])
        cast_final_vote(state, p_v1["id"], p_mayor["id"])

        result, msg = tally_and_resolve_vote(state)
        assert result == "mayor_immune"
        assert "holds executive immunity as Public Mayor" in msg
        assert state["players"][p_mayor["id"]]["status"] == "alive"
        assert state["voting"]["eliminated_player_id"] is None
        assert state["voting"]["elimination_result"] == "mayor_immune"

    def test_hidden_mayor_can_be_executed_and_has_single_vote(self):
        """Hidden Mayor has 1x vote and CAN be voted out by town execution."""
        from lupus.game_state import (
            add_player,
            cast_final_vote,
            create_initial_state,
            get_voter_weight,
            proceed_to_final_vote,
            set_manual_player_role,
            start_voting_session,
            tally_and_resolve_vote,
            toggle_official_nomination,
        )

        state = create_initial_state(
            "HIDMAYOR", "Hidden Mayor Room", settings={"mayor_type": "hidden", "limbo_enabled": False}
        )
        state, p_mayor = add_player(state, "SecretMayor")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_v1 = add_player(state, "Villager1")

        state["phase"] = "day_discussion"
        set_manual_player_role(state, p_mayor["id"], "mayor")
        set_manual_player_role(state, p_wolf["id"], "werewolf")
        set_manual_player_role(state, p_v1["id"], "villager")

        # Hidden Mayor has standard 1x vote weight
        assert get_voter_weight(state, p_mayor["id"]) == 1
        assert state["players"][p_mayor["id"]]["is_public_mayor"] is False

        # Start voting and nominate Hidden Mayor
        state = start_voting_session(state, "two_stage_50pct")
        toggle_official_nomination(state, p_mayor["id"])
        proceed_to_final_vote(state)

        cast_final_vote(state, p_wolf["id"], p_mayor["id"])
        cast_final_vote(state, p_v1["id"], p_mayor["id"])

        result, msg = tally_and_resolve_vote(state)
        assert result == "eliminated"
        assert state["players"][p_mayor["id"]]["status"] == "dead"
        assert state["voting"]["eliminated_player_id"] == p_mayor["id"]

    def test_sniper_bullet_tuning_deal_and_view(self):
        """Sniper danger and silver bullet counts are tuned on card settings and dealt correctly."""
        from lupus.game_state import (
            add_player,
            create_initial_state,
            deal_roles,
            get_sanitized_player_view,
        )

        state = create_initial_state(
            "SNIPTUNE",
            "Sniper Tuning Room",
            settings={"sniper_danger_bullets": 3, "sniper_silver_bullets": 2},
        )
        state, p1 = add_player(state, "Hawkeye")
        state, p2 = add_player(state, "WolfA")
        state, p3 = add_player(state, "VillagerB")

        deck = ["sniper", "werewolf", "villager"]
        state = deal_roles(state, deck)

        sniper_p = next(p for p in state["players"].values() if p["role"] == "sniper")
        assert sniper_p["sniper_danger_bullets"] == 3
        assert sniper_p["sniper_silver_bullets"] == 2

        pv = get_sanitized_player_view(state, sniper_p["id"])
        assert pv["me"]["sniper_danger_bullets"] == 3
        assert pv["me"]["sniper_silver_bullets"] == 2
        assert pv["settings"]["sniper_danger_bullets"] == 3
        assert pv["settings"]["sniper_silver_bullets"] == 2


class TestLupusMayorCancelVoteAndPreassignV116:
    """Test suite for v116: Mayor vote canceling toggles and pre-assignment enhancements."""

    def test_mayor_can_cancel_vote_toggle_on_and_off(self):
        """Both Public and Hidden Mayors can have the power to cancel the vote enabled or disabled."""
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_night_stages,
            record_gm_night_action,
            resolve_night,
            set_manual_player_role,
        )

        # 1. Mayor with cancel vote power ENABLED (default True)
        state_on = create_initial_state(
            "MAYORVETO1",
            "Mayor Veto Room",
            settings={"mayor_type": "public", "mayor_can_cancel_vote": True, "limbo_enabled": False},
        )
        state_on, p_mayor = add_player(state_on, "PublicMayor")
        state_on, p_victim = add_player(state_on, "Condemned")
        state_on, p_wolf = add_player(state_on, "Wolf")

        state_on["phase"] = "night"
        state_on["round_number"] = 2
        set_manual_player_role(state_on, p_mayor["id"], "mayor")
        set_manual_player_role(state_on, p_victim["id"], "villager")
        set_manual_player_role(state_on, p_wolf["id"], "werewolf")

        # Condemned was lynched
        state_on["last_lynched_id"] = p_victim["id"]
        state_on["players"][p_victim["id"]]["status"] = "dead"

        stages_on = get_night_stages(state_on)
        m_stage_on = next(s for s in stages_on if s["id"] == "mayor")
        assert m_stage_on["has_veto"] is True
        assert m_stage_on["can_cancel_vote"] is True

        # GM can record veto
        ok, msg = record_gm_night_action(state_on, "mayor", extra={"veto": True})
        assert ok is True
        assert state_on["night_actions"]["mayor_veto"] is True

        # Dawn resolution revives condemned
        state_on = resolve_night(state_on)
        assert state_on["players"][p_victim["id"]]["status"] == "alive"
        assert state_on["mayor_used_veto"] is True

        # 2. Mayor with cancel vote power DISABLED (mayor_can_cancel_vote = False)
        state_off = create_initial_state(
            "MAYORVETO2",
            "Mayor No Veto Room",
            settings={"mayor_type": "hidden", "mayor_can_cancel_vote": False, "limbo_enabled": False},
        )
        state_off, p_m2 = add_player(state_off, "HiddenMayor")
        state_off, p_v2 = add_player(state_off, "Condemned2")
        state_off, p_w2 = add_player(state_off, "Wolf2")

        state_off["phase"] = "night"
        state_off["round_number"] = 2
        set_manual_player_role(state_off, p_m2["id"], "mayor")
        set_manual_player_role(state_off, p_v2["id"], "villager")
        set_manual_player_role(state_off, p_w2["id"], "werewolf")

        state_off["last_lynched_id"] = p_v2["id"]
        state_off["players"][p_v2["id"]]["status"] = "dead"

        stages_off = get_night_stages(state_off)
        m_stage_off = next(s for s in stages_off if s["id"] == "mayor")
        assert m_stage_off["has_veto"] is False
        assert m_stage_off["can_cancel_vote"] is False

        # GM cannot record veto when power is disabled
        ok, err_msg = record_gm_night_action(state_off, "mayor", extra={"veto": True})
        assert ok is False
        assert "power to cancel the vote" in err_msg

    def test_auto_assign_death_angel_and_wolf_hunter_keywords(self):
        """Auto-assign scans and matches player names for Death Angel and Wolf Hunter."""
        from lupus.game_state import (
            add_player,
            auto_assign_roles_from_names,
            create_initial_state,
        )

        state = create_initial_state("AUTOASSIGN2", "Autoassign Addons Room")
        state, p1 = add_player(state, "Death Angel 1")
        state, p2 = add_player(state, "Wolf Hunter Bob")
        state, p3 = add_player(state, "Dark Angel")
        state, p4 = add_player(state, "Lone Hunter")

        matched = auto_assign_roles_from_names(state)
        assert matched == 4
        assert state["players"][p1["id"]]["preassigned_role"] == "death_angel"
        assert state["players"][p2["id"]]["preassigned_role"] == "wolf_hunter"
        assert state["players"][p3["id"]]["preassigned_role"] == "death_angel"
        assert state["players"][p4["id"]]["preassigned_role"] == "wolf_hunter"


class TestLupusV118Features:
    """Test suite for v118 features:
    - Death Angel standalone role (no demotion without Angel).
    - Wakeup stages without targets (lovers_meet, watson_intro, wolves_meet).
    - Hacker waking only on Round 0 (Night 0), not on Round 1.
    - Gazette reset and game_history archiving on return_to_lobby.
    """

    def test_hacker_only_on_round_0(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_night_stages,
            set_manual_player_role,
        )

        state = create_initial_state("HACKER01", "Hacker Night Scheduling Test")
        for name in ["Alice", "Bob", "Charlie", "Dave"]:
            state, _ = add_player(state, name)

        pids = list(state["players"].keys())
        set_manual_player_role(state, pids[0], "hacker")
        set_manual_player_role(state, pids[1], "werewolf")
        set_manual_player_role(state, pids[2], "villager")
        set_manual_player_role(state, pids[3], "villager")

        # Round 0 (Night 0): Hacker scan is present
        state["round_number"] = 0
        state["is_night_zero"] = True
        state["phase"] = "night"
        stages_r0 = get_night_stages(state)
        assert any(s["id"] == "hacker" for s in stages_r0)

        # Round 1 (Night 1): Hacker scan is NOT scheduled (only on Round 0)
        state["round_number"] = 1
        state["is_night_zero"] = False
        state["phase"] = "night"
        stages_r1 = get_night_stages(state)
        assert not any(s["id"] == "hacker" for s in stages_r1)

    def test_no_target_on_wakeup_stages(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_night_stages,
            set_manual_player_role,
        )

        state = create_initial_state("NOTARGET1", "No Target Stages Test")
        for name in ["Lover1", "Lover2", "Det", "Wat", "Wolf1"]:
            state, _ = add_player(state, name)

        pids = list(state["players"].keys())
        set_manual_player_role(state, pids[0], "lover")
        set_manual_player_role(state, pids[1], "lover")
        set_manual_player_role(state, pids[2], "detective")
        set_manual_player_role(state, pids[3], "watson")
        set_manual_player_role(state, pids[4], "werewolf")

        state["round_number"] = 0
        state["is_night_zero"] = True
        state["phase"] = "night"
        stages = get_night_stages(state)

        stage_map = {s["id"]: s for s in stages}
        assert "lovers_meet" in stage_map
        assert stage_map["lovers_meet"].get("no_target") is True

        assert "watson_intro" in stage_map
        assert stage_map["watson_intro"].get("no_target") is True

        assert "wolves_meet" in stage_map
        assert stage_map["wolves_meet"].get("no_target") is True

    def test_return_to_lobby_resets_gazette_and_archives_history(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            deal_roles,
            return_to_lobby,
            submit_news_bulletin,
        )

        state = create_initial_state("HIST01", "History and Gazette Reset Test")
        for name in ["P1", "P2", "P3", "P4"]:
            state, _ = add_player(state, name)

        deal_roles(state, ["werewolf", "villager", "villager", "villager"])
        pids = list(state["players"].keys())

        # Submit news bulletins
        state["round_number"] = 1
        ok, _ = submit_news_bulletin(state, pids[1], "I suspect P1 is evil!", anonymous=False)
        assert ok is True
        assert len(state["news_bulletins"]) == 1
        assert state["players"][pids[1]]["last_news_post_round"] == 1

        state["player_points"] = {pids[0]: pids[1]}
        state["winner"] = "town"

        # Return to lobby
        state = return_to_lobby(state)

        # 1. State reset to lobby
        assert state["phase"] == "lobby"
        assert state["round_number"] == 0
        assert state["news_bulletins"] == []
        assert state["approved_news_bulletins"] == []
        assert state["player_points"] == {}
        assert state["players"][pids[1]]["last_news_post_round"] is None
        assert state["players"][pids[1]]["used_dead_news_bulletin"] is False

        # 2. Archive saved in game_history
        history = state.get("game_history", [])
        assert len(history) == 1
        entry = history[0]
        assert entry["game_number"] == 1
        assert entry["winner"] == "town"
        assert entry["rounds_played"] == 1
        assert len(entry["roster"]) == 4

    def test_witch_potions_limbo_revive_and_noop_when_dead(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            record_gm_night_action,
            resolve_night,
            set_manual_player_role,
            set_player_status,
        )

        state = create_initial_state("WITCH01", "Witch Limbo Revive Test")
        for name in ["WitchAlice", "LimboBob", "LivingCharlie", "WolfDave"]:
            state, _ = add_player(state, name)

        pids = list(state["players"].keys())
        w_id, l_id, c_id, wolf_id = pids[0], pids[1], pids[2], pids[3]
        set_manual_player_role(state, w_id, "witch")
        set_manual_player_role(state, l_id, "villager")
        set_manual_player_role(state, c_id, "villager")
        set_manual_player_role(state, wolf_id, "werewolf")

        # Put Bob in Limbo
        set_player_status(state, l_id, "limbo")
        assert state["players"][l_id]["status"] == "limbo"

        # 1. Alive Witch revives Bob from Limbo and poisons Charlie
        ok, msg = record_gm_night_action(
            state,
            "witch",
            extra={"revive_target": l_id, "kill_target": c_id},
        )
        assert ok is True
        state["phase"] = "night"
        state["round_number"] = 2
        state = resolve_night(state)

        # Bob is revived back to alive!
        assert state["players"][l_id]["status"] == "alive"
        # Charlie is poisoned!
        assert state["players"][c_id]["status"] in ("dead", "limbo")
        assert state["witch_used_revive"] is True
        assert state["witch_used_kill"] is True

        # 2. Dead Witch: actions are NOOP!
        state2 = create_initial_state("WITCH02", "Dead Witch Noop Test")
        for name in ["DeadWitch", "LimboSoul", "LivingPlayer", "LivingAngel"]:
            state2, _ = add_player(state2, name)
        pids2 = list(state2["players"].keys())
        dw_id, ls_id, lp_id, la_id = pids2[0], pids2[1], pids2[2], pids2[3]
        set_manual_player_role(state2, dw_id, "witch")
        set_manual_player_role(state2, la_id, "angel")
        set_player_status(state2, dw_id, "dead")
        set_player_status(state2, ls_id, "limbo")

        # GM enters witch targets even though witch is dead (bluffing/voice prompt)
        record_gm_night_action(
            state2,
            "witch",
            extra={"revive_target": ls_id, "kill_target": lp_id},
        )
        state2["phase"] = "night"
        state2["round_number"] = 2
        state2 = resolve_night(state2)

        # No-op: Limbo soul remains in limbo, living player remains alive!
        assert state2["players"][ls_id]["status"] == "limbo"
        assert state2["players"][lp_id]["status"] == "alive"
        assert state2["witch_used_revive"] is False
        assert state2["witch_used_kill"] is False

    def test_hacker_intel_announcement_and_activity_log(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            record_gm_night_action,
            resolve_night,
            set_manual_player_role,
        )

        state = create_initial_state("HACKRND2", "Hacker Intel Round 2 Test")
        for name in ["Hacker", "Wolf", "Villager1", "Villager2"]:
            state, _ = add_player(state, name)

        pids = list(state["players"].keys())
        set_manual_player_role(state, pids[0], "hacker")
        set_manual_player_role(state, pids[1], "werewolf")
        set_manual_player_role(state, pids[2], "villager")
        set_manual_player_role(state, pids[3], "villager")

        # Record hacker scan during night (even on Round 2)
        state["phase"] = "night"
        state["round_number"] = 2
        record_gm_night_action(state, "hacker", extra={"targets": [pids[1], pids[2], pids[3]]})

        state = resolve_night(state)

        # Hacker intel is announced in night_report and logged to events_log
        assert any("Hacker Intel:" in r for r in state["night_report"])
        assert any("Hacker scan revealed:" in e["message"] for e in state["events_log"])
        assert state["hacker_announced"] is True

        # Dawn report is fully logged in events_log
        assert any("--- Dawn Report" in e["message"] for e in state["events_log"])

    def test_witch_killed_tonight_powers_still_work_and_limbo_witch_noop(self):
        """If Witch is alive and killed tonight, her recorded potions still execute at dawn.
        If Witch is already in Limbo, her actions silently no-op."""
        from lupus.game_state import (
            add_player,
            create_initial_state,
            record_gm_night_action,
            resolve_night,
            set_manual_player_role,
            set_player_status,
        )

        # Part 1: Alive Witch attacked by Wolves tonight; her poison and limbo-revive still resolve!
        state = create_initial_state("WITCHKILL", "Witch Killed Tonight Test", settings={"limbo_enabled": False})
        for name in ["WitchAlice", "LimboBob", "TargetCharlie", "WolfDave"]:
            state, _ = add_player(state, name)

        pids = list(state["players"].keys())
        w_id, l_id, tc_id, wolf_id = pids[0], pids[1], pids[2], pids[3]
        set_manual_player_role(state, w_id, "witch")
        set_manual_player_role(state, l_id, "villager")
        set_manual_player_role(state, tc_id, "villager")
        set_manual_player_role(state, wolf_id, "werewolf")

        # Put Bob in Limbo
        set_player_status(state, l_id, "limbo")

        # Wolves attack Witch!
        record_gm_night_action(state, "wolves", w_id)
        # Witch revives Bob from Limbo and poisons Charlie!
        record_gm_night_action(
            state,
            "witch",
            extra={"revive_target": l_id, "kill_target": tc_id},
        )
        state["phase"] = "night"
        state["round_number"] = 2
        state = resolve_night(state)

        # Witch died from wolf attack
        assert state["players"][w_id]["status"] == "dead"
        # BUT LimboBob was revived back to alive!
        assert state["players"][l_id]["status"] == "alive"
        # AND TargetCharlie was killed by Witch's poison!
        assert state["players"][tc_id]["status"] == "dead"
        assert state["witch_used_revive"] is True
        assert state["witch_used_kill"] is True

        # Part 2: Witch already in Limbo at night start cannot act (silent no-op)
        state2 = create_initial_state("WITCHLIMBO", "Witch In Limbo Test", settings={"limbo_enabled": True})
        for name in ["LimboWitch", "LimboBob2", "LivingCharlie2", "AngelAlice"]:
            state2, _ = add_player(state2, name)

        pids2 = list(state2["players"].keys())
        lw_id, lb2_id, lc2_id, a_id = pids2[0], pids2[1], pids2[2], pids2[3]
        set_manual_player_role(state2, lw_id, "witch")
        set_manual_player_role(state2, lb2_id, "villager")
        set_manual_player_role(state2, lc2_id, "villager")
        set_manual_player_role(state2, a_id, "angel")

        set_player_status(state2, lw_id, "limbo")
        set_player_status(state2, lb2_id, "limbo")

        # GM enters actions for LimboWitch (bluffing call)
        record_gm_night_action(
            state2,
            "witch",
            extra={"revive_target": lb2_id, "kill_target": lc2_id},
        )
        state2["phase"] = "night"
        state2["round_number"] = 2
        state2 = resolve_night(state2)

        # Witch was in Limbo so potions do NOT execute
        assert state2["players"][lb2_id]["status"] == "limbo"
        assert state2["players"][lc2_id]["status"] == "alive"
        assert state2["witch_used_revive"] is False
        assert state2["witch_used_kill"] is False

    def test_action_history_recording_and_export_bundle(self):
        """Verify action tape recording on mutations and export bundle structure."""
        state = create_initial_state("ACTIONTAPE", "Action Tape Test Room")
        assert len(state["action_history"]) == 1
        assert state["action_history"][0]["action"] == "create_game"

        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")
        set_preassigned_role(state, p1["id"], "werewolf")
        set_preassigned_role(state, p2["id"], "villager")

        state = start_game(state)
        # Advance to round 1
        state["is_night_zero"] = False
        state["round_number"] = 1

        record_gm_night_action(state, "wolves", p2["id"])
        state = resolve_night(state)

        # Verify action history tracked sequence
        actions = [a["action"] for a in state["action_history"]]
        assert "create_game" in actions
        assert "player_joined" in actions
        assert "set_preassigned_role" in actions
        assert "start_game" in actions
        assert "night_action" in actions
        assert "resolve_night" in actions

        # Verify GM view contains action history
        gm_view = get_gm_view(state)
        assert "action_history" in gm_view
        assert len(gm_view["action_history"]) == len(state["action_history"])

        # Verify exported replay bundle
        bundle = export_game_replay(state)
        assert bundle["code"] == "ACTIONTAPE"
        assert bundle["version"] is not None
        assert bundle["summary"]["rounds_played"] == 1
        assert len(bundle["players"]) == 2
        assert len(bundle["action_history"]) == len(state["action_history"])


class TestLupusRoomLifecycleAndPortugueseDemo:
    """Tests for Open/Running/Finished room lifecycle, title incrementing, lobby forwarding,
    and Portuguese 22-role demo room."""

    def test_increment_room_title(self):
        from lupus.game_state import increment_room_title

        assert increment_room_title("someones birthday") == "someones birthday 2"
        assert increment_room_title("someones birthday 2") == "someones birthday 3"
        assert increment_room_title("someones birthday 3") == "someones birthday 4"
        assert increment_room_title("someones birthday 99") == "someones birthday 100"
        assert increment_room_title("Game 1") == "Game 2"
        assert increment_room_title("Lupus Room ABCD") == "Lupus Room ABCD 2"
        assert increment_room_title("Lupus Room ABCD 2") == "Lupus Room ABCD 3"
        assert increment_room_title("") == "Lupus Room 2"
        assert increment_room_title(None) == "Lupus Room 2"

    @pytest.mark.django_db
    def test_room_status_transitions(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            start_game,
            trigger_game_over,
        )

        room = Room.objects.create(code="CYCLE01", title="Lifecycle Test", game_type="lupus")
        state = create_initial_state(room.code, room.title)
        assert state["status"] == "open"

        state, _ = add_player(state, "Alice")
        state, _ = add_player(state, "Bob")
        state = start_game(state, ["werewolf", "villager"])
        assert state["status"] == "running"
        room.refresh_from_db()
        assert room.status == "running"

        state = trigger_game_over(state, "town")
        assert state["status"] == "finished"
        room.refresh_from_db()
        assert room.status == "finished"

    @pytest.mark.django_db
    def test_create_next_game_lobby_moves_players_and_increments_title(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            create_next_game_lobby,
            reorder_players,
            start_game,
            trigger_game_over,
        )

        old_room = Room.objects.create(code="PARTY01", title="Marco's Birthday", game_type="lupus")
        state = create_initial_state(old_room.code, old_room.title, gm_token="SECRET_GM_TOKEN", gm_name="Marco GM")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")
        reorder_players(state, [p2["id"], p1["id"]])

        # Play a round and finish
        state = start_game(state, ["werewolf", "villager"])
        state = trigger_game_over(state, "town")
        assert state["status"] == "finished"

        # GM creates next game lobby
        new_state = create_next_game_lobby(state)

        # 1. Old state was marked finished and holds pointer
        assert state["status"] == "finished"
        assert state["next_room_code"] == new_state["code"]
        old_room.refresh_from_db()
        assert old_room.status == "finished"

        # 2. New state has incremented title and open status
        assert new_state["title"] == "Marco's Birthday 2"
        assert new_state["status"] == "open"
        assert new_state["phase"] == "lobby"
        assert new_state["previous_room_code"] == "PARTY01"
        assert new_state["gm_token"] == "SECRET_GM_TOKEN"

        # 3. All players preserved with tokens and seating order
        assert len(new_state["players"]) == 2
        assert p1["id"] in new_state["players"]
        assert p2["id"] in new_state["players"]
        assert new_state["players"][p1["id"]]["token"] == p1["token"]
        assert new_state["players"][p2["id"]]["token"] == p2["token"]
        assert new_state["players"][p1["id"]]["role"] is None
        assert new_state["players"][p1["id"]]["status"] == "alive"
        assert new_state["player_order"] == [p2["id"], p1["id"]]

        # 4. Repeating again increments to 3
        third_state = create_next_game_lobby(new_state)
        assert third_state["title"] == "Marco's Birthday 3"
        assert third_state["status"] == "open"
        assert third_state["previous_room_code"] == new_state["code"]

    def test_demo_room_populates_portuguese_roles(self):
        from lupus.game_state import (
            DEMO_PLAYERS,
            create_initial_state,
            setup_demo_room,
        )

        state = create_initial_state("DEMO25", "Demo Test")
        state = setup_demo_room(state)

        assert len(state["players"]) == len(DEMO_PLAYERS)
        assert len(state["deck"]) == len(DEMO_PLAYERS)
        assert len(DEMO_PLAYERS) == 25

        roles_assigned = {p["role"] for p in state["players"].values()}
        assert "werewolf" in roles_assigned
        assert "alpha_wolf" in roles_assigned
        assert "framer" in roles_assigned
        assert "detective" in roles_assigned
        assert "doctor" in roles_assigned
        assert "bodyguard" in roles_assigned
        assert "angel" in roles_assigned
        assert "death_angel" in roles_assigned
        assert "sniper" in roles_assigned
        assert "mayor" in roles_assigned
        assert "witch" in roles_assigned
        assert "lover" in roles_assigned
        assert "cupid" in roles_assigned
        assert "jester" in roles_assigned
        assert "serial_killer" in roles_assigned
        assert "wolf_hunter" in roles_assigned
        assert "hacker" in roles_assigned
        assert "wolf_cub" in roles_assigned
        assert "martyrdom" in roles_assigned
        assert "gull" in roles_assigned
        assert "villager" in roles_assigned

        player_names = {p["name"] for p in state["players"].values()}
        assert "Lobisomem" in player_names
        assert "Lobo Alfa" in player_names
        assert "Incriminador" in player_names
        assert "Vidente" in player_names
        assert "Médico" in player_names
        assert "Guarda-Costas" in player_names
        assert "Anjo" in player_names
        assert "Anjo da Morte" in player_names
        assert "Vigilante" in player_names
        assert "Presidente" in player_names
        assert "Bruxa" in player_names
        assert "Amante 1" in player_names
        assert "Amante 2" in player_names
        assert "Cupido" in player_names
        assert "Bobo da Corte" in player_names
        assert "Assassino em Série" in player_names
        assert "Caçador de Lobos" in player_names
        assert "Hacker" in player_names
        assert "Filhote de Lobo" in player_names
        assert "Mártir" in player_names
        assert "O Pato" in player_names
        assert "Aldeão" in player_names

    @pytest.mark.django_db
    def test_view_redirects_when_next_room_code_present(self, client):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            create_next_game_lobby,
        )

        old_room = Room.objects.create(code="OLDROOM1", title="Room Old", game_type="lupus")
        state = create_initial_state(old_room.code, old_room.title, gm_token="GM_TOK_123")
        state, player = add_player(state, "TestPlayer")

        new_state = create_next_game_lobby(state)
        new_code = new_state["code"]

        # 1. Player visiting old room play url is redirected to new room play url
        old_play_url = (
            f"{reverse('gamerooms:lupus:play', kwargs={'code': 'OLDROOM1'})}?token={player['token']}&pid={player['id']}"
        )
        res = client.get(old_play_url)
        assert res.status_code == 302
        assert f"/games/lupus/{new_code}/play/" in res.url
        assert player["token"] in res.url

        # 2. Player visiting old join url is redirected to new room join url
        old_join_url = reverse("gamerooms:lupus:join", kwargs={"code": "OLDROOM1"})
        res = client.get(old_join_url)
        assert res.status_code == 302
        assert f"/games/lupus/{new_code}/join/" in res.url

        # 3. GM visiting old dashboard url is redirected to new dashboard url
        old_gm_url = f"{reverse('gamerooms:lupus:gm', kwargs={'code': 'OLDROOM1'})}?gm_token=GM_TOK_123"
        res = client.get(old_gm_url)
        assert res.status_code == 302
        assert f"/games/lupus/{new_code}/gm/" in res.url
        assert "GM_TOK_123" in res.url

        # 4. GM visiting with ?stay=1 stays on old dashboard
        stay_gm_url = f"{reverse('gamerooms:lupus:gm', kwargs={'code': 'OLDROOM1'})}?gm_token=GM_TOK_123&stay=1"
        res = client.get(stay_gm_url)
        assert res.status_code == 200

    def test_wolf_cub_rampage_double_kill(self):
        """When Wolf Cub dies, wolf_cub_rampage becomes active and wolves hunt two victims."""
        state = create_initial_state("TESTCUB", "Test Cub")
        state["settings"]["limbo_enabled"] = False
        state, p_wolf = add_player(state, "Alpha")
        state, p_cub = add_player(state, "LittleCub")
        state, p_v1 = add_player(state, "Villager1")
        state, p_v2 = add_player(state, "Villager2")
        state, p_v3 = add_player(state, "Villager3")

        p_wolf["role"] = "werewolf"
        p_wolf["faction"] = "wolves"
        p_cub["role"] = "wolf_cub"
        p_cub["faction"] = "wolves"
        p_v1["role"] = "villager"
        p_v1["faction"] = "town"
        p_v2["role"] = "villager"
        p_v2["faction"] = "town"
        p_v3["role"] = "villager"
        p_v3["faction"] = "town"

        assert state.get("wolf_cub_rampage") is False

        # Wolf Cub dies
        set_player_status(state, p_cub["id"], "dead")
        assert state["wolf_cub_rampage"] is True

        # Advance to night
        state["phase"] = "night"
        stages = get_night_stages(state)
        wolf_stage = next(s for s in stages if s["id"] == "wolves")
        assert wolf_stage["wolf_cub_rampage"] is True
        assert wolf_stage["requires_two_targets"] is True
        assert "Rampage (2 Kills Tonight!)" in wolf_stage["title"]

        # Wolves select 2 victims
        record_gm_night_action(state, "wolves", target_id=p_v1["id"], extra={"target_id_2": p_v2["id"]})
        assert state["night_actions"]["wolf_target"] == p_v1["id"]
        assert state["night_actions"]["wolf_target_2"] == p_v2["id"]

        # Resolve night
        resolve_night(state)
        assert state["players"][p_v1["id"]]["status"] == "dead"
        assert state["players"][p_v2["id"]]["status"] == "dead"
        assert state["players"][p_v3["id"]]["status"] == "alive"
        # Rampage is consumed
        assert state["wolf_cub_rampage"] is False

    def test_martyrdom_revenge_grenade(self):
        """When Martyrdom dies, their live grenade takes down their primed victim."""
        state = create_initial_state("TESTMARTYR", "Test Martyr")
        state["settings"]["limbo_enabled"] = False
        state, p_martyr = add_player(state, "Soldier")
        state, p_wolf = add_player(state, "BadWolf")
        state, p_villager = add_player(state, "GoodGuy")

        p_martyr["role"] = "martyrdom"
        p_martyr["faction"] = "town"
        p_wolf["role"] = "werewolf"
        p_wolf["faction"] = "wolves"
        p_villager["role"] = "villager"
        p_villager["faction"] = "town"

        # Soldier primes grenade on BadWolf
        ok, msg = set_martyrdom_target(state, p_martyr["id"], p_wolf["id"])
        assert ok is True
        assert p_martyr["martyrdom_target_id"] == p_wolf["id"]

        # Soldier is lynched / killed
        set_player_status(state, p_martyr["id"], "dead")
        assert p_martyr["status"] == "dead"
        # Revenge grenade blew up BadWolf!
        assert state["players"][p_wolf["id"]]["status"] == "dead"
        assert state["players"][p_villager["id"]]["status"] == "alive"

        # Test manual detonation when killed without primed target
        state2 = create_initial_state("TESTMARTYR2", "Test Martyr 2")
        state2["settings"]["limbo_enabled"] = False
        state2, m2 = add_player(state2, "Soldier2")
        state2, w2 = add_player(state2, "Wolf2")
        m2["role"] = "martyrdom"
        m2["faction"] = "town"
        w2["role"] = "werewolf"
        w2["faction"] = "wolves"

        set_player_status(state2, m2["id"], "dead")
        assert state2.get("pending_martyrdom_player_id") == m2["id"]
        assert state2["players"][w2["id"]]["status"] == "alive"

        # Detonate live grenade manually
        ok2, msg2 = trigger_martyrdom_detonation(state2, m2["id"], w2["id"])
        assert ok2 is True
        assert state2["players"][w2["id"]]["status"] == "dead"
        assert state2.get("pending_martyrdom_player_id") is None

    def test_martyrdom_hidden_variety_night_trap(self):
        """Hidden Martyrdom does not detonate on death, but wakes up on next night to trap their victim."""
        from lupus.game_state import (
            advance_to_night,
            get_night_stages,
            resolve_night,
        )

        state = create_initial_state(
            "TESTHIDMARTYR",
            "Hidden Martyr Room",
            settings={"martyrdom_type": "hidden", "limbo_enabled": False},
        )
        state, p_martyr = add_player(state, "StealthSoldier")
        state, p_wolf = add_player(state, "BadWolf")
        state, p_doc = add_player(state, "Doctor")
        state, p_villager = add_player(state, "GoodGuy")

        p_martyr["role"] = "martyrdom"
        p_martyr["faction"] = "town"
        p_martyr["is_public_martyrdom"] = False
        p_wolf["role"] = "werewolf"
        p_wolf["faction"] = "wolves"
        p_doc["role"] = "doctor"
        p_doc["faction"] = "town"
        p_villager["role"] = "villager"
        p_villager["faction"] = "town"

        # 1. Before death: Night stages show Martyrdom stage with is_alive=False (bluff pause)
        advance_to_night(state)
        stages = get_night_stages(state)
        m_stage = next((s for s in stages if s["id"] == "martyrdom"), None)
        assert m_stage is not None
        assert m_stage["is_alive"] is False  # Not dead yet: GM bluffs for 5-10s

        # Resolve peaceful night 1
        resolve_night(state)

        # 2. Daytime: StealthSoldier is eliminated by town execution
        set_player_status(state, p_martyr["id"], "dead")
        assert p_martyr["status"] == "dead"
        # In hidden variety: NO instant explosion, NO pending_martyrdom_player_id
        assert state.get("pending_martyrdom_player_id") is None
        assert state["players"][p_wolf["id"]]["status"] == "alive"
        # Secret pending flag is active
        assert p_martyr["pending_hidden_martyrdom"] is True

        # 3. Night 2: StealthSoldier is called in secret to designate their revenge trap
        advance_to_night(state)
        stages2 = get_night_stages(state)
        m_stage2 = next((s for s in stages2 if s["id"] == "martyrdom"), None)
        assert m_stage2 is not None
        assert m_stage2["is_alive"] is True  # Active! Pending revenge

        # Deceased soldier can pick their revenge target in secret
        ok, msg = set_martyrdom_target(state, p_martyr["id"], p_wolf["id"])
        assert ok is True
        assert state["night_actions"]["martyrdom_target"] == p_wolf["id"]

        # 4. Night 2 resolves at dawn: Booby trap explodes and eliminates BadWolf!
        resolve_night(state)
        assert state["players"][p_wolf["id"]]["status"] == "dead"
        assert any("explosive booby trap" in line for line in state["night_report"])
        # Revenge window is closed
        assert p_martyr["pending_hidden_martyrdom"] is False
        assert p_martyr["used_hidden_martyrdom"] is True

        # 5. Night 3: Martyrdom is called again for bluffing, but is_alive is False
        advance_to_night(state)
        stages3 = get_night_stages(state)
        m_stage3 = next((s for s in stages3 if s["id"] == "martyrdom"), None)
        assert m_stage3 is not None
        assert m_stage3["is_alive"] is False  # Window expired: bluff pause only

    def test_martyrdom_hidden_doctor_protection(self):
        """If Doctor protects the target of hidden Martyrdom booby trap, target survives."""
        from lupus.game_state import (
            advance_to_night,
            record_gm_night_action,
            resolve_night,
        )

        state = create_initial_state(
            "TESTHIDDOC",
            "Hidden Martyr Doc Room",
            settings={"martyrdom_type": "hidden", "limbo_enabled": False},
        )
        state, p_martyr = add_player(state, "Martyr")
        state, p_wolf = add_player(state, "Wolf")
        state, p_doc = add_player(state, "Doc")

        p_martyr["role"] = "martyrdom"
        p_martyr["faction"] = "town"
        p_martyr["is_public_martyrdom"] = False
        p_wolf["role"] = "werewolf"
        p_wolf["faction"] = "wolves"
        p_doc["role"] = "doctor"
        p_doc["faction"] = "town"

        # Martyr dies
        set_player_status(state, p_martyr["id"], "dead")
        assert p_martyr["pending_hidden_martyrdom"] is True

        # Night falls
        advance_to_night(state)
        # Martyr targets Wolf with booby trap
        record_gm_night_action(state, "martyrdom", target_id=p_wolf["id"])
        # Doctor protects Wolf
        record_gm_night_action(state, "doctor", target_id=p_wolf["id"])

        resolve_night(state)
        # Protected! Wolf survives!
        assert state["players"][p_wolf["id"]]["status"] == "alive"

    def test_gull_wolf_bite_conversion(self):
        """When The Gull is attacked by wolves without Doctor protection, they survive and convert to Werewolf."""
        from lupus.game_state import is_evil_for_detective

        state = create_initial_state("TESTGULL", "Test Gull")
        state["settings"]["limbo_enabled"] = False
        state, p_wolf = add_player(state, "Wolf")
        state, p_gull = add_player(state, "NaiveGull")
        state, p_doc = add_player(state, "Medic")

        p_wolf["role"] = "werewolf"
        p_wolf["faction"] = "wolves"
        p_gull["role"] = "gull"
        p_gull["faction"] = "town"
        p_doc["role"] = "doctor"
        p_doc["faction"] = "town"

        # Detective inspection before bite: Good
        assert is_evil_for_detective(p_gull) is False

        # Wolves attack The Gull without Doctor protect
        state["phase"] = "night"
        record_gm_night_action(state, "wolves", target_id=p_gull["id"])
        resolve_night(state)

        # The Gull survives and converts to Werewolf
        assert p_gull["status"] == "alive"
        assert p_gull["faction"] == "wolves"
        assert p_gull["gull_converted"] is True

        # Detective inspection after bite: Evil
        assert is_evil_for_detective(p_gull) is True

        # Test Doctor protect prevents bite/conversion
        state2 = create_initial_state("TESTGULL2", "Test Gull Protected")
        state2["settings"]["limbo_enabled"] = False
        state2, w2 = add_player(state2, "Wolf2")
        state2, g2 = add_player(state2, "Gull2")
        state2, d2 = add_player(state2, "Medic2")

        w2["role"] = "werewolf"
        w2["faction"] = "wolves"
        g2["role"] = "gull"
        g2["faction"] = "town"
        d2["role"] = "doctor"
        d2["faction"] = "town"

        state2["phase"] = "night"
        record_gm_night_action(state2, "doctor", target_id=g2["id"])
        record_gm_night_action(state2, "wolves", target_id=g2["id"])
        resolve_night(state2)

        # Protected by Doctor: stays town, alive, not converted
        assert g2["status"] == "alive"
        assert g2["faction"] == "town"
        assert g2["gull_converted"] is False
        assert is_evil_for_detective(g2) is False


class TestMidgameJoinerAndNearGameoverEdgeCases:
    def test_midgame_unassigned_joiner_does_not_break_wolf_parity(self):
        """A spectator joining mid-game without a role starts as 'waiting' and does not disrupt wolf parity."""
        state = create_initial_state("TESTMID1", "Test Midgame Joiner")
        state, w1 = add_player(state, "Wolf1")
        state, w2 = add_player(state, "Wolf2")
        state, v1 = add_player(state, "Villager1")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        w2["role"] = "werewolf"
        w2["faction"] = "wolves"
        v1["role"] = "villager"
        v1["faction"] = "town"

        state["phase"] = "night"
        state["status"] = "running"

        # 2 wolves vs 1 villager -> Wolf parity win condition met
        winner = check_win_condition(state)
        assert winner == "wolves"
        assert state.get("pending_gameover", {}).get("winner") == "wolves"

        # Late spectator joins mid-game
        state, late = add_player(state, "SpectatorLate")
        assert late["status"] == "waiting"
        assert late["role"] is None
        assert late["faction"] is None

        # Verify living players still only counts active alive players
        living = get_living_players(state)
        assert len(living) == 3
        assert late["id"] not in [p["id"] for p in living]

        # Verify wolf parity remains intact despite spectator presence
        winner = check_win_condition(state)
        assert winner == "wolves"

    def test_traveler_midgame_assignment_reverses_pending_wolf_win(self):
        """Assigning a Traveler mid-game adds a living Town member and clears pending wolf victory."""
        state = create_initial_state("TESTMID2", "Test Traveler Reversal")
        state, w1 = add_player(state, "Wolf1")
        state, w2 = add_player(state, "Wolf2")
        state, v1 = add_player(state, "Villager1")
        state, v2 = add_player(state, "Villager2")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        w2["role"] = "werewolf"
        w2["faction"] = "wolves"
        v1["role"] = "villager"
        v1["faction"] = "town"
        v2["role"] = "villager"
        v2["faction"] = "town"

        state["phase"] = "day"
        state["status"] = "running"

        # 2 wolves vs 2 villagers -> Parity reached (2 >= 4 - 2)
        winner = check_win_condition(state)
        assert winner == "wolves"
        assert state.get("pending_gameover") is not None

        # Late joiner enters mid-game and is assigned Traveler
        state, late = add_player(state, "TravelerJoiner")
        success, msg = assign_midgame_role(state, late["id"], "traveler")
        assert success
        assert late["status"] == "alive"
        assert late["faction"] == "town"
        assert late["is_traveler"] is True

        # Now 2 wolves vs 3 town -> Wolf parity is broken!
        assert state.get("pending_gameover") is None
        assert check_win_condition(state) is None
        assert len(get_living_players(state)) == 5

    def test_successor_inherits_last_werewolf_preventing_premature_town_win(self):
        """When the last werewolf is executed, a waiting Successor inherits the role and averts Town victory."""
        state = create_initial_state("TESTMID3", "Test Successor Last Wolf")
        state["settings"]["limbo_enabled"] = False
        state, w1 = add_player(state, "AlphaWolf")
        state, v1 = add_player(state, "Villager1")
        state, v2 = add_player(state, "Villager2")
        state, succ = add_player(state, "Understudy")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        v1["role"] = "villager"
        v1["faction"] = "town"
        v2["role"] = "villager"
        v2["faction"] = "town"

        state["phase"] = "day"
        state["status"] = "running"

        # Assign understudy as Successor
        assign_midgame_role(state, succ["id"], "successor")
        assert succ["status"] == "waiting"
        assert succ["role"] == "successor"

        # Town executes AlphaWolf by day vote
        start_voting_session(state)
        toggle_official_nomination(state, w1["id"])
        proceed_to_final_vote(state)
        cast_final_vote(state, v1["id"], w1["id"])
        cast_final_vote(state, v2["id"], w1["id"])
        res, msg = tally_and_resolve_vote(state)
        assert res == "eliminated"

        # Verify AlphaWolf is dead
        assert w1["status"] == "dead"

        # Verify Successor inherited Werewolf role and became alive!
        assert succ["status"] == "alive"
        assert succ["role"] == "werewolf"
        assert succ["faction"] == "wolves"
        assert succ["inherited_from_name"] == "AlphaWolf"

        # Verify Town does NOT win because the pack lives on through the Successor
        assert state.get("pending_gameover") is None
        assert check_win_condition(state) is None

    def test_successor_inherits_werewolf_from_serial_killer_night_kill(self):
        """Serial Killer killing the last werewolf does not trigger instant solo win if Successor inherits."""
        state = create_initial_state("TESTMID4", "Test SK vs Successor")
        state["settings"]["limbo_enabled"] = False
        state, w1 = add_player(state, "LoneWolf")
        state, sk = add_player(state, "Dexter")
        state, v1 = add_player(state, "Villager1")
        state, succ = add_player(state, "Understudy")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        sk["role"] = "serial_killer"
        sk["faction"] = "evil"
        v1["role"] = "villager"
        v1["faction"] = "town"

        state["phase"] = "night"
        state["status"] = "running"
        assign_midgame_role(state, succ["id"], "successor")

        # Serial Killer strikes LoneWolf at night
        record_gm_night_action(state, "serial_killer", target_id=w1["id"])
        resolve_night(state)

        # LoneWolf is dead, but Successor inherited the Werewolf role
        assert w1["status"] == "dead"
        assert succ["status"] == "alive"
        assert succ["role"] == "werewolf"
        assert succ["faction"] == "wolves"

        # SK does not win solo victory because wolves faction is still alive
        assert state.get("pending_gameover") is None
        assert check_win_condition(state) is None

    def test_successor_saves_obsessive_lovers_to_trigger_lovers_win(self):
        """Successor inherits fallen Lover, averts heartbreak, and enables 2-survivor Lovers victory."""
        state = create_initial_state("TESTMID5", "Test Successor Lovers Win")
        state["settings"]["limbo_enabled"] = False
        state, r = add_player(state, "Romeo")
        state, j = add_player(state, "Juliet")
        state, w = add_player(state, "BigBadWolf")
        state, succ = add_player(state, "Paris")

        r["role"] = "villager"
        r["faction"] = "town"
        j["role"] = "villager"
        j["faction"] = "town"
        w["role"] = "werewolf"
        w["faction"] = "wolves"

        r["lover_id"] = j["id"]
        r["lover_type"] = "obsessive"
        j["lover_id"] = r["id"]
        j["lover_type"] = "obsessive"
        assign_midgame_role(state, succ["id"], "successor")

        state["phase"] = "night"
        state["status"] = "running"

        # Wolves attack Romeo, but Wolf is eliminated simultaneously by a night kill (e.g. status dead)
        set_player_status(state, r["id"], "dead")
        set_player_status(state, w["id"], "dead")

        # Romeo died, but Paris stepped in as Successor, inheriting Romeo and becoming Juliet's new lover!
        assert succ["status"] == "alive"
        assert succ["lover_id"] == j["id"]
        assert j["lover_id"] == succ["id"]
        assert j["status"] == "alive"
        assert succ["lover_type"] == "obsessive"

        # The only 2 living players left are Paris and Juliet (Obsessive Lovers)!
        winner = check_win_condition(state)
        assert winner == "lovers"
        assert state.get("pending_gameover", {}).get("winner") == "lovers"

    def test_ghost_and_disgruntled_ghost_midgame_do_not_affect_alive_counts(self):
        """Ghosts join with status 'dead' and do not disturb alive counts or wolf parity."""
        state = create_initial_state("TESTMID6", "Test Spectral Ghosts")
        state, w1 = add_player(state, "Wolf1")
        state, v1 = add_player(state, "Villager1")
        state, v2 = add_player(state, "Villager2")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        v1["role"] = "villager"
        v1["faction"] = "town"
        v2["role"] = "villager"
        v2["faction"] = "town"

        state["phase"] = "day"
        state["status"] = "running"

        # Late joiners enter as Ghosts
        state, g1 = add_player(state, "Casper")
        state, g2 = add_player(state, "Poltergeist")

        assign_midgame_role(state, g1["id"], "ghost")
        assign_midgame_role(state, g2["id"], "disgruntled_ghost")

        assert g1["status"] == "dead"
        assert g1["is_ghost"] is True
        assert g2["status"] == "dead"

        # Living players count remains 3
        living = get_living_players(state)
        assert len(living) == 3
        assert g1["id"] not in [p["id"] for p in living]
        assert g2["id"] not in [p["id"] for p in living]

    def test_midgame_joiner_after_gameover_does_not_mutate_winner(self):
        """Joining or assigning roles after GameOver preserves finished status and recorded winner."""
        state = create_initial_state("TESTMID7", "Test Post GameOver")
        state, w1 = add_player(state, "Wolf1")
        state, v1 = add_player(state, "Villager1")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        v1["role"] = "villager"
        v1["faction"] = "town"

        trigger_game_over(state, "wolves")
        assert state["phase"] == "gameover"
        assert state["status"] == "finished"
        assert state["winner"] == "wolves"

        # Late player joins and tries to take a town role
        state, late = add_player(state, "LateArrival")
        assign_midgame_role(state, late["id"], "traveler")

        # Concluded game status and winner are strictly maintained
        assert state["phase"] == "gameover"
        assert state["status"] == "finished"
        assert state["winner"] == "wolves"

    def test_late_joiner_assigned_standard_town_role_activates_alive(self):
        """A mid-game joiner assigned a standard role (e.g. Villager) becomes alive and can participate."""
        state = create_initial_state("TESTMID8", "Test Standard Midgame Role")
        state, w1 = add_player(state, "Wolf1")
        state, v1 = add_player(state, "Villager1")

        w1["role"] = "werewolf"
        w1["faction"] = "wolves"
        v1["role"] = "villager"
        v1["faction"] = "town"

        state["phase"] = "day"
        state["status"] = "running"

        state, late = add_player(state, "LateCitizen")
        assert late["status"] == "waiting"

        success, msg = assign_midgame_role(state, late["id"], "villager")
        assert success
        assert late["status"] == "alive"
        assert late["faction"] == "town"
        assert late["id"] in [p["id"] for p in get_living_players(state)]


class TestLupusInternationalization:
    """Validate internationalization (i18n) across supported languages and verify engine English invariance."""

    def test_engine_invariance_rules_and_state_stay_canonical_english(self):
        """Internal game state, factions, roles, and phases remain 100% in English."""
        state = create_initial_state("I18N01", "Engine Invariance Test")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")

        p1["role"] = "werewolf"
        p1["faction"] = "wolves"
        p1["status"] = "alive"

        p2["role"] = "detective"
        p2["faction"] = "town"
        p2["status"] = "alive"

        state["phase"] = "night"
        state["status"] = "running"

        # Assert internal engine fields are canonical English
        assert state["players"][p1["id"]]["role"] == "werewolf"
        assert state["players"][p1["id"]]["faction"] == "wolves"
        assert state["players"][p1["id"]]["status"] == "alive"
        assert state["players"][p2["id"]]["role"] == "detective"
        assert state["players"][p2["id"]]["faction"] == "town"
        assert state["phase"] == "night"
        assert state["status"] == "running"

    def test_presentation_boundary_role_localization_all_9_languages(self):
        """get_role_info returns localized display name and guide while preserving engine id and faction."""
        from lupus.roles import get_role_info

        expected_names = {
            "en": "Werewolf",
            "pt": "Lobisomem",
            "it": "Lupo Mannaro",
            "es": "Hombre Lobo",
            "fr": "Loup-Garou",
            "el": "Λυκάνθρωπος",
            "ru": "Оборотень",
            "hi": "भेड़िया",
            "kn": "ತೋಳ",
        }

        for lang, expected_name in expected_names.items():
            info = get_role_info("werewolf", lang=lang)
            assert info["name"] == expected_name, f"Failed for {lang}: got {info['name']}"
            assert info["id"] == "werewolf"
            assert info["faction"] == "wolves"
            assert "objective" in info["guide"]

    def test_status_phase_and_faction_translation_lookups(self):
        """Localized helper functions correctly translate statuses, phases, and factions."""
        from lupus.translations import (
            get_localized_faction,
            get_localized_phase,
            get_localized_status,
            get_localized_ui_strings,
        )

        # Status translations
        assert get_localized_status("alive", lang="pt") == "Vivo"
        assert get_localized_status("dead", lang="it") == "Morto"
        assert get_localized_status("limbo", lang="ru") == "В лимбе"
        assert get_localized_status("spectator", lang="es") == "Espectador"

        # Phase translations
        assert get_localized_phase("night", lang="es") == "Noche"
        assert get_localized_phase("day_voting", lang="fr") == "Vote du Jour"
        assert get_localized_phase("gameover", lang="pt") == "Fim de Jogo"

        # Faction translations
        assert get_localized_faction("wolves", lang="kn") == "ತೋಳಗಳು / ಮಾಫಿಯಾ"
        assert get_localized_faction("town", lang="el") == "Χωρικοί / Χωριό"

        # UI strings
        pt_ui = get_localized_ui_strings(lang="pt")
        assert pt_ui["hold_to_peek"] == "Segure para espiar o papel secreto"
        assert pt_ui["release_to_hide"] == "Solte para esconder de olhares curiosos"

        it_ui = get_localized_ui_strings(lang="it")
        assert it_ui["hold_to_peek"] == "Tieni premuto per vedere il ruolo segreto"

    def test_sanitized_player_view_localized_presentation(self):
        """get_sanitized_player_view includes localized status_display, phase_display, and ui_strings."""
        from lupus.game_state import get_sanitized_player_view

        state = create_initial_state("I18N02", "Player View Test")
        state, p1 = add_player(state, "Carlos")
        p1["role"] = "doctor"
        p1["faction"] = "town"
        p1["status"] = "alive"
        state["phase"] = "night"

        # Request Portuguese view
        view_pt = get_sanitized_player_view(state, p1["id"], lang="pt")
        assert view_pt["lang"] == "pt"
        assert view_pt["phase_display"] == "Noite"
        assert view_pt["phase"] == "night"  # Engine phase preserved
        assert view_pt["me"]["status_display"] == "Vivo"
        assert view_pt["me"]["status"] == "alive"  # Engine status preserved
        assert view_pt["me"]["role"]["name"] == "Médico"
        assert view_pt["ui_strings"]["hold_to_peek"] == "Segure para espiar o papel secreto"

        # Engine state itself untouched
        assert state["players"][p1["id"]]["status"] == "alive"
        assert state["phase"] == "night"

    def test_all_29_roles_have_complete_translations_for_all_supported_languages(self):
        """Verify that every single role in ROLE_REGISTRY has valid translations across all 9 languages."""
        from lupus.roles import ROLE_REGISTRY, get_role_info
        from lupus.translations import SUPPORTED_LANGUAGES

        assert len(ROLE_REGISTRY) >= 29

        for role_id in ROLE_REGISTRY:
            for lang in SUPPORTED_LANGUAGES:
                info = get_role_info(role_id, lang=lang)
                assert info["name"], f"Role {role_id} missing name in {lang}"
                assert info["description"], f"Role {role_id} missing description in {lang}"
                assert "objective" in info["guide"], f"Role {role_id} missing objective in {lang}"


class TestLupusV129HackerDeckAndScan:
    def test_deck_builder_and_manual_modal_contain_all_roles(self):
        """Verify that gm_dashboard.html has toggle chips and widgets for hacker, watson, and saboteur_wolf."""
        import os

        from django.conf import settings

        tpl_path = os.path.join(settings.BASE_DIR, "templates", "lupus", "gm_dashboard.html")
        with open(tpl_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Deck builder toggle chips
        assert 'id="chip-hacker"' in html
        assert 'id="badge-hacker"' in html
        assert 'id="chip-watson"' in html
        assert 'id="badge-watson"' in html
        assert 'id="chip-saboteur_wolf"' in html
        assert 'id="badge-saboteur_wolf"' in html

        # Manual role modal buttons
        assert 'data-role="wolf_cub"' in html
        assert 'data-role="martyrdom"' in html
        assert 'data-role="gull"' in html
        assert 'data-role="hacker"' in html
        assert 'data-role="watson"' in html
        assert 'data-role="saboteur_wolf"' in html

        # Hacker scan night widget
        assert 'id="hacker-widget"' in html
        assert 'id="hacker-player-toggles"' in html
        assert 'id="hacker-result-preview-box"' in html

    def test_hacker_deal_and_scan_evil_ratio_and_day_voting_block(self):
        """Verify Hacker dealing blocks Day 1 voting, and scan evaluates evil ratios accurately."""
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_night_stages,
            record_gm_night_action,
            resolve_night,
            start_game,
            start_voting_session,
        )

        state = create_initial_state("HACK01", "Hacker Full Cycle Test")
        for name in ["Alice", "Bob", "Charlie", "Dave"]:
            state, _ = add_player(state, name)

        roles = ["hacker", "werewolf", "serial_killer", "villager"]
        state = start_game(state, role_list=roles)

        assert state["day1_no_voting"] is True

        # Night 0 stages
        stages = get_night_stages(state)
        hacker_stage = next((s for s in stages if s["id"] == "hacker"), None)
        assert hacker_stage is not None

        wolf_p = next(p for p in state["players"].values() if p["role"] == "werewolf")
        sk_p = next(p for p in state["players"].values() if p["role"] == "serial_killer")

        # Scan Wolf and Serial Killer -> Both Evil -> "All Evil"
        record_gm_night_action(state, "hacker", wolf_p["id"])
        record_gm_night_action(state, "hacker", sk_p["id"])
        assert set(state["night_actions"]["hacker_targets"]) == {wolf_p["id"], sk_p["id"]}

        # Resolve Night 0 into Day 0
        state = resolve_night(state)
        assert state["hacker_result"] == "All Evil"
        assert state["hacker_evil_count"] == 2
        assert state["hacker_total_count"] == 2
        assert state["hacker_announced"] is True

        # Day 0 voting is blocked
        voting_state = start_voting_session(state)
        assert voting_state.get("phase") != "day_voting"

    def test_mayor_self_pardon_veto_when_executed(self):
        """When Mayor is executed by day vote, they can exercise executive veto during night to revive themselves."""
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_night_stages,
            record_gm_night_action,
            resolve_night,
            set_player_status,
            start_game,
        )

        state = create_initial_state("MAYOR_TEST", "Mayor Pardon Room")
        for name in ["Mayor Bob", "Wolf Alice", "Villager Charlie", "Villager Dave"]:
            state, _ = add_player(state, name)

        roles = ["mayor", "werewolf", "villager", "villager"]
        state = start_game(state, role_list=roles)

        mayor_p = next(p for p in state["players"].values() if p["role"] == "mayor")

        # Simulate Mayor was lynched during the day
        state["last_lynched_id"] = mayor_p["id"]
        set_player_status(state, mayor_p["id"], "dead")
        state["phase"] = "night"
        state["round_number"] = 2
        state["is_night_zero"] = False

        # Check Night stages: Mayor stage must allow self-pardon
        stages = get_night_stages(state)
        mayor_stage = next((s for s in stages if s.get("id") == "mayor"), None)
        assert mayor_stage is not None
        assert mayor_stage["was_lynched_yesterday"] is True
        assert mayor_stage["is_alive"] is True
        assert mayor_stage["has_veto"] is True

        # GM records Mayor exercising veto
        record_gm_night_action(state, "mayor", mayor_p["id"], extra={"mayor_veto": True})
        assert state["night_actions"]["mayor_veto"] is True

        # Resolve night -> Mayor should be revived and alive again!
        state = resolve_night(state)
        assert state["players"][mayor_p["id"]]["status"] == "alive"
        assert state["mayor_used_veto"] is True
        assert any("pardoned and returned alive" in r for r in state["night_report"])

    def test_cancel_day_vote_veto(self):
        """Verify GM / Mayor can cancel day vote outcome and restore eliminated player."""
        from lupus.game_state import (
            add_player,
            cancel_day_vote_veto,
            create_initial_state,
            set_player_status,
            start_game,
        )

        state = create_initial_state("VETO_DAY", "Cancel Day Vote Room")
        for name in ["Victim", "Wolf", "Villager1", "Villager2"]:
            state, _ = add_player(state, name)

        roles = ["mayor", "werewolf", "villager", "villager"]
        state = start_game(state, role_list=roles)

        victim = state["players"][list(state["players"].keys())[0]]
        set_player_status(state, victim["id"], "dead")
        state["last_lynched_id"] = victim["id"]
        state["voting"] = {"stage": "outcome", "eliminated_player_id": victim["id"]}

        success, msg = cancel_day_vote_veto(state)
        assert success is True
        assert "pardoned and returned alive" in msg
        assert state["players"][victim["id"]]["status"] == "alive"
        assert state["voting"]["eliminated_player_id"] is None
        assert state["voting"]["elimination_result"] == "mayor_vetoed"

    def test_direct_messages_player_and_gm(self):
        """Verify private direct messaging system between players and Game Master."""
        from lupus.game_state import (
            add_player,
            create_initial_state,
            get_gm_view,
            get_sanitized_player_view,
            mark_dms_read,
            send_direct_message,
        )

        state = create_initial_state("DM_TEST", "Direct Message Room")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")

        # 1. Alice sends DM to GM
        ok, msg, entry = send_direct_message(state, p1["id"], "gm", "Can I use my ability tonight?")
        assert ok is True
        assert entry["message"] == "Can I use my ability tonight?"
        assert entry["sender_name"] == "Alice"

        # Check views: Alice view has 1 DM, unread=0 (she sent it); Bob has 0 DMs; GM view has unread=1
        alice_view = get_sanitized_player_view(state, p1["id"])
        assert len(alice_view["my_dms"]) == 1
        assert alice_view["unread_dms_count"] == 0

        bob_view = get_sanitized_player_view(state, p2["id"])
        assert len(bob_view["my_dms"]) == 0
        assert bob_view["unread_dms_count"] == 0

        gm_view = get_gm_view(state)
        assert len(gm_view["direct_messages"]) == 1
        assert gm_view["unread_dms_count"] == 1

        # 2. GM replies to Alice
        ok, msg, entry2 = send_direct_message(state, "gm", p1["id"], "Yes, you may target anyone alive.")
        assert ok is True
        assert entry2["sender_id"] == "gm"

        alice_view = get_sanitized_player_view(state, p1["id"])
        assert len(alice_view["my_dms"]) == 2
        assert alice_view["unread_dms_count"] == 1

        # 3. Alice marks DMs as read
        updated = mark_dms_read(state, p1["id"])
        assert updated is True
        alice_view = get_sanitized_player_view(state, p1["id"])
        assert alice_view["unread_dms_count"] == 0

        # 4. GM marks DMs read for Alice
        gm_view = get_gm_view(state)
        assert gm_view["unread_dms_count"] == 1
        updated_gm = mark_dms_read(state, "gm", p1["id"])
        assert updated_gm is True
        gm_view = get_gm_view(state)
        assert gm_view["unread_dms_count"] == 0

    def test_ghost_midgame_lifecycle_and_optional_haunt(self):
        """Mid-game spirits (ghost, disgruntled ghost) only exist when a player holds them, and haunt is optional."""
        from lupus.game_state import (
            add_player,
            assign_midgame_role,
            create_initial_state,
            get_night_stages,
            remove_player,
            start_game,
        )

        state = create_initial_state("GHOST_TEST", "Ghost Lifecycle Room")
        for name in ["P1", "P2", "P3", "P4"]:
            state, _ = add_player(state, name)

        roles = ["werewolf", "villager", "villager", "villager"]
        state = start_game(state, role_list=roles)
        state["is_night_zero"] = False
        state["round_number"] = 1

        # Before any ghost is in room, ghost must NOT be in night stages
        stages = get_night_stages(state)
        assert not any(s.get("id") == "ghost" for s in stages)
        assert not any(s.get("id") == "disgruntled_ghost" for s in stages)

        # New player joins mid-game
        state, p_new = add_player(state, "New Joiner")
        assert p_new["status"] == "waiting"

        # GM assigns Town Ghost
        assign_midgame_role(state, p_new["id"], "ghost")
        assert state["players"][p_new["id"]]["role"] == "ghost"

        # Now Ghost stage appears in night stages and is_complete is True (optional action)
        stages = get_night_stages(state)
        ghost_stage = next((s for s in stages if s.get("id") == "ghost"), None)
        assert ghost_stage is not None
        assert ghost_stage["is_complete"] is True

        # Player leaves room
        remove_player(state, p_new["id"])

        # Ghost stage must cease to exist in night stages!
        stages = get_night_stages(state)
        assert not any(s.get("id") == "ghost" for s in stages)


@pytest.mark.django_db
class TestLupusV134GazetteLimitationsAndReplay:
    """Test v134 Gazette multi-posting (one-at-a-time pending) and GM round mute, plus Replay Timeline."""

    def test_gazette_multi_post_and_single_pending_enforcement(self):
        state = create_initial_state("TEST_GZ1", "Gazette Test")
        state, p1 = add_player(state, "Reporter1")
        state, p2 = add_player(state, "Reporter2")
        roles = ["villager", "villager"]
        state = start_game(state, role_list=roles)

        # 1. P1 submits first bulletin
        ok, msg = submit_news_bulletin(state, p1["id"], "News bulletin #1", anonymous=False)
        assert ok is True
        assert len(state["news_bulletins"]) == 1

        # 2. P1 tries to submit second bulletin while first is pending -> rejected!
        ok2, msg2 = submit_news_bulletin(state, p1["id"], "News bulletin #2", anonymous=False)
        assert ok2 is False
        assert "waiting for Game Master review" in msg2

        # 3. P2 can submit because P2 has no pending bulletins
        ok_p2, _ = submit_news_bulletin(state, p2["id"], "P2 News", anonymous=False)
        assert ok_p2 is True

        # 4. Check sanitized player view reflects pending bulletin
        view_p1 = get_sanitized_player_view(state, p1["id"])
        assert view_p1["me"]["has_pending_bulletin"] is True
        assert view_p1["me"]["can_submit_news"] is False
        assert view_p1["me"]["my_pending_bulletin"]["message"] == "News bulletin #1"

        # 5. GM rejects P1's first bulletin
        b1_id = state["news_bulletins"][0]["id"]
        ok_rej, _ = approve_news_bulletin(state, b1_id, approved=False)
        assert ok_rej is True

        # 6. Now that P1's bulletin was rejected, P1 CAN submit a second bulletin immediately!
        view_p1_after = get_sanitized_player_view(state, p1["id"])
        assert view_p1_after["me"]["has_pending_bulletin"] is False
        assert view_p1_after["me"]["can_submit_news"] is True

        ok3, _ = submit_news_bulletin(state, p1["id"], "Revised bulletin #2", anonymous=False)
        assert ok3 is True

        # 7. GM approves revised bulletin
        b2_id = state["news_bulletins"][-1]["id"]
        approve_news_bulletin(state, b2_id, approved=True)

        # 8. P1 can now submit a third bulletin!
        ok4, _ = submit_news_bulletin(state, p1["id"], "Breaking bulletin #3", anonymous=True)
        assert ok4 is True

    def test_gazette_gm_round_mute_and_automatic_reset(self):
        state = create_initial_state("TEST_MUTE", "Mute Test")
        state, p1 = add_player(state, "Troublemaker")
        state, p2 = add_player(state, "Townsperson")
        roles = ["villager", "villager"]
        state = start_game(state, role_list=roles)

        # GM mutes P1 from the gazette
        ok_m, msg_m = toggle_player_gazette_mute(state, p1["id"], muted=True)
        assert ok_m is True
        assert state["players"][p1["id"]]["is_gazette_muted"] is True

        # P1 tries to submit bulletin while muted -> rejected!
        ok_sub, msg_sub = submit_news_bulletin(state, p1["id"], "I want to spam!")
        assert ok_sub is False
        assert "muted from posting in the Town Gazette" in msg_sub

        # Player view indicates muted state
        view = get_sanitized_player_view(state, p1["id"])
        assert view["me"]["is_gazette_muted"] is True
        assert view["me"]["can_submit_news"] is False

        # Advance to night -> mute must reset!
        advance_to_night(state)
        assert state["players"][p1["id"]]["is_gazette_muted"] is False

        # Living player can now submit at night
        ok_night, _ = submit_news_bulletin(state, p1["id"], "Night scoop")
        assert ok_night is True

        # GM mutes P1 during night
        toggle_player_gazette_mute(state, p1["id"], muted=True)
        assert state["players"][p1["id"]]["is_gazette_muted"] is True

        # Dawn breaks (resolve_night) -> mute must reset again!
        resolve_night(state)
        assert state["players"][p1["id"]]["is_gazette_muted"] is False

    def test_build_round_timeline_and_gameover_view(self):
        state = create_initial_state("TEST_REPLAY", "Replay Test")
        state, p_wolf = add_player(state, "Wolfie")
        state, p_doc = add_player(state, "Doc")
        state, p_vill = add_player(state, "VillagerJoe")
        roles = ["werewolf", "doctor", "villager"]
        state = start_game(state, role_list=roles)

        # Submit bulletin on Day 0
        submit_news_bulletin(state, p_vill["id"], "Good morning town!")
        b_id = state["news_bulletins"][0]["id"]
        approve_news_bulletin(state, b_id, approved=True)

        # Night 1: Wolf attacks Joe, Doctor saves Joe
        advance_to_night(state)
        submit_night_action(state, p_wolf["id"], "kill", target_id=p_vill["id"])
        submit_night_action(state, p_doc["id"], "heal", target_id=p_vill["id"])
        resolve_night(state)

        # Day 1: Voting
        start_voting_session(state, system="two_stage_50pct")
        toggle_nomination_vote(state, p_doc["id"], p_wolf["id"])
        toggle_official_nomination(state, p_wolf["id"])
        proceed_to_final_vote(state)
        cast_final_vote(state, p_doc["id"], p_wolf["id"])
        tally_and_resolve_vote(state)

        # Build timeline
        timeline = build_round_timeline(state)
        assert len(timeline) >= 2

        # Verify round properties
        step_n0 = timeline[0]
        assert step_n0["phase"] == "night"
        assert step_n0["round"] == 0

        # Trigger Game Over
        state["phase"] = "gameover"
        state["winner"] = "town"

        # Verify get_sanitized_player_view contains round_timeline on gameover
        p_view = get_sanitized_player_view(state, p_vill["id"])
        assert "round_timeline" in p_view
        assert len(p_view["round_timeline"]) >= 2

    def test_circular_turn_order_mechanics_and_hand_raising(self):
        """Test circular turn order initialization, directionality, steppers, and arm-raising."""
        state = create_initial_state("ROOM_TURN", "Turn Order Room")
        state, p1 = add_player(state, "Alice")
        state, p2 = add_player(state, "Bob")
        state, p3 = add_player(state, "Charlie")
        state, p4 = add_player(state, "David")

        start_game(state)
        # Advance to day voting
        state["phase"] = "day_voting"
        start_voting_session(state, "two_stage_50pct")

        # 1. Start circular turn order clockwise starting at Bob (p2)
        start_circular_turn_order(state, starter_id=p2["id"], direction="clockwise")
        to = state["voting"]["turn_order"]
        assert to["active"] is True
        assert to["starter_id"] == p2["id"]
        assert to["direction"] == "clockwise"
        assert to["active_suspect_id"] == p2["id"]
        assert to["turn_index"] == 0
        assert to["turn_roster"] == [p2["id"], p3["id"], p4["id"], p1["id"]]

        # 2. Step forward clockwise -> Charlie (p3)
        advance_circular_turn(state, step=1)
        assert state["voting"]["turn_order"]["turn_index"] == 1
        assert state["voting"]["turn_order"]["active_suspect_id"] == p3["id"]

        # 3. Step forward clockwise -> David (p4)
        advance_circular_turn(state, step=1)
        assert state["voting"]["turn_order"]["turn_index"] == 2
        assert state["voting"]["turn_order"]["active_suspect_id"] == p4["id"]

        # 4. Step backward -> Charlie (p3)
        advance_circular_turn(state, step=-1)
        assert state["voting"]["turn_order"]["turn_index"] == 1
        assert state["voting"]["turn_order"]["active_suspect_id"] == p3["id"]

        # 5. Flip direction to counter-clockwise
        set_turn_order_direction(state, "counterclockwise")
        assert state["voting"]["turn_order"]["direction"] == "counterclockwise"
        assert state["voting"]["turn_order"]["turn_roster"] == [p3["id"], p2["id"], p1["id"], p4["id"]]

        # 6. Player arm-raising: Alice and Bob raise arms for Charlie
        ok, msg = toggle_hand_raise(state, p1["id"], candidate_id=p3["id"], source="player")
        assert ok is True
        assert "raised arm" in msg
        ok, msg = toggle_hand_raise(state, p2["id"], candidate_id=p3["id"], source="gm")
        assert ok is True

        # Check view
        v_view = get_voting_view(state, is_gm=False, player_id=p1["id"])
        assert v_view["turn_order"]["active"] is True
        assert v_view["turn_order"]["is_my_hand_raised"] is True
        assert v_view["turn_order"]["hands_raised_count"] == 2
        assert set(v_view["turn_order"]["hands_raised_ids"]) == {p1["id"], p2["id"]}

        # Alice lowers arm
        ok, msg = toggle_hand_raise(state, p1["id"], candidate_id=p3["id"])
        assert ok is True
        assert "lowered arm" in msg
        v_view_alice = get_voting_view(state, is_gm=False, player_id=p1["id"])
        assert v_view_alice["turn_order"]["is_my_hand_raised"] is False
        assert v_view_alice["turn_order"]["hands_raised_count"] == 1

        # Check timeline logs turn order and arm raises
        timeline = build_round_timeline(state)
        day_step = next(s for s in timeline if s["phase"] == "day")
        assert any("Turn order started" in ev for ev in day_step.get("events", []))
        assert "Charlie" in day_step.get("hand_raises", {})
        assert "Bob" in day_step["hand_raises"]["Charlie"]

        # 7. Stop turn order
        stop_circular_turn_order(state)
        assert state["voting"]["turn_order"]["active"] is False


class TestLupusTunableSettingsAndPresetsV136:
    """Tests for the comprehensive game settings schema, presets, and live tuning engine (v136)."""

    def test_settings_schema_defaults_and_validation(self):
        from lupus.settings_schema import (
            get_default_settings,
            validate_and_sanitize_settings,
        )

        defaults = get_default_settings()
        assert defaults["witch_revive_potions"] == 1
        assert defaults["witch_kill_potions"] == 1
        assert defaults["witch_can_use_both_in_one_night"] is True
        assert defaults["sniper_danger_bullets"] == 1
        assert defaults["sniper_silver_bullets"] == 0
        assert defaults["discussion_timer"] == 300
        assert defaults["defense_timer"] == 30
        assert defaults["public_mayor"] is True
        assert defaults["mayor_type"] == "public"

        # Test boundary clamping
        updates = {
            "witch_revive_potions": 99,  # max is 3
            "witch_kill_potions": -5,  # min is 0
            "sniper_danger_bullets": 10,  # max is 5
            "discussion_timer": 5,  # min is 30
            "mayor_type": "hidden",
            "reveal_roles_on_death": "3",
            "invalid_key_should_be_ignored": 123,
        }
        sanitized = validate_and_sanitize_settings(defaults, updates)
        assert sanitized["witch_revive_potions"] == 3
        assert sanitized["witch_kill_potions"] == 0
        assert sanitized["sniper_danger_bullets"] == 5
        assert sanitized["discussion_timer"] == 30
        assert sanitized["mayor_type"] == "hidden"
        assert sanitized["public_mayor"] is False
        assert sanitized["reveal_roles_on_death"] == 3
        assert "invalid_key_should_be_ignored" not in sanitized

    def test_update_settings_and_player_sync(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            set_manual_player_role,
            update_settings,
        )

        state = create_initial_state("SETT1", "Settings Test Room")
        state, p_mayor = add_player(state, "AliceMayor")
        state, p_sniper = add_player(state, "BobSniper")
        set_manual_player_role(state, p_mayor["id"], "mayor")
        set_manual_player_role(state, p_sniper["id"], "sniper")

        assert state["players"][p_mayor["id"]]["is_public_mayor"] is True

        # Update settings to hidden mayor and extra bullets
        state = update_settings(
            state,
            {
                "mayor_type": "hidden",
                "sniper_danger_bullets": 3,
                "sniper_silver_bullets": 2,
            },
        )
        assert state["settings"]["mayor_type"] == "hidden"
        assert state["settings"]["public_mayor"] is False
        assert state["players"][p_mayor["id"]]["is_public_mayor"] is False
        assert state["players"][p_sniper["id"]]["sniper_danger_bullets"] == 3
        assert state["players"][p_sniper["id"]]["sniper_silver_bullets"] == 2

        # Verify action recorded in history
        last_action = state["action_history"][-1]
        assert last_action["action"] == "update_settings"
        assert "mayor_type" in last_action["payload"]["updated_keys"]

    def test_settings_presets_application(self):
        from lupus.game_state import (
            apply_settings_preset,
            create_initial_state,
            reset_settings_to_default,
        )

        state = create_initial_state("PRE1", "Preset Test Room")

        # Apply chaos preset
        state = apply_settings_preset(state, "chaos")
        assert state["settings"]["witch_revive_potions"] == 2
        assert state["settings"]["witch_kill_potions"] == 2
        assert state["settings"]["sniper_danger_bullets"] == 2
        assert state["settings"]["sniper_silver_bullets"] == 2

        # Apply blitz preset
        state = apply_settings_preset(state, "blitz")
        assert state["settings"]["discussion_timer"] == 120
        assert state["settings"]["defense_timer"] == 20
        assert state["settings"]["reveal_roles_on_death"] == 1

        # Reset back to defaults
        state = reset_settings_to_default(state)
        assert state["settings"]["discussion_timer"] == 300
        assert state["settings"]["defense_timer"] == 30
        assert state["settings"]["witch_revive_potions"] == 1
        assert state["settings"]["witch_kill_potions"] == 1

    def test_witch_multiple_potions_and_dual_use_limitation(self):
        from lupus.game_state import (
            add_player,
            create_initial_state,
            record_gm_night_action,
            resolve_night,
            set_manual_player_role,
            submit_night_action,
            update_settings,
        )

        state = create_initial_state("WTCH1", "Witch Test Room")
        state, p_witch = add_player(state, "WandaWitch")
        state, p_victim1 = add_player(state, "VictimOne")
        state, p_victim2 = add_player(state, "VictimTwo")
        state, p_enemy1 = add_player(state, "EnemyOne")
        state, p_enemy2 = add_player(state, "EnemyTwo")

        set_manual_player_role(state, p_witch["id"], "witch")
        set_manual_player_role(state, p_victim1["id"], "villager")
        set_manual_player_role(state, p_victim2["id"], "villager")
        set_manual_player_role(state, p_enemy1["id"], "werewolf")
        set_manual_player_role(state, p_enemy2["id"], "werewolf")

        # Now start night 1
        state["phase"] = "night"
        state["round_number"] = 1
        state["is_night_zero"] = False

        # Configure Witch with 2 revive and 2 kill potions, but NO dual-use in same night, and limbo disabled
        state = update_settings(
            state,
            {
                "witch_revive_potions": 2,
                "witch_kill_potions": 2,
                "witch_can_use_both_in_one_night": False,
                "limbo_enabled": False,
            },
        )
        assert state["witch_revive_potions_left"] == 2
        assert state["witch_kill_potions_left"] == 2
        assert state["witch_used_revive"] is False
        assert state["witch_used_kill"] is False

        # Attempt to queue both revive and kill when dual use is forbidden
        ok, err = submit_night_action(
            state,
            p_witch["id"],
            "potion",
            extra={"revive": True, "kill_target": p_enemy1["id"]},
        )
        assert ok is False
        assert "both" in err.lower()

        # Night 1: Witch uses poison potion on Enemy 1
        record_gm_night_action(
            state,
            "witch",
            target_id=None,
            extra={"revive": False, "kill_target": p_enemy1["id"]},
        )
        resolve_night(state)
        assert state["players"][p_enemy1["id"]]["status"] == "dead"
        assert state["witch_kill_potions_left"] == 1
        assert state["witch_used_kill"] is False  # Still has 1 kill potion left!

        # Night 2: Advance round to night 2, Witch uses poison potion again on Enemy 2
        state["phase"] = "night"
        state["round_number"] = 2
        state["is_night_zero"] = False
        record_gm_night_action(
            state,
            "witch",
            target_id=None,
            extra={"revive": False, "kill_target": p_enemy2["id"]},
        )
        resolve_night(state)
        assert state["players"][p_enemy2["id"]]["status"] == "dead"
        assert state["witch_kill_potions_left"] == 0
        assert state["witch_used_kill"] is True  # Now kill potions exhausted!

    def test_gm_view_contains_settings_schema_and_presets(self):
        from lupus.game_state import create_initial_state, get_gm_view

        state = create_initial_state("VIEW1", "View Test Room")
        gm_view = get_gm_view(state)

        assert "settings_schema" in gm_view
        assert len(gm_view["settings_schema"]) == 5  # 5 categories
        cat_ids = [c["id"] for c in gm_view["settings_schema"]]
        assert "roles" in cat_ids
        assert "timers" in cat_ids
        assert "voting" in cat_ids
        assert "death_limbo" in cat_ids
        assert "communication" in cat_ids

        assert "settings_presets" in gm_view
        assert "default" in gm_view["settings_presets"]
        assert "chaos" in gm_view["settings_presets"]
        assert "blitz" in gm_view["settings_presets"]
        assert "competitive" in gm_view["settings_presets"]

    def test_table_placed_next_to_round_card_in_gm_dashboard(self):
        """Verify the physical table seating is placed right next to the round card."""
        with open("templates/lupus/gm_dashboard.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Layout container containing both Round Card and Table
        assert "gm-round-table-layout" in content
        assert "active-table-slot" in content
        assert "lobby-table-slot" in content
        assert "table-management-section" in content
        assert "syncTableSlot" in content

        # Verify Round Card and Table live together in the layout grid
        layout_idx = content.find('class="gm-round-table-layout"')
        assert layout_idx != -1
        active_slot_idx = content.find('id="active-table-slot"')
        assert active_slot_idx > layout_idx

        # Verify table-management-section is next to the round card
        table_mgmt_idx = content.find('id="table-management-section"')
        assert table_mgmt_idx != -1
        assert active_slot_idx < table_mgmt_idx < active_slot_idx + 300

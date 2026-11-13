"""Declarative schema, defaults, and presets for all Lupus game rules, role capacities, timers, and mechanics."""

from typing import Any

CATEGORIES = [
    {"id": "roles", "name": "Roles & Powers", "emoji": "🧙"},
    {"id": "timers", "name": "Timers & Pacing", "emoji": "⏱️"},
    {"id": "voting", "name": "Voting & Trials", "emoji": "🗳️"},
    {"id": "death_limbo", "name": "Death, Limbo & Reveals", "emoji": "⚰️"},
    {"id": "communication", "name": "Gazette & Communications", "emoji": "🗞️"},
]

LUPUS_SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    # ----------------------------------------------------
    # 1. ROLES & CAPACITIES
    # ----------------------------------------------------
    "witch_revive_potions": {
        "key": "witch_revive_potions",
        "category": "roles",
        "label": "Witch Revive Potions",
        "description": "Number of revival potions the Witch possesses to heal victims attacked by werewolves.",
        "type": "int",
        "default": 1,
        "min": 0,
        "max": 3,
        "step": 1,
    },
    "witch_kill_potions": {
        "key": "witch_kill_potions",
        "category": "roles",
        "label": "Witch Poison Potions",
        "description": "Number of lethal poison potions the Witch possesses to eliminate any living player at night.",
        "type": "int",
        "default": 1,
        "min": 0,
        "max": 3,
        "step": 1,
    },
    "witch_can_use_both_in_one_night": {
        "key": "witch_can_use_both_in_one_night",
        "category": "roles",
        "label": "Witch Dual Potion Usage",
        "description": "Allows the Witch to use both a revival potion and a poison potion on the exact same night.",
        "type": "bool",
        "default": True,
    },
    "sniper_danger_bullets": {
        "key": "sniper_danger_bullets",
        "category": "roles",
        "label": "Sniper Danger Bullets",
        "description": "Danger bullets for the Sniper (kills evil targets, backfires and eliminates the Sniper if target is innocent).",
        "type": "int",
        "default": 1,
        "min": 0,
        "max": 5,
        "step": 1,
    },
    "sniper_silver_bullets": {
        "key": "sniper_silver_bullets",
        "category": "roles",
        "label": "Sniper Silver Bullets",
        "description": "Silver bullets for the Sniper (kills evil targets, harmlessly expended with no recoil if target is innocent).",
        "type": "int",
        "default": 0,
        "min": 0,
        "max": 5,
        "step": 1,
    },
    "staggering_doctor": {
        "key": "staggering_doctor",
        "category": "roles",
        "label": "Doctor Consecutive Shield Cooldown",
        "description": "Doctor cannot shield the same player two nights in a row (staggered protection).",
        "type": "bool",
        "default": True,
    },
    "doctor_saves_from_sniper": {
        "key": "doctor_saves_from_sniper",
        "category": "roles",
        "label": "Doctor Saves From Sniper",
        "description": "Allows the Doctor's medical protection to shield an innocent player from being eliminated by a sniper shot.",
        "type": "bool",
        "default": False,
    },
    "bodyguard_can_guard_self": {
        "key": "bodyguard_can_guard_self",
        "category": "roles",
        "label": "Bodyguard Can Guard Self",
        "description": "Allows the Bodyguard to assign night protection to their own seat.",
        "type": "bool",
        "default": False,
    },
    "bodyguard_dies_on_save": {
        "key": "bodyguard_dies_on_save",
        "category": "roles",
        "label": "Bodyguard Sacrifices on Save",
        "description": "Bodyguard dies in place of their client if the client is attacked by werewolves.",
        "type": "bool",
        "default": True,
    },
    "wolf_cub_rampage_kills": {
        "key": "wolf_cub_rampage_kills",
        "category": "roles",
        "label": "Wolf Cub Rampage Total Kills",
        "description": "Total werewolf kills allowed on the night following the death of the Wolf Cub (frenzy rampage).",
        "type": "int",
        "default": 2,
        "min": 1,
        "max": 4,
        "step": 1,
    },
    "saboteur_wolf_charges": {
        "key": "saboteur_wolf_charges",
        "category": "roles",
        "label": "Saboteur Wolf Charges",
        "description": "Number of power-suppression or role-theft charges the Saboteur Wolf can execute per game.",
        "type": "int",
        "default": 1,
        "min": 1,
        "max": 3,
        "step": 1,
    },
    "hacker_scans_per_game": {
        "key": "hacker_scans_per_game",
        "category": "roles",
        "label": "Hacker Scans Limit",
        "description": "Maximum number of dark web intelligence scans the Hacker can perform across the game.",
        "type": "int",
        "default": 1,
        "min": 1,
        "max": 3,
        "step": 1,
    },
    "hacker_lockdown_enabled": {
        "key": "hacker_lockdown_enabled",
        "category": "roles",
        "label": "Hacker Day 1 Vote Lockdown",
        "description": "Hacker's Night 0 scan triggers mandatory voting lockdown on Day 1 (no execution permitted).",
        "type": "bool",
        "default": True,
    },
    "gull_shield_required": {
        "key": "gull_shield_required",
        "category": "roles",
        "label": "The Gull Converts to Werewolf",
        "description": "When attacked by werewolves, The Gull survives and secretly converts to Werewolf unless protected by Doctor.",
        "type": "bool",
        "default": True,
    },
    "mayor_type": {
        "key": "mayor_type",
        "category": "roles",
        "label": "Mayor Archetype",
        "description": "Public Mayor is openly revealed, immune to town lynching, and has 2x vote weight. Hidden Mayor is a secret disguised villager.",
        "type": "choice",
        "choices": [
            ("public", "Public Mayor (Revealed, Lynch Immune, 2x Vote)"),
            ("hidden", "Hidden Mayor (Secret, Normal Lynch, 1x Vote)"),
        ],
        "default": "public",
    },
    "mayor_can_cancel_vote": {
        "key": "mayor_can_cancel_vote",
        "category": "roles",
        "label": "Mayor Executive Pardon Veto",
        "description": "Mayor possesses executive veto power to cancel daytime execution and pardon the convicted player.",
        "type": "bool",
        "default": True,
    },
    "mayor_vote_weight": {
        "key": "mayor_vote_weight",
        "category": "roles",
        "label": "Public Mayor Vote Weight",
        "description": "Vote weight assigned to the Public Mayor during daytime trial voting ballots.",
        "type": "int",
        "default": 2,
        "min": 1,
        "max": 3,
        "step": 1,
    },
    "martyrdom_type": {
        "key": "martyrdom_type",
        "category": "roles",
        "label": "Martyrdom Detonation Trigger",
        "description": "Public Martyrdom allows instant daytime town square grenade detonation. Hidden Martyrdom sets a delayed night booby trap.",
        "type": "choice",
        "choices": [
            ("public", "Public Detonation (Instant Day Blast)"),
            ("hidden", "Hidden Booby Trap (Stealth Night Trigger)"),
        ],
        "default": "public",
    },
    # ----------------------------------------------------
    # 2. TIMERS & PACING
    # ----------------------------------------------------
    "discussion_timer": {
        "key": "discussion_timer",
        "category": "timers",
        "label": "Day Discussion Timer (sec)",
        "description": "Duration in seconds for open village discussion before nominations/voting commence.",
        "type": "int",
        "default": 300,
        "min": 30,
        "max": 1800,
        "step": 15,
    },
    "defense_timer": {
        "key": "defense_timer",
        "category": "timers",
        "label": "Defense Speech Timer (sec)",
        "description": "Speech time in seconds granted to an accused player on trial to speak in their defense.",
        "type": "int",
        "default": 30,
        "min": 10,
        "max": 300,
        "step": 5,
    },
    "voting_timer": {
        "key": "voting_timer",
        "category": "timers",
        "label": "Final Ballot Timer (sec)",
        "description": "Countdown in seconds for casting final execution ballots (0 = untimed GM pacing).",
        "type": "int",
        "default": 60,
        "min": 0,
        "max": 300,
        "step": 5,
    },
    "night_stage_timer": {
        "key": "night_stage_timer",
        "category": "timers",
        "label": "Night Stage Timer (sec)",
        "description": "Countdown timer in seconds for each active night action stage (0 = untimed GM pacing).",
        "type": "int",
        "default": 60,
        "min": 0,
        "max": 300,
        "step": 5,
    },
    # ----------------------------------------------------
    # 3. DAYTIME VOTING & TRIALS
    # ----------------------------------------------------
    "voting_system": {
        "key": "voting_system",
        "category": "voting",
        "label": "Day Voting & Trial System",
        "description": "Rules for nominating and executing players during the daytime.",
        "type": "choice",
        "choices": [
            ("two_stage_50pct", "Two-Stage: 50% Living Threshold Nominations + Trial"),
            ("two_stage_top_n", "Two-Stage: Top N Candidates Nominated + Trial"),
            ("simple_plurality", "Simple Plurality: Single Runoff Execution Ballot"),
        ],
        "default": "two_stage_50pct",
    },
    "nomination_threshold_pct": {
        "key": "nomination_threshold_pct",
        "category": "voting",
        "label": "Nomination Threshold (%)",
        "description": "Percentage of living players who must raise their hands to send a candidate to trial (for 50% threshold system).",
        "type": "int",
        "default": 50,
        "min": 10,
        "max": 100,
        "step": 5,
    },
    "top_n_nominees_count": {
        "key": "top_n_nominees_count",
        "category": "voting",
        "label": "Top-N Nominees Count",
        "description": "Number of top candidates who advance to trial in the Top-N voting system.",
        "type": "int",
        "default": 2,
        "min": 2,
        "max": 5,
        "step": 1,
    },
    "max_tie_runoffs": {
        "key": "max_tie_runoffs",
        "category": "voting",
        "label": "Maximum Tie Runoffs",
        "description": "How many tied runoff ballots are permitted before day ends with NO elimination.",
        "type": "int",
        "default": 1,
        "min": 0,
        "max": 3,
        "step": 1,
    },
    "allow_self_nomination": {
        "key": "allow_self_nomination",
        "category": "voting",
        "label": "Allow Self-Nomination",
        "description": "Permits players to raise their own hand to nominate themselves.",
        "type": "bool",
        "default": True,
    },
    # ----------------------------------------------------
    # 4. DEATH, LIMBO & REVEALS
    # ----------------------------------------------------
    "limbo_enabled": {
        "key": "limbo_enabled",
        "category": "death_limbo",
        "label": "Limbo Realm Enabled",
        "description": "Slain players hover between life and death in Limbo before permanently dying, giving Angel/Medium a chance to rescue them.",
        "type": "bool",
        "default": True,
    },
    "limbo_duration_rounds": {
        "key": "limbo_duration_rounds",
        "category": "death_limbo",
        "label": "Limbo Duration (Rounds)",
        "description": "Number of rounds a soul lingers in Limbo before fading permanently.",
        "type": "int",
        "default": 1,
        "min": 1,
        "max": 3,
        "step": 1,
    },
    "reveal_roles_on_death": {
        "key": "reveal_roles_on_death",
        "category": "death_limbo",
        "label": "Death Role Reveal Policy",
        "description": "How much secret role information is announced to the room when a player dies.",
        "type": "choice",
        "choices": [
            ("0", "0 — Secret: Closed graveyard, roles concealed until game over"),
            ("1", "1 — Alignment Only: Announces GOOD vs EVIL"),
            ("2", "2 — Faction / Team: Announces Town, Werewolves, Neutral"),
            ("3", "3 — Full Role Card: Announces exact role name and icon"),
        ],
        "default": 0,
    },
    "public_heartbreak_cause": {
        "key": "public_heartbreak_cause",
        "category": "death_limbo",
        "label": "Public Heartbreak Announcement",
        "description": "When a lover perishes from heartbreak, announce 'Died of a Broken Heart' vs generic 'Found Dead'.",
        "type": "bool",
        "default": False,
    },
    # ----------------------------------------------------
    # 5. GAZETTE, SPIRITS & CHAT
    # ----------------------------------------------------
    "gazette_enabled": {
        "key": "gazette_enabled",
        "category": "communication",
        "label": "Town Gazette Enabled",
        "description": "Enables the player-submitted press and news bulletin publication desk.",
        "type": "bool",
        "default": True,
    },
    "gazette_anonymous_allowed": {
        "key": "gazette_anonymous_allowed",
        "category": "communication",
        "label": "Gazette Anonymous Informants",
        "description": "Permits players to submit news bulletins anonymously under the 'Anonymous Informant' byline.",
        "type": "bool",
        "default": True,
    },
    "gazette_max_pending_per_player": {
        "key": "gazette_max_pending_per_player",
        "category": "communication",
        "label": "Gazette Max Pending Bulletins",
        "description": "Maximum number of unapproved bulletins a player can have pending in the GM queue at one time.",
        "type": "int",
        "default": 1,
        "min": 1,
        "max": 3,
        "step": 1,
    },
    "gazette_max_length": {
        "key": "gazette_max_length",
        "category": "communication",
        "label": "Gazette Bulletin Max Chars",
        "description": "Maximum character length allowed per published news bulletin.",
        "type": "int",
        "default": 200,
        "min": 50,
        "max": 500,
        "step": 25,
    },
    "ghost_messages_per_round": {
        "key": "ghost_messages_per_round",
        "category": "communication",
        "label": "Ghost Messages Per Round",
        "description": "Number of spectral messages a deceased Ghost may transmit to the Medium per round.",
        "type": "int",
        "default": 1,
        "min": 1,
        "max": 5,
        "step": 1,
    },
    "direct_messages_enabled": {
        "key": "direct_messages_enabled",
        "category": "communication",
        "label": "Host Direct Messages (DMs)",
        "description": "Enables private, discreet two-way chat between individual players and the Game Master.",
        "type": "bool",
        "default": True,
    },
    "confetti_enabled": {
        "key": "confetti_enabled",
        "category": "communication",
        "label": "Victory Confetti Celebration",
        "description": "Fires winning faction emoji confetti upon match completion.",
        "type": "bool",
        "default": True,
    },
}


SETTINGS_PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "name": "Balanced / Standard",
        "description": "Classic Lupus balance: 50% nomination threshold, 5min discussion, 1 danger bullet, 1 revive/kill potion, mystery deaths.",
        "settings": {k: v["default"] for k, v in LUPUS_SETTINGS_SCHEMA.items()},
    },
    "blitz": {
        "name": "Blitz / Fast Paced",
        "description": "Fast-paced action with tight discussion timers (120s), quick 20s defense speeches, and extra sniper ammunition.",
        "settings": {
            **{k: v["default"] for k, v in LUPUS_SETTINGS_SCHEMA.items()},
            "discussion_timer": 120,
            "defense_timer": 20,
            "voting_timer": 30,
            "night_stage_timer": 30,
            "sniper_danger_bullets": 2,
            "sniper_silver_bullets": 1,
            "reveal_roles_on_death": 1,
        },
    },
    "chaos": {
        "name": "Chaos / High Power",
        "description": "Maximum firepower: 2 revive & 2 kill potions, 3 wolf cub rampage frenzy kills, 2 hacker scans, and instant public blasts.",
        "settings": {
            **{k: v["default"] for k, v in LUPUS_SETTINGS_SCHEMA.items()},
            "witch_revive_potions": 2,
            "witch_kill_potions": 2,
            "sniper_danger_bullets": 2,
            "sniper_silver_bullets": 2,
            "wolf_cub_rampage_kills": 3,
            "hacker_scans_per_game": 2,
            "saboteur_wolf_charges": 2,
            "martyrdom_type": "public",
            "public_heartbreak_cause": True,
        },
    },
    "competitive": {
        "name": "Competitive / Mystery",
        "description": "Strict deductive hardcore play: zero death reveals until game over, no anonymous gazette, 1 tie max, and 1-shot ammo limits.",
        "settings": {
            **{k: v["default"] for k, v in LUPUS_SETTINGS_SCHEMA.items()},
            "discussion_timer": 360,
            "defense_timer": 45,
            "reveal_roles_on_death": 0,
            "gazette_anonymous_allowed": False,
            "sniper_danger_bullets": 1,
            "sniper_silver_bullets": 0,
            "witch_revive_potions": 1,
            "witch_kill_potions": 1,
            "max_tie_runoffs": 1,
        },
    },
}


def get_default_settings() -> dict[str, Any]:
    """Return dictionary with all settings initialized to their default values."""
    defaults = {k: v["default"] for k, v in LUPUS_SETTINGS_SCHEMA.items()}
    defaults["public_mayor"] = defaults.get("mayor_type") == "public"
    defaults["public_martyrdom"] = defaults.get("martyrdom_type") == "public"
    return defaults


def validate_and_sanitize_settings(current_settings: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Merge and validate user updates against the declarative settings schema.
    Clamps numeric boundaries and verifies choice selections.
    """
    merged = dict(current_settings or {})
    for key, val in updates.items():
        if key not in LUPUS_SETTINGS_SCHEMA:
            # Handle aliases or legacy keys
            if key == "public_mayor":
                merged["public_mayor"] = bool(val)
                merged["mayor_type"] = "public" if val else "hidden"
            elif key == "public_martyrdom":
                merged["public_martyrdom"] = bool(val)
                merged["martyrdom_type"] = "public" if val else "hidden"
            continue

        meta = LUPUS_SETTINGS_SCHEMA[key]
        stype = meta["type"]

        if stype == "int":
            try:
                num = int(val)
                if "min" in meta and num < meta["min"]:
                    num = meta["min"]
                if "max" in meta and num > meta["max"]:
                    num = meta["max"]
                merged[key] = num
            except (ValueError, TypeError):
                pass
        elif stype == "bool":
            if isinstance(val, str):
                merged[key] = val.lower() in ("true", "1", "yes", "on")
            else:
                merged[key] = bool(val)
        elif stype == "choice":
            val_str = str(val)
            valid_choices = [str(c[0]) for c in meta.get("choices", [])]
            if val_str in valid_choices:
                if isinstance(meta.get("default"), int):
                    merged[key] = int(val_str)
                else:
                    merged[key] = val_str

    # Synchronize boolean aliases
    if "mayor_type" in merged:
        merged["public_mayor"] = merged["mayor_type"] == "public"
    if "martyrdom_type" in merged:
        merged["public_martyrdom"] = merged["martyrdom_type"] == "public"

    return merged


def get_settings_schema_view() -> list[dict[str, Any]]:
    """Return category-grouped settings metadata for frontend rendering."""
    grouped = []
    for cat in CATEGORIES:
        cat_id = cat["id"]
        items = [meta for k, meta in LUPUS_SETTINGS_SCHEMA.items() if meta.get("category") == cat_id]
        grouped.append(
            {
                "id": cat_id,
                "name": cat["name"],
                "emoji": cat["emoji"],
                "items": items,
            }
        )
    return grouped

"""Role definitions, factions, abilities, and theme mappings (Werewolf vs. Mafia)."""

from typing import Any

FACTION_TOWN = "town"
FACTION_WOLVES = "wolves"
FACTION_NEUTRAL = "neutral"

ROLE_REGISTRY: dict[str, dict[str, Any]] = {
    "villager": {
        "id": "villager",
        "faction": FACTION_TOWN,
        "emoji": "🧑",
        "names": {"werewolf": "Villager", "mafia": "Citizen"},
        "descriptions": {
            "werewolf": "No special night action. Deduce who the wolves are and vote during the day.",
            "mafia": "No special night action. Deduce who the mobsters are and vote during the day.",
        },
        "night_action": None,
    },
    "werewolf": {
        "id": "werewolf",
        "faction": FACTION_WOLVES,
        "emoji": "🐺",
        "names": {"werewolf": "Werewolf", "mafia": "Mafioso"},
        "descriptions": {
            "werewolf": "Wakes with the pack at night to select a victim to eliminate.",
            "mafia": "Wakes with the family at night to select a target to eliminate.",
        },
        "night_action": "kill",
    },
    "alpha_wolf": {
        "id": "alpha_wolf",
        "faction": FACTION_WOLVES,
        "emoji": "👑",
        "names": {"werewolf": "Alpha Wolf", "mafia": "Godfather"},
        "descriptions": {
            "werewolf": "Pack leader. Appears innocent ('Good') to the Detective's investigation.",
            "mafia": "Crime boss. Appears innocent ('Good') to the Detective's investigation.",
        },
        "night_action": "kill",
    },
    "silencer": {
        "id": "silencer",
        "faction": FACTION_WOLVES,
        "emoji": "🤐",
        "names": {"werewolf": "Magic Wolf (Silencer)", "mafia": "Consigliere (Psychologist)"},
        "descriptions": {
            "werewolf": "Can choose one player at night to be completely silenced during the next day.",
            "mafia": "Can choose one player at night to be completely silenced during the next day.",
        },
        "night_action": "silence",
    },
    "detective": {
        "id": "detective",
        "faction": FACTION_TOWN,
        "emoji": "🔍",
        "names": {"werewolf": "Detective / Vidente", "mafia": "Detective / Cop"},
        "descriptions": {
            "werewolf": "Inspects one player each night to learn if they are Evil or Good.",
            "mafia": "Inspects one player each night to learn if they are Evil or Good.",
        },
        "night_action": "inspect",
    },
    "doctor": {
        "id": "doctor",
        "faction": FACTION_TOWN,
        "emoji": "🩺",
        "names": {"werewolf": "Guard / Doctor", "mafia": "Doctor / Medic"},
        "descriptions": {
            "werewolf": "Protects a player from death each night (can choose self). Cannot protect same target twice.",
            "mafia": "Protects a player from death each night (can choose self). Cannot protect same target twice.",
        },
        "night_action": "protect",
    },
    "sniper": {
        "id": "sniper",
        "faction": FACTION_TOWN,
        "emoji": "🎯",
        "names": {"werewolf": "Sniper / Hunter", "mafia": "Sniper / Vigilante"},
        "descriptions": {
            "werewolf": "Can shoot at night. Beware danger bullets: if you miss a wolf, you die!",
            "mafia": "Can shoot at night. Beware danger bullets: if you miss a mafioso, you die!",
        },
        "night_action": "shoot",
    },
    "mayor": {
        "id": "mayor",
        "faction": FACTION_TOWN,
        "emoji": "🎖️",
        "names": {"werewolf": "Mayor", "mafia": "Mayor"},
        "descriptions": {
            "werewolf": "Can secretly veto and cancel the previous day's vote, reviving the lynched victim.",
            "mafia": "Can secretly veto and cancel the previous day's vote, reviving the lynched victim.",
        },
        "night_action": "veto",
    },
    "angel": {
        "id": "angel",
        "faction": FACTION_TOWN,
        "emoji": "👼",
        "names": {"werewolf": "Angel", "mafia": "Angel"},
        "descriptions": {
            "werewolf": "Limbo guardian. Players in Limbo who guess who you are return to life!",
            "mafia": "Limbo guardian. Players in Limbo who guess who you are return to life!",
        },
        "night_action": None,
    },
    "witch": {
        "id": "witch",
        "faction": FACTION_TOWN,
        "emoji": "🧙‍♀️",
        "names": {"werewolf": "Witch", "mafia": "Chemist"},
        "descriptions": {
            "werewolf": "Possesses two potions: one to revive the night's victim, and one lethal poison.",
            "mafia": "Possesses two potions: one antidote to revive the victim, and one lethal poison.",
        },
        "night_action": "potion",
    },
    "cupid": {
        "id": "cupid",
        "faction": FACTION_NEUTRAL,
        "emoji": "💘",
        "names": {"werewolf": "Cupid", "mafia": "Matchmaker"},
        "descriptions": {
            "werewolf": "On Night 1, chooses two lovers. If one dies, the other dies of grief.",
            "mafia": "On Night 1, chooses two lovers. If one dies, the other dies of grief.",
        },
        "night_action": "link_lovers",
    },
    "jester": {
        "id": "jester",
        "faction": FACTION_NEUTRAL,
        "emoji": "🃏",
        "names": {"werewolf": "Jester", "mafia": "Fool"},
        "descriptions": {
            "werewolf": "A tricky loner. Wins the game if voted out and executed during the day!",
            "mafia": "A tricky loner. Wins the game if voted out and executed during the day!",
        },
        "night_action": None,
    },
}


def get_role_info(role_id: str, theme: str = "werewolf") -> dict[str, Any]:
    """Retrieve localized role configuration according to selected theme."""
    base = ROLE_REGISTRY.get(role_id, ROLE_REGISTRY["villager"])
    theme_key = "mafia" if theme == "mafia" else "werewolf"
    return {
        "id": base["id"],
        "faction": base["faction"],
        "emoji": base["emoji"],
        "name": base["names"].get(theme_key, base["names"]["werewolf"]),
        "description": base["descriptions"].get(theme_key, base["descriptions"]["werewolf"]),
        "night_action": base["night_action"],
    }


def get_faction_display(faction: str, theme: str = "werewolf") -> str:
    if faction == FACTION_WOLVES:
        return "Mafia" if theme == "mafia" else "Werewolves"
    if faction == FACTION_TOWN:
        return "Civilians / Town" if theme == "mafia" else "Villagers"
    return "Neutral"


DEFAULT_PRESETS = {
    "quick_5": ["werewolf", "detective", "doctor", "villager", "villager"],
    "balanced_8": ["werewolf", "werewolf", "detective", "doctor", "angel", "sniper", "villager", "villager"],
    "full_10": [
        "werewolf",
        "alpha_wolf",
        "detective",
        "doctor",
        "angel",
        "sniper",
        "mayor",
        "silencer",
        "villager",
        "villager",
    ],
    "chaos_12": [
        "werewolf",
        "werewolf",
        "silencer",
        "detective",
        "doctor",
        "angel",
        "sniper",
        "mayor",
        "witch",
        "cupid",
        "jester",
        "villager",
    ],
}

"""Role definitions, factions, abilities, beginner guides, and theme mappings (Werewolf vs. Mafia)."""

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
        "guide": {
            "objective": "Town: Eliminate all Werewolves/Mafia to win.",
            "day_tips": "Speak up! Ask players questions, listen for hesitations, and watch who votes together.",
            "night_tips": "Sleep safely. You have no night power, but watch the morning dawn report carefully.",
            "pro_tip": "Your vote is the town's most lethal weapon. Don't be afraid to lead discussions!",
        },
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
        "guide": {
            "objective": "Evil: Eliminate townspeople until wolves equal or outnumber the living town.",
            "day_tips": "Act like a helpful villager. Propose theories, but avoid defending packmates too visibly.",
            "night_tips": "Select a single town member to eliminate with your pack.",
            "pro_tip": "Target strong or confirmed town power roles (Detective, Doctor) early to blind the town.",
        },
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
        "guide": {
            "objective": "Evil: Lead your pack to victory. You are immune to Detective detection.",
            "day_tips": "Play boldly! If the Detective checks you, you appear completely innocent and cleared.",
            "night_tips": "Coordinate night kills with fellow wolves.",
            "pro_tip": "Use your false innocence to gain town trust and guide executions onto innocent villagers.",
        },
    },
    "silencer": {
        "id": "silencer",
        "faction": FACTION_WOLVES,
        "emoji": "🤐",
        "names": {"werewolf": "Magic Wolf (Silencer)", "mafia": "Consigliere (Silencer)"},
        "descriptions": {
            "werewolf": "Can choose one player at night to be completely silenced during the next day.",
            "mafia": "Can choose one player at night to be completely silenced during the next day.",
        },
        "night_action": "silence",
        "guide": {
            "objective": "Evil: Silence vocal leaders to disrupt town communication.",
            "day_tips": "Notice who is silenced and use their forced quiet to steer suspicions.",
            "night_tips": "Select a player to mute. Tomorrow they cannot speak, whisper, or gesture until nightfall.",
            "pro_tip": "Silence the Detective or most convincing speaker to keep them from sharing clues.",
        },
    },
    "framer": {
        "id": "framer",
        "faction": FACTION_WOLVES,
        "emoji": "🎭",
        "names": {"werewolf": "Cursed Shaman (Framer)", "mafia": "Framer / Swindler"},
        "descriptions": {
            "werewolf": "Frames an innocent player at night. If inspected by the Detective, they appear Evil!",
            "mafia": "Frames an innocent player at night. If inspected by the Detective, they appear Evil!",
        },
        "night_action": "frame",
        "guide": {
            "objective": "Evil: Frame innocent town members to trick the Detective into executing townspeople.",
            "day_tips": "Cast doubt on your framed target. If the Detective checks them, they appear evil!",
            "night_tips": "Pick an active townsperson who you think the Detective is curious about.",
            "pro_tip": "A framed villager who gets investigated leads to an instant town mislynch!",
        },
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
        "guide": {
            "objective": "Town: Investigate one player every night to identify wolves and clear innocents.",
            "day_tips": "Share findings carefully. Don't reveal your role too early or wolves will kill you!",
            "night_tips": "Choose one suspect to investigate their true alignment.",
            "pro_tip": "Beware: The Alpha Wolf appears Good, and Framed players appear Evil!",
        },
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
        "guide": {
            "objective": "Town: Guard living players from night elimination.",
            "day_tips": "Listen closely to figure out who the Detective is, so you can guard them.",
            "night_tips": "Shield one player. If wolves attack them, they survive! (Cannot guard same target twice).",
            "pro_tip": "Guard yourself when in danger; guard confirmed innocents on subsequent nights.",
        },
    },
    "bodyguard": {
        "id": "bodyguard",
        "faction": FACTION_TOWN,
        "emoji": "🛡️",
        "names": {"werewolf": "Bodyguard", "mafia": "Bodyguard"},
        "descriptions": {
            "werewolf": "Protects a player at night. If wolves attack them, you sacrifice yourself to save their life!",
            "mafia": "Protects a player at night. If mafia attacks them, you sacrifice yourself to save their life!",
        },
        "night_action": "guard_bodyguard",
        "guide": {
            "objective": "Town: Protect a key town member with your life.",
            "day_tips": "Identify the Detective or town leader and stay in the shadows.",
            "night_tips": "Choose a player to guard. If wolves attack them, you die in their place and they live.",
            "pro_tip": "Never announce who you are guarding; let wolves walk into your trap.",
        },
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
        "guide": {
            "objective": "Town: Take out suspected wolves under cover of darkness.",
            "day_tips": "Watch for deceptive claims or suspicious voting blocks during the day.",
            "night_tips": "Shoot a suspect. If danger bullets are on and target is innocent, you die of guilt!",
            "pro_tip": "Do not shoot blindly on Night 1. Wait until day discussions give you a high-probability read.",
        },
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
        "guide": {
            "objective": "Town: Stay alive so souls sent to Limbo can guess your identity and resurrect.",
            "day_tips": "Drop subtle hints to townspeople you trust so they know who to guess if sent to Limbo.",
            "night_tips": "Sleep safely. Your spiritual presence watches over Limbo.",
            "pro_tip": "If wolves figure out you are the Angel, they will eliminate you immediately to stop revivals.",
        },
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
        "guide": {
            "objective": "Town: Lead the town and veto incorrect executions.",
            "day_tips": "Participate actively and watch the vote outcome.",
            "night_tips": "If an innocent player was voted out, trigger your 1-time Veto to bring them back alive.",
            "pro_tip": "Save your veto for a confirmed innocent or critical power role like the Detective.",
        },
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
        "guide": {
            "objective": "Town: Use your two powerful potions at crucial turning points.",
            "day_tips": "Keep quiet about your potion inventory.",
            "night_tips": "You have 1 revival potion (saves tonight's victim) and 1 poison potion (kills any player).",
            "pro_tip": "Use poison when you are confident someone is an evil wolf who avoided day execution.",
        },
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
        "guide": {
            "objective": "Neutral: Link two lovers. If from opposing factions, they must win together!",
            "day_tips": "Observe how your chosen lovers behave and protect their secret bond.",
            "night_tips": "On Night 1 only, select two players to bind as lovers.",
            "pro_tip": "Binding a Wolf to a Villager creates an exciting romance that flips the game!",
        },
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
        "guide": {
            "objective": "Neutral Solo: Get yourself executed during the daytime town vote to win instantly!",
            "day_tips": "Act slightly suspicious or defend accused wolves poorly so town votes you out.",
            "night_tips": "Sleep safely. Hope wolves don't kill you at night (you only win if executed by day vote!).",
            "pro_tip": "Don't act too obviously crazy, or experienced players will recognize you and ignore you.",
        },
    },
    "serial_killer": {
        "id": "serial_killer",
        "faction": FACTION_NEUTRAL,
        "emoji": "🔪",
        "names": {"werewolf": "Maniac / Lone Wolf", "mafia": "Serial Killer"},
        "descriptions": {
            "werewolf": "A solo killer independent of the pack. Wakes each night to eliminate a victim.",
            "mafia": "A solo killer independent of the family. Wakes each night to eliminate a victim.",
        },
        "night_action": "solo_kill",
        "guide": {
            "objective": "Neutral Solo: Outlive everyone! You win if you are the last survivor standing.",
            "day_tips": "Act like an ordinary villager. Eliminate wolves by day and pick off town by night.",
            "night_tips": "Select a player to eliminate secretly in the shadows.",
            "pro_tip": "Target vocal players or wolves; let Town and Wolves tear each other apart while you clean up.",
        },
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
        "guide": base.get("guide", {}),
    }


def get_faction_display(faction: str, theme: str = "werewolf") -> str:
    if faction == FACTION_WOLVES:
        return "Mafia" if theme == "mafia" else "Werewolves"
    if faction == FACTION_TOWN:
        return "Civilians / Town" if theme == "mafia" else "Villagers"
    return "Neutral"


def get_all_roles_catalogue(theme: str = "werewolf") -> list[dict[str, Any]]:
    """Return all available roles with localized names, descriptions, and beginner guides."""
    return [get_role_info(role_id, theme) for role_id in ROLE_REGISTRY.keys()]


def generate_preset_deck(player_count: int, preset: str = "simple") -> list[str]:
    """Generate a balanced deck of roles dynamically tailored to the player count.

    Standard evil ratio is ~25%–33%:
    - 3-5 players: 1 evil
    - 6-8 players: 2 evil
    - 9-11 players: 3 evil
    - 12+ players: 4 evil
    """
    count = max(3, player_count)
    if count <= 5:
        num_evil = 1
    elif count <= 8:
        num_evil = 2
    elif count <= 11:
        num_evil = 3
    else:
        num_evil = 4

    deck: list[str] = []

    if preset in ("simple", "pure", "quick_5"):
        # Pure wolves/mafia vs plain villagers (zero special powers)
        deck.extend(["werewolf"] * num_evil)
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    elif preset in ("standard", "classic", "balanced_8"):
        # Standard: Wolves + Detective + Doctor + Villagers
        deck.extend(["werewolf"] * num_evil)
        if count >= 4:
            deck.append("detective")
        if count >= 5:
            deck.append("doctor")
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    elif preset in ("limbo", "angel"):
        # Limbo: Wolves + Detective + Doctor + Angel + Sniper + Bodyguard + Villagers
        deck.extend(["werewolf"] * num_evil)
        if count >= 4:
            deck.append("detective")
        if count >= 5:
            deck.append("doctor")
        if count >= 6:
            deck.append("angel")
        if count >= 7:
            deck.append("sniper")
        if count >= 9:
            deck.append("bodyguard")
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    elif preset in ("chaos", "full_10", "chaos_12"):
        # Chaos: Diverse powers (Alpha wolf, Silencer, Framer, Detective, Doctor, Bodyguard, Angel, etc.)
        if num_evil >= 3:
            deck.extend(["werewolf"] * (num_evil - 2))
            deck.append("alpha_wolf")
            deck.append("framer")
        elif num_evil >= 2:
            deck.append("werewolf")
            deck.append("alpha_wolf")
        else:
            deck.append("werewolf")

        specials = [
            "detective",
            "doctor",
            "bodyguard",
            "angel",
            "silencer",
            "sniper",
            "mayor",
            "witch",
            "cupid",
            "jester",
            "serial_killer",
        ]
        for s in specials:
            if len(deck) < count - 1:
                deck.append(s)
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    else:
        deck.extend(["werewolf"] * num_evil)
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    return deck[:count]


DEFAULT_PRESETS = {
    "simple": ["werewolf", "werewolf", "villager", "villager", "villager", "villager", "villager"],
    "standard": ["werewolf", "werewolf", "detective", "doctor", "villager", "villager", "villager"],
    "limbo": ["werewolf", "werewolf", "detective", "doctor", "angel", "sniper", "villager", "villager"],
    "chaos": [
        "werewolf",
        "alpha_wolf",
        "silencer",
        "framer",
        "detective",
        "doctor",
        "bodyguard",
        "angel",
        "sniper",
        "mayor",
        "witch",
        "cupid",
        "jester",
        "serial_killer",
        "villager",
    ],
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

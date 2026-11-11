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
            "objective": "Town: Eliminate all Werewolves/Mafia and evil threats to win.",
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
        "emoji": "🦍",
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
            "werewolf": "Can choose one player at night to be silenced during the next day. The silenced target cannot speak or gesture during discussion, but CAN still vote! Cannot silence the same target two nights in a row.",
            "mafia": "Can choose one player at night to be silenced during the next day. The silenced target cannot speak or gesture during discussion, but CAN still vote! Cannot silence the same target two nights in a row.",
        },
        "night_action": "silence",
        "guide": {
            "objective": "Evil: Silence vocal leaders to disrupt town communication.",
            "day_tips": "Notice who is silenced and use their forced quiet to steer suspicions.",
            "night_tips": "Select a player to mute. Tomorrow they cannot speak or whisper, but they can still cast their vote. You cannot mute the same player two nights in a row.",
            "pro_tip": "Silence the Detective or most convincing speaker to keep them from sharing clues.",
        },
    },
    "framer": {
        "id": "framer",
        "faction": FACTION_WOLVES,
        "emoji": "😵‍💫",
        "enabled": True,
        "names": {"werewolf": "Cursed Shaman (Framer)", "mafia": "Framer / Swindler"},
        "descriptions": {
            "werewolf": "Frames an innocent player at night. If inspected by the Detective, they appear Evil for that night!",
            "mafia": "Frames an innocent player at night. If inspected by the Detective, they appear Evil for that night!",
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
            "werewolf": "Inspects one player each night to learn if they are Evil or Good (Wolves and Serial Killer appear Evil; Citizens, Doctor, Watson, and Jester appear Good).",
            "mafia": "Inspects one player each night to learn if they are Evil or Good (Mafia and Serial Killer appear Evil; Citizens, Doctor, Watson, and Fool appear Good).",
        },
        "night_action": "inspect",
        "guide": {
            "objective": "Town: Investigate one player every night to identify wolves and clear innocents.",
            "day_tips": "Share findings carefully. Don't reveal your role too early or wolves will kill you!",
            "night_tips": "Choose one suspect to investigate their true alignment.",
            "pro_tip": "Beware: The Alpha Wolf appears Good, while the Serial Killer appears Evil! Watson knows your identity and will try to protect you.",
        },
    },
    "doctor": {
        "id": "doctor",
        "faction": FACTION_TOWN,
        "emoji": "🩺",
        "names": {"werewolf": "Guard / Doctor", "mafia": "Doctor / Medic"},
        "descriptions": {
            "werewolf": "Protects a player from death each night (can choose self). Cannot protect the same target two nights in a row (staggered).",
            "mafia": "Protects a player from death each night (can choose self). Cannot protect the same target two nights in a row (staggered).",
        },
        "night_action": "protect",
        "guide": {
            "objective": "Town: Guard living players from night elimination.",
            "day_tips": "Listen closely to figure out who the Detective is, so you can guard them.",
            "night_tips": "Shield one player from lethal attacks. Cannot guard the same target two nights in a row (staggered protection).",
            "pro_tip": "Guard yourself when in danger; guard confirmed innocents on subsequent nights.",
        },
    },
    "bodyguard": {
        "id": "bodyguard",
        "faction": FACTION_TOWN,
        "emoji": "🛡️",
        "names": {"werewolf": "Bodyguard", "mafia": "Bodyguard"},
        "descriptions": {
            "werewolf": "Protects a player at night from ANY lethal attack (Wolves, Serial Killer, Vigilante). If an evil attack strikes them, or if the Vigilante shoots an evil player you guarded, you intercept the blow and die in their place!",
            "mafia": "Protects a player at night from ANY lethal attack (Mafia, Serial Killer, Vigilante). If an evil attack strikes them, or if the Vigilante shoots an evil player you guarded, you intercept the blow and die in their place!",
        },
        "night_action": "guard_bodyguard",
        "guide": {
            "objective": "Town: Protect a key player with your life against any killer.",
            "day_tips": "Identify the Detective or town leader and stay in the shadows.",
            "night_tips": "Choose a player to guard. If wolves or the Serial Killer strike them, you die in their place. If you guard an innocent citizen from a danger bullet, the Vigilante backfires and you both live!",
            "pro_tip": "Never announce who you are guarding; let killers walk into your shield.",
        },
    },
    "sniper": {
        "id": "sniper",
        "faction": FACTION_TOWN,
        "emoji": "🎯",
        "names": {"werewolf": "Vigilante / Sniper", "mafia": "Vigilante / Hitman"},
        "descriptions": {
            "werewolf": "Can shoot at night to eliminate any bad faction player (Wolves, Serial Killer, Saboteur, Disgruntled Ghost). If you shoot a good citizen or Jester with a danger bullet, you die of guilt! Holding fire earns safe silver bullets.",
            "mafia": "Can shoot at night to eliminate any bad faction player (Mafia, Serial Killer, Saboteur, Disgruntled Ghost). If you shoot an innocent civilian or Fool with a danger bullet, you die of guilt! Holding fire earns safe silver bullets.",
        },
        "night_action": "shoot",
        "guide": {
            "objective": "Town: Hunt down evil threats at night. Bullet count scales with the wolf count.",
            "day_tips": "Watch for deceptive claims or suspicious voting blocks during the day.",
            "night_tips": "Shoot a suspect. Danger bullets backfire if the target is innocent (or Jester). Silver bullets are safe and never backfire.",
            "pro_tip": "Hold your fire for 2 rounds without shooting to earn safe silver bullets!",
        },
    },
    "angel": {
        "id": "angel",
        "faction": FACTION_TOWN,
        "emoji": "👼",
        "names": {"werewolf": "Angel", "mafia": "Angel"},
        "descriptions": {
            "werewolf": "Limbo guardian. Players sent to Limbo get one chance total to guess who you are to resurrect. Souls in Limbo cannot speak. If you perish, future deaths skip Limbo secretly.",
            "mafia": "Limbo guardian. Players sent to Limbo get one chance total to guess who you are to resurrect. Souls in Limbo cannot speak. If you perish, future deaths skip Limbo secretly.",
        },
        "night_action": None,
        "guide": {
            "objective": "Town: Stay alive so souls sent to Limbo can guess your identity and resurrect.",
            "day_tips": "Drop subtle hints to townspeople you trust so they know who to guess if sent to Limbo.",
            "night_tips": "Sleep safely. Souls in Limbo cannot speak and have only 1 total guess to return. If you die, Limbo ends secretly without tipping off the wolves!",
            "pro_tip": "If wolves figure out you are the Angel, they will eliminate you immediately to stop revivals.",
        },
    },
    "mayor": {
        "id": "mayor",
        "faction": FACTION_TOWN,
        "emoji": "👨‍⚖️",
        "names": {"werewolf": "Mayor", "mafia": "Mayor"},
        "descriptions": {
            "werewolf": "Leader of the town. Public Mayor cannot be voted out by town execution and has double voting power (2x). Hidden Mayor remains secret, has 1x vote, and can veto an execution at night once per person.",
            "mafia": "Leader of the city. Public Mayor cannot be voted out by town execution and has double voting power (2x). Hidden Mayor remains secret, has 1x vote, and can veto an execution at night once per person.",
        },
        "night_action": "veto",
        "guide": {
            "objective": "Town: Lead the town and protect innocents. Public Mayor cannot be voted out and has double vote!",
            "day_tips": "As Public Mayor, you cannot be voted out by town execution and your vote counts as 2! As Hidden Mayor, stay secret and use normal 1x voting.",
            "night_tips": "If an executed player was innocent, you can exercise an official veto to pardon them. You can pardon multiple players across the game, but each player only once!",
            "pro_tip": "Save your veto for a confirmed innocent or critical power role like the Detective.",
        },
    },
    "witch": {
        "id": "witch",
        "faction": FACTION_TOWN,
        "emoji": "🧙‍♀️",
        "names": {"werewolf": "Witch", "mafia": "Chemist"},
        "descriptions": {
            "werewolf": "Possesses two 1-time potions: one revival potion and one lethal poison. Can only brew while alive (cannot brew from Limbo or death; cannot self-heal). If attacked tonight, your potions still resolve at dawn!",
            "mafia": "Possesses two 1-time potions: one revival potion and one lethal poison. Can only brew while alive (cannot brew from Limbo or death; cannot self-heal). If attacked tonight, your potions still resolve at dawn!",
        },
        "night_action": "potion",
        "guide": {
            "objective": "Town: Use your two powerful potions at crucial turning points.",
            "day_tips": "Keep quiet about your potion inventory.",
            "night_tips": "You have 1 revival potion (restores a soul from Limbo) and 1 poison potion (kills any living player). Even if you are attacked tonight, your potions still take effect at dawn!",
            "pro_tip": "Use poison when you are confident someone is an evil wolf who avoided day execution.",
        },
    },
    "lover": {
        "id": "lover",
        "faction": FACTION_TOWN,
        "emoji": "💞",
        "names": {"werewolf": "Innocent Lovers (New Couple)", "mafia": "Innocent Lovers (New Couple)"},
        "descriptions": {
            "werewolf": "Two innocent Citizens bound in love from the start. You know each other's identity and win with the Town. If one dies, both perish!",
            "mafia": "Two innocent Civilians bound in love from the start. You know each other's identity and win with the Town. If one dies, both perish!",
        },
        "night_action": None,
        "guide": {
            "objective": "Town / Citizen: Eliminate all evil! Form a reliable 2-vote block with your lover to sway daytime trials.",
            "day_tips": "Coordinate votes with your lover. Keep your connection discreet so wolves don't target you for a 2-for-1 kill!",
            "night_tips": "Sleep safely. You have no night powers, but pray you both survive the night.",
            "pro_tip": "You can 100% trust your lover as a fellow innocent Citizen. Protect each other's secrets!",
        },
    },
    "cupid": {
        "id": "cupid",
        "faction": FACTION_NEUTRAL,
        "emoji": "🏹",
        "names": {"werewolf": "Cupid (Matchmaker)", "mafia": "Cupid (Matchmaker)"},
        "descriptions": {
            "werewolf": "On Night 0, binds two players into Obsessive Lovers. Bound by obsession, they only win if everyone else dies!",
            "mafia": "On Night 0, binds two players into Obsessive Lovers. Bound by obsession, they only win if everyone else dies!",
        },
        "night_action": "link_lovers",
        "guide": {
            "objective": "Neutral: Link two players into Obsessive Lovers whose only win condition is being the last survivors.",
            "day_tips": "Observe how your chosen lovers behave and protect their secret bond.",
            "night_tips": "On Night 0 only, select two players to bind as obsessive lovers.",
            "pro_tip": "Binding a Wolf to a Villager creates an exciting romance that flips the game!",
        },
    },
    "obsessive_lover": {
        "id": "obsessive_lover",
        "faction": FACTION_NEUTRAL,
        "emoji": "❤️‍🔥",
        "enabled": False,  # Status/condition applied by Cupid, not a dealable deck card
        "names": {"werewolf": "Obsessive Lover (Cupid Victim)", "mafia": "Obsessive Lover (Cupid Victim)"},
        "descriptions": {
            "werewolf": "Stricken by Cupid's arrow. You and your partner are so obsessed that you abandon your factions: you only win if everyone else is eliminated!",
            "mafia": "Stricken by Cupid's arrow. You and your partner are so obsessed that you abandon your factions: you only win if everyone else is eliminated!",
        },
        "night_action": None,
        "guide": {
            "objective": "Neutral Lovers: Cupid's spell binds you. Outlive all other players to claim mutual victory!",
            "day_tips": "Work secretly with your lover. Vote down both town and wolves.",
            "night_tips": "Protect each other. If one dies, both perish of a broken heart!",
            "pro_tip": "You win if you and your lover are the last two players alive.",
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
            "werewolf": "A solo killer independent of the pack. Wakes each night to eliminate a victim. Wins instantly if all wolves perish!",
            "mafia": "A solo killer independent of the family. Wakes each night to eliminate a victim. Wins instantly if all mafia perish!",
        },
        "night_action": "solo_kill",
        "guide": {
            "objective": "Neutral Solo: Outlive the wolves! If all wolves are eliminated while you survive, you achieve instant solo victory. You can even resurrect from Limbo!",
            "day_tips": "Act like an ordinary villager. Eliminate wolves by day and pick off town by night.",
            "night_tips": "Select a player to eliminate secretly in the shadows.",
            "pro_tip": "Target vocal players or wolves; let Town and Wolves tear each other apart while you clean up.",
        },
    },
    "death_angel": {
        "id": "death_angel",
        "faction": FACTION_TOWN,
        "emoji": "💀",
        "names": {"werewolf": "Death Angel (Limbo Executioner)", "mafia": "Angel of Death"},
        "descriptions": {
            "werewolf": "Aligned with Good. Can strike a soul lingering in Limbo to kill them permanently. Can act even while in Limbo! Reverts to Citizen if no Angel in play.",
            "mafia": "Aligned with Good. Can strike a soul lingering in Limbo to kill them permanently. Can act even while in Limbo! Reverts to Civilian if no Angel in play.",
        },
        "night_action": "kill_limbo",
        "guide": {
            "objective": "Town: Cleanse Limbo of dangerous or suspicious souls so they cannot resurrect.",
            "day_tips": "Pay attention to who entered Limbo. Coordinate with town on whether that soul is trustworthy.",
            "night_tips": "You may strike once per game to permanently extinguish a soul in Limbo (even if you are in Limbo yourself!). If the room has no Angel, you are a regular Citizen.",
            "pro_tip": "If a suspected werewolf or serial killer is in Limbo trying to guess the Angel, strike them before they get lucky!",
        },
    },
    "wolf_hunter": {
        "id": "wolf_hunter",
        "faction": FACTION_NEUTRAL,
        "emoji": "🏹🐺",
        "names": {"werewolf": "Wolf Hunter (Lone Vigilante)", "mafia": "Mob Hunter"},
        "descriptions": {
            "werewolf": "Solo hunter. Can strike a player at night: if the target is a Werewolf, the wolf dies. If the target is NOT a werewolf, the hunter dies of backfire instead!",
            "mafia": "Solo hunter. Can strike a player at night: if the target is Mafia, the mobster dies. If the target is NOT Mafia, the hunter dies of backfire instead!",
        },
        "night_action": "hunt_wolf",
        "guide": {
            "objective": "Eliminate the Werewolves! Strike evil with deadly precision. A miscalculation will cost your life.",
            "day_tips": "Observe player behavior closely. You can only strike at night when you are 100% sure your target is a Wolf.",
            "night_tips": "Select a suspected Wolf. If they are a Werewolf, they die. If they are innocent or independent, your weapon backfires and you die!",
            "pro_tip": "Never guess randomly. Wait for Detective clues, slip-ups, or solid voting evidence before pulling the trigger.",
        },
    },
    "traveler": {
        "id": "traveler",
        "faction": FACTION_TOWN,
        "emoji": "🧳",
        "midgame_only": True,  # Added only mid-game by moderator
        "names": {"werewolf": "Traveler (Confirmed Good)", "mafia": "Traveler (Confirmed Good)"},
        "descriptions": {
            "werewolf": "A mid-game arrival on the side of good. Has no night powers, but everyone publicly knows they are confirmed good!",
            "mafia": "A mid-game arrival on the side of good. Has no night powers, but everyone publicly knows they are confirmed good!",
        },
        "night_action": None,
        "guide": {
            "objective": "Town: You are a confirmed innocent traveler! Help the town coordinate trusted discussions.",
            "day_tips": "Lead discussions and help organize town votes. Everyone knows you are 100% good!",
            "night_tips": "Sleep peacefully. Watch the morning report carefully.",
            "pro_tip": "Since everyone knows you are clean, your voice holds tremendous weight at the table.",
        },
    },
    "ghost": {
        "id": "ghost",
        "faction": FACTION_TOWN,
        "emoji": "👻",
        "midgame_only": True,  # Added only mid-game by moderator
        "names": {"werewolf": "Ghost (Town Spirit)", "mafia": "Ghost (Town Spirit)"},
        "descriptions": {
            "werewolf": "A traveler who died immediately upon arrival. Cannot vote or die. Can haunt a player at night and leave a spectral message for the town (moderator approved).",
            "mafia": "A traveler who died immediately upon arrival. Cannot vote or die. Can haunt a player at night and leave a spectral message for the town (moderator approved).",
        },
        "night_action": "ghost_haunt",
        "guide": {
            "objective": "Town Spirit: Guide the living to victory from beyond the veil!",
            "day_tips": "You cannot vote, but your approved spectral messages appear at dawn to guide discussions.",
            "night_tips": "Choose a player to haunt, and submit a message for the Game Master to broadcast at dawn.",
            "pro_tip": "Leave cryptic or insightful clues about voting patterns to help the living deduce the wolves.",
        },
    },
    "disgruntled_ghost": {
        "id": "disgruntled_ghost",
        "faction": FACTION_NEUTRAL,
        "emoji": "👿",
        "midgame_only": True,  # Added only mid-game by moderator
        "names": {"werewolf": "Disgruntled Ghost", "mafia": "Vengeful Spirit"},
        "descriptions": {
            "werewolf": "A spiteful spirit who cannot vote or die. Wakes early each night to hunt a player and suppress their powers for that night!",
            "mafia": "A spiteful spirit who cannot vote or die. Wakes early each night to hunt a player and suppress their powers for that night!",
        },
        "night_action": "suppress_power",
        "guide": {
            "objective": "Spiteful Spirit: Interfere with players and suppress their abilities before they can act!",
            "day_tips": "Watch how suppressed players react when their night powers fail.",
            "night_tips": "You are called early in the night. Select a player to suppress their powers for the night.",
            "pro_tip": "Suppress suspected power roles like the Doctor, Detective, or Vigilante to create chaos.",
        },
    },
    "saboteur_wolf": {
        "id": "saboteur_wolf",
        "faction": FACTION_WOLVES,
        "emoji": "🐺⚡",
        "names": {"werewolf": "Saboteur Wolf", "mafia": "Mafia Saboteur"},
        "descriptions": {
            "werewolf": "Werewolf pack member. Once per game, can target a citizen at night to suppress their power and steal it (revealing their role to the pack)!",
            "mafia": "Mafia family member. Once per game, can target a civilian at night to suppress their power and steal it (revealing their role to the family)!",
        },
        "night_action": "sabotage",
        "guide": {
            "objective": "Evil: Coordinate with wolves. Use your 1-time sabotage to neutralize a critical town power role and learn their identity.",
            "day_tips": "Blend in with the pack. Share stolen role intelligence with your teammates.",
            "night_tips": "Trigger your one-time sabotage when you suspect a powerful town role is about to strike.",
            "pro_tip": "Sabotaging the Detective or Vigilante completely disarms them for the night while exposing their identity to you!",
        },
    },
    "hacker": {
        "id": "hacker",
        "faction": FACTION_TOWN,
        "emoji": "💻",
        "names": {"werewolf": "Hacker (Analyst)", "mafia": "Hacker (Informant)"},
        "descriptions": {
            "werewolf": "On Night 1, scans a group of players. At dawn on Day 1, announces the evil ratio (Majority, Minority, Even, All Bad, or Clean). Day 1 has introductions only (no voting)!",
            "mafia": "On Night 1, scans a group of players. At dawn on Day 1, announces the evil ratio (Majority, Minority, Even, All Bad, or Clean). Day 1 has introductions only (no voting)!",
        },
        "night_action": "hack_scan",
        "guide": {
            "objective": "Town: Scan a group on Night 1 to establish yourself as confirmed town and jumpstart daytime deduction.",
            "day_tips": "Share the group you scanned and analyze the evil ratio with the town during Day 1 introductions.",
            "night_tips": "On Night 1 only, select a group of players to scan.",
            "pro_tip": "Scanning suspected leaders or quiet players gives immediate mathematical leverage to the town.",
        },
    },
    "watson": {
        "id": "watson",
        "faction": FACTION_TOWN,
        "emoji": "🕵️‍♂️",
        "names": {"werewolf": "Watson (Detective Helper)", "mafia": "Deputy (Cop Helper)"},
        "descriptions": {
            "werewolf": "Loyal assistant who knows who the Detective is from the start. Cover up for them, deflect suspicion, and keep them alive!",
            "mafia": "Loyal assistant who knows who the Detective is from the start. Cover up for them, deflect suspicion, and keep them alive!",
        },
        "night_action": None,
        "guide": {
            "objective": "Town: You know the Detective's identity! Protect them during discussion and make sure town doesn't vote them out.",
            "day_tips": "Back up the Detective's claims without making it obvious they are the real Detective. Draw wolf attention to yourself if needed!",
            "night_tips": "Sleep safely. You have no night powers, but your daytime protection keeps the town's greatest mind alive.",
            "pro_tip": "If the Detective is in danger of being lynched, stand in the line of fire to defend them!",
        },
    },
    "successor": {
        "id": "successor",
        "faction": FACTION_NEUTRAL,
        "emoji": "⏳",
        "midgame_only": True,  # Added only mid-game by moderator
        "names": {"werewolf": "Successor (Inheritor)", "mafia": "Understudy (Inheritor)"},
        "descriptions": {
            "werewolf": "Mid-game arrival waiting in the wings. Inherits the role, faction, and abilities of the next player who dies. If a lover falls, inherits their place as the new lover, preventing heartbreak!",
            "mafia": "Mid-game arrival waiting in the wings. Inherits the role, faction, and abilities of the next player who dies. If a lover falls, inherits their place as the new lover, preventing heartbreak!",
        },
        "night_action": None,
        "guide": {
            "objective": "Wait until a player falls to inherit their role and faction, then win with that faction.",
            "day_tips": "Observe players closely while you wait so you understand the game board when you step into action.",
            "night_tips": "Watch the night unfold. You will awaken as the role of the next player to fall.",
            "pro_tip": "If a lover is eliminated, stepping in as their successor prevents their partner from dying of heartbreak!",
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
        "night_action": base.get("night_action"),
        "guide": base.get("guide", {}),
        "enabled": base.get("enabled", True),
        "midgame_only": base.get("midgame_only", False),
    }


def get_faction_display(faction: str, theme: str = "werewolf") -> str:
    if faction == FACTION_WOLVES:
        return "Mafia" if theme == "mafia" else "Werewolves"
    if faction == FACTION_TOWN:
        return "Civilians / Town" if theme == "mafia" else "Villagers"
    return "Neutral"


def get_all_roles_catalogue(theme: str = "werewolf", include_midgame: bool = True) -> list[dict[str, Any]]:
    """Return all available roles with localized names, descriptions, and beginner guides.

    Filters out any disabled roles. If include_midgame is False, excludes midgame-only add-ons.
    """
    roles = []
    for role_id, data in ROLE_REGISTRY.items():
        if not data.get("enabled", True):
            continue
        if not include_midgame and data.get("midgame_only", False):
            continue
        roles.append(get_role_info(role_id, theme))
    return roles


def get_all_roles_by_category(theme: str = "werewolf") -> dict[str, list[dict[str, Any]]]:
    """Return enabled roles organized into 4 categories: good, bad, neutral, and addon."""
    cats: dict[str, list[dict[str, Any]]] = {"good": [], "bad": [], "neutral": [], "addon": []}
    for role_id, data in ROLE_REGISTRY.items():
        if not data.get("enabled", True):
            continue
        info = get_role_info(role_id, theme)
        if data.get("midgame_only", False):
            cats["addon"].append(info)
        elif data.get("faction") == FACTION_WOLVES:
            cats["bad"].append(info)
        elif data.get("faction") == FACTION_TOWN:
            cats["good"].append(info)
        else:
            cats["neutral"].append(info)
    return cats


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
        deck.extend(["werewolf"] * num_evil)
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    elif preset in ("standard", "classic", "balanced_8"):
        deck.extend(["werewolf"] * num_evil)
        if count >= 4:
            deck.append("detective")
        if count >= 5:
            deck.append("doctor")
        if count >= 8:
            deck.append("watson")
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    elif preset in ("limbo", "angel"):
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
        if count >= 10:
            deck.append("watson")
        remaining = max(0, count - len(deck))
        deck.extend(["villager"] * remaining)

    elif preset in ("chaos", "full_10", "chaos_12"):
        if num_evil >= 3:
            deck.extend(["werewolf"] * (num_evil - 2))
            deck.append("alpha_wolf")
            deck.append("saboteur_wolf")
        elif num_evil >= 2:
            deck.append("werewolf")
            deck.append("alpha_wolf")
        else:
            deck.append("werewolf")

        specials = [
            "detective",
            "watson",
            "doctor",
            "bodyguard",
            "angel",
            "silencer",
            "sniper",
            "mayor",
            "witch",
            "hacker",
            "death_angel",
            "wolf_hunter",
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
    "standard": ["werewolf", "werewolf", "detective", "doctor", "watson", "villager", "villager"],
    "limbo": ["werewolf", "werewolf", "detective", "doctor", "angel", "sniper", "villager", "villager"],
    "chaos": [
        "werewolf",
        "alpha_wolf",
        "silencer",
        "saboteur_wolf",
        "detective",
        "watson",
        "doctor",
        "bodyguard",
        "angel",
        "sniper",
        "mayor",
        "witch",
        "hacker",
        "death_angel",
        "wolf_hunter",
        "cupid",
        "jester",
        "serial_killer",
        "villager",
    ],
    "quick_5": ["werewolf", "detective", "doctor", "villager", "villager"],
    "balanced_8": ["werewolf", "werewolf", "detective", "doctor", "angel", "sniper", "watson", "villager"],
    "full_10": [
        "werewolf",
        "alpha_wolf",
        "detective",
        "watson",
        "doctor",
        "angel",
        "sniper",
        "mayor",
        "silencer",
        "villager",
    ],
    "chaos_12": [
        "werewolf",
        "alpha_wolf",
        "silencer",
        "saboteur_wolf",
        "detective",
        "watson",
        "doctor",
        "angel",
        "sniper",
        "mayor",
        "witch",
        "hacker",
        "jester",
        "serial_killer",
    ],
}

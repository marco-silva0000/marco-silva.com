# Lupus in Tabula: Werewolf & Mafia Social Deduction Engine

Lupus in Tabula is a digital Game Master assistant and real-time social deduction platform. Designed to eliminate the friction, memorization, and table disputes of running physical Werewolf games, while providing players with interactive secret role cards, night action interfaces, and voting ballots.

---

## 1. Reference

### Core Factions & Victory Conditions
- **Villagers (Good)**: Win when all Werewolves are eliminated.
- **Werewolves (Evil)**: Win when the number of Werewolves equals or exceeds the number of living Villagers.
- **Independent Roles**: Possess unique conditions (e.g., Hamster / Lone Wolf).

### Key Role Directory (`lupus/roles.py`)
- **Seer**: Wakes at night to inspect one player's aura (Human vs Werewolf).
- **Medium**: Discovers whether the player eliminated at the previous day's trial was a Werewolf.
- **Bodyguard**: Protects one player each night against Werewolf attack (cannot pick the same player twice in a row).
- **Werewolf Pack**: Wakes at night to select a victim by consensus.
- **Werewolf Cub**: If killed, the Werewolf pack hunts two victims the following night!
- **Owl**: Chooses one player at night who automatically receives 2 nomination votes at dawn.
- **Possessed**: Human who wins with the Werewolves without knowing their identities.
- **Ghost**: Eliminated players who can submit one moderated spectral message to the living.

### Phase Lifecycle
```
[Lobby] -> [Dealing Roles] -> [Night Phase] -> [Dawn Report]
                                   ^                |
                                   |                v
                            [Night Phase] <- [Day Trial / Verdict]
```

---

## 2. Explanation

### The Digital GM Assistant Philosophy
In traditional Werewolf, the moderator has a high cognitive load: tracking who the Seer pointed to, which target the Bodyguard warded, remembering Werewolf consensus, and tallying split votes.
This engine turns the GM into an empowered director:
- The system automatically prompts roles on their phones in secret.
- The **GM Cockpit** summarizes night actions into a pre-computed Dawn Report.
- The GM can accept the report with one click or apply custom narrative overrides (e.g., saving a player for dramatic effect).

---

## 3. How-To Guides

### How to Moderate a Match with the GM Cockpit
1. Create a room at `/games/create/?game=lupus`.
2. Connect your players via QR code.
3. In the Cockpit, select a role deck preset or customize your deck with the balance meter.
4. Click **Deal Roles** $\rightarrow$ Players receive secret cards on their phones.
5. Click **Start Night** $\rightarrow$ Roles secretly input actions on their devices.
6. Click **Resolve Night** $\rightarrow$ Review the casualty report and announce the dawn to the village!

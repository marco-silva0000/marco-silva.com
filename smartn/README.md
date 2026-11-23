# SmartN: Real-Time Trivia Party Game

SmartN is a real-time multiplayer trivia game built on Django Channels, Redis, and WebSockets. Featuring $N$ covered answers per question card, tactile zero-spoiler reveals, push-your-luck point banking, and couch pass-and-play mechanics.

---

## 1. Reference

### Game Specifications
- **Player Count**: 1 to 16+ players (or couch teams).
- **Match Duration**: 15–25 minutes.
- **Card Question Types**:
  - `true_false`: Items that are factually True or False for the given prompt.
  - `order`: 10 items to arrange in chronological, spatial, or hierarchical sequence (1 to 10).
  - `number`: 10 items with numerical or year answers.
  - `match`: 10 items categorized into groups.
- **Question Packs**: Geography (`geo`), Cinema & Pop Culture (`media`), Science & Nature (`science`), History & Inventions (`history`), Culinary & Food (`food`), Sports & Athletics (`sports`), or All Mixed (`mix`). 164 fact-checked questions.

### Rules of Play
1. **Dealing**: A question card is dealt with a prompt and 10 covered capsules. Slots 1..10 are randomly shuffled.
2. **Taking a Turn**:
   - The active player chooses one covered capsule.
   - For `order` cards, the player selects their predicted sequence position (`#1` through `#10`) from an interactive modal.
   - For other cards, tapping reveals the secret value immediately.
3. **Scoring**:
   - **Correct Answer**: Awards +1 point into the player's round basket. The player remains active.
   - **Incorrect Answer (Bust)**: The player busts, forfeits all unbanked basket points for that card, and is eliminated from the remainder of the round.
4. **Pass & Bank**:
   - On their turn, an active player may choose to **Pass & Bank**. All unbanked basket points are safely transferred into their permanent score, and the player bows out safely for that card.
5. **Round End & Victory**:
   - The round ends when all players have either passed or busted, or when all 10 capsules are opened.
   - The first player to reach the match target score (default: 20 points) wins the match.

### Configuration Options (`settings`)

| Key | Default | Options | Description |
| :--- | :--- | :--- | :--- |
| `target_score` | `20` | `10`, `15`, `20`, `25`, `30` | Points required to win the match. |
| `mode` | `multi_device` | `multi_device`, `single_device` | Multi-phone sync or single-device couch pass & play. |
| `pack` | `mix` | `mix`, `geo`, `science`, `media`, `food`, `sports`, `history` | Question topic theme. |
| `type_filter` | `all` | `all`, `order`, `true_false`, `number`, `match` | Restrict deck to specific question styles. |
| `yes_no_scoring`| `standard` | `standard`, `prediction` | In prediction mode, guessing "No/False" correctly awards +1 pt. |

---

## 2. Explanation

### Push-Your-Luck Psychology
In traditional trivia games, players answer individually with no penalty for guessing. SmartN introduces high-tension risk assessment:
- Do you take an easy point on capsule #1 and pass, banking 1 point safely?
- Or do you risk 3 banked points to guess an obscure #9 rank, knowing a bust wipes out your round's entire earnings?
This dynamic keeps all players invested, as conservative play can be overtaken by a single brave multi-point streak.

### Single-Device Couch Mode Ergonomics
In party settings where not everyone wants to scan a QR code or connect to Wi-Fi:
- A single phone acts as the physical "Smartbox" toy passed between players.
- Prominent banners instruct who holds the device.
- Administrative tools (settings, skips, mid-match additions) are tucked inside a slide-out GM drawer (`#gm-drawer`) so couch players do not see spoilers or settings clutter.

### Direct Outcome Overrides
Trivia debates are common in casual party games. If a player states "1066" verbally on a `number` card or disputes a foreign spelling, the host can tap the revealed capsule and flip the result between Correct (+1 pt) and Bust with zero interruption to game flow.

---

## 3. How-To Guides

### How to Host a Single-Device Couch Match
1. Navigate to `/games/create/?game=smartn` and create a room.
2. Join as Host. In the lobby, click **🛋️ Couch Pass & Play (Single Device)**.
3. Type the names of your friends and click **➕ Add Player**.
4. Click **Start SmartN Match** and pass the phone around the room!

### How to Override an Answer Outcome
1. When a capsule is revealed on the board, tap directly on the capsule row.
2. The **Override Capsule Outcome** modal opens.
3. Click **💥 Mark as WRONG (Bust)** to revoke the point and bust the player, or **✅ Mark as CORRECT (+1 pt)** to validate.

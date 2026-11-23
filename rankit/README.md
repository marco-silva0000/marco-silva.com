# Rank It!: Cooperative Spectrum Party Game

Rank It! is a real-time cooperative party game based on the Japanese sensation *ito*. Players secretly receive numbers from 1 to 100, discuss where their clues land on a subjective spectrum, and cooperatively place cards into a shared timeline in ascending order.

---

## 1. Reference

### Game Specifications
- **Player Count**: 2 to 10 players.
- **Duration**: 10–20 minutes.
- **Card Spectrum**: Numbers 1 to 100 (1 = absolute Minimum, 100 = absolute Maximum).
- **Prompt Themes**: Classic, Everyday Life, Superpowers, Culinary & Food, Scary & Spooky, Deep & Philosophical, and an opt-in 18+ Spicy / NSFW pack.

### Rules of Play
1. **Dealing & The Spectrum**:
   - Each player is dealt secret numbered cards from 1 to 100.
   - A spectrum prompt is displayed (e.g. *1 = Mildest thing on earth $\longleftrightarrow$ 100 = Absolute hottest spice*).
2. **Discussion & Clue Giving**:
   - Players describe their numbers using themed clues.
   - **Golden Rule**: You may NEVER say numbers, percentages, math equations, or reference the 1–100 scale directly!
3. **Placing Cards on the Timeline**:
   - When players feel confident about relative order, they play cards onto the central Timeline.
   - Cards land face-down. Any player can propose swapping positions (`propose_swap`) to fine-tune ordering.
4. **The Reveal**:
   - When all cards are placed, the Host triggers the reveal.
   - Cards flip sequentially from left to right.
   - If every card is higher than or equal to the previous card: **Level Cleared!**
   - Each out-of-order card costs the team **1 Life Heart** (❤️).
5. **Victory & Defeat**:
   - **Victory**: The team clears all target levels (default: 3 levels).
   - **Game Over**: Team lives drop to 0.

### Configuration Options (`settings`)

| Option | Default | Choices | Description |
| :--- | :--- | :--- | :--- |
| `starting_lives` | `3` | `1`, `2`, `3`, `4`, `5` | Team life hearts before defeat. |
| `target_levels` | `3` | `1`, `2`, `3`, `5`, `0 (Endless)` | Levels needed to win. |
| `cards_per_player` | `level_based` | `level_based`, `1`, `2`, `3` | Level-based: Level $N$ deals $N$ cards per player. |
| `pack` | `mix` | `mix`, `classic`, `everyday`, `superpowers`, `food`, `scary`, `deep`, `nsfw` | Topic spectrum pack. |
| `allow_nsfw` | `False` | `True`, `False` | Explicit opt-in for adult 18+ themes. |

---

## 2. Explanation

### Subjective Scale Calibration
The magic of *ito* comes from the subjective variance between human minds:
- To Alice, a "warm summer breeze" might be a 40. To Bob, who hates heat, it might be a 75.
- Through conversational calibration ("Is a ghost pepper hotter than your wasabi?"), the group builds a shared mental model of reality without ever using arithmetic.

### Zero-Spoiler Web Architecture
Unlike physical tabletop games where players can accidentally flash numbers, the web app strictly masks card numbers on the server side:
- A player's phone renders their own secret numbers.
- Other players' devices only receive `number: null` until the Host triggers `reveal_timeline`.
- Timeline cards stay face-down until the animated flip sequence begins.

---

## 3. How-To Guides

### How to Propose and Approve Card Swaps
1. During the discussion phase, any player can tap two face-down timeline cards and click **Propose Swap**.
2. A pulsing yellow swap banner appears on all screens indicating the proposed swap.
3. The Host clicks **Approve Swap** to execute the swap or any player clicks **Reject** to dismiss it.
4. Cards can also be retracted back into hand with **Retract Card** before the reveal.

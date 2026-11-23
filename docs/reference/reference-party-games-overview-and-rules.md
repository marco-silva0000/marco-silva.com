---
title: Reference - Party Games Overview and Rules Matrix
tags: [reference, party-games, specifications, rules, matrix]
created: 2026-11-24
updated: 2026-11-24
---

# Reference: Party Games Overview and Rules Matrix

This document provides a comprehensive technical reference for the nine party game engines deployed on `marco-silva.com`. It details player thresholds, round lifecycle parameters, victory conditions, user interaction modalities, linguistic localization capabilities, and local couch pass-and-play mechanisms.

---

## 1. Universal Platform Game Matrix

| Game Engine | Route Slug | Min / Max Players | Default Round Duration | Victory Condition | Primary Input Style | Content Localization | Couch / Pass-and-Play |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Emojinary** | `emojinary` | 2 / 32 (default 8) | 60s (configurable 30–180s) | Highest cumulative score after configured rounds | Emoji palette canvas placement + real-time text chat guessing | Full content: `en` + Wiktionary lexicon ($\ge 100$ entries) | Spectator screen + mobile chat guessers |
| **Word Impostor** | `impostor` | 3 / 24 (default 8) | Untimed (configurable 30–120s per clue) | Citizens: eliminate Impostor and deny steal. Impostor: survive, outnumber, or steal citizen word. | Secret card peek + text clue / Moderator oral clue log + voting ballot | Full content: `en` + Wiktionary lexicon ($\ge 100$ entries) | Oral Table mode with Moderator clue entry |
| **Codenames** | `codenames` | 2 / 30+ (teams) | Untimed (configurable 30–180s per turn) | First team to reveal all agent words. Instant loss on Assassin (💀) card. | 5×5 tactile card grid + Spymaster clue input + number stepper | Full content: `en` + Wiktionary lexicon ($\ge 100$ entries) | Spymaster/Operative view toggle on shared screen |
| **Stop! (Tutti Frutti)** | `stop` | 2 / 32 (default 8) | 30s base + 10s rush countdown on STOP call | Highest cumulative score across rounds (uniqueness + speed bonus) | Rapid mobile text field entry per category + tactile STOP trigger | Full content: `en` + Wiktionary lexicon ($\ge 100$ entries) | Live public validation grid + community adjudication |
| **Don't Say** | `dontsay` | 2 / 32 (default 8) | 45s (configurable 30–90s) | Classic: Highest score avoiding clashes. The ME: eliminate all guessers (ME) or survive all rounds (Guessers). | Secret text submission + AI validation + Host arbitration modal | Curated packs in `en`, `pt`, `es`, `it`, `fr` | Oral Table mode with living-room elimination |
| **Rank It! (*ito*)** | `rankit` | 2 / 16 (default 8) | Untimed discussion (optional 60/90/120s) | Cooperative: Team clears target levels (1–3+) without losing all lives (hearts ❤️) | Drag-and-drop / click-to-play cards + swap proposal + host reorder | Curated spectrum packs in `en`, `pt`, `es`, `it`, `fr` | Group verbal discussion; face-down placement with consensus swaps |
| **SmartN** | `smartn` | 1 / 32 (default 8) | Untimed turn-based push-your-luck | First player to reach target score (default 20 points) | 10-capsule tactile board + sequence rank modal (#1–#10) + Bank/Pass trigger | Curated trivia decks in `en`, `pt`, `es`, `it`, `fr` | Native Single-Device Couch Pass & Play (`is_couch: true`) |
| **Lupus in Tabula** | `lupus` | 4 / 35+ (default 12) | Discussion: 300s, Defense: 60s, Voting: 45s, Night: GM-paced | Town: eliminate all Wolves & solo killers. Wolves: achieve parity. Solo: specialized win triggers. | GM Cockpit dashboard + player voting ballot + finger-pointing map | Handcrafted narrative cards: 10 languages (`en`, `pt`, `it`, `it-or`, `es`, `fr`, `el`, `ru`, `hi`, `kn`) | Single-device GM Cockpit with circular seating layout |
| **Secret Santa** | `secretsanta` | 2 / 64 (default 12) | Event-driven (Lobby $\to$ Target Draw) | Zero-spoiler bipartite matching satisfying derangement and exclusion graph | Wishlist editor + exclusion selector + 3D wax seal "Tap & Hold" curtain | Full UI and target draw across all site locales | Offline participant mode (`is_offline: true`) with pass-and-play switcher |

---

## 2. Engine Specifications and State Machine Phases

### 2.1 Emojinary (`emojinary`)

- **Player Cardinality**: Minimum 2, maximum 32, default room capacity 8.
- **State Machine Phases**:
  1. `lobby`: Room configuration, player color assignment, mode selection (`round_robin`, `collective`, `best_guess`).
  2. `prep`: Drawer receives secret word and prepares initial canvas layout.
  3. `emoji`: Drawer places emojis onto the canvas grid; timer countdown begins.
  4. `guess`: Guessers type into the live chat feed; fuzzy evaluation matches aliases.
  5. `round_end`: Word revealed, round points tallied, round replay snapshot archived.
  6. `gameover`: Final podium ranking displayed, replay export available (`/replay.json`).
- **Input Modalities**:
  - Drawer: Tap/click on searchable emoji grid (`emojinary/data/emoji_keywords.json`), click to place/remove on canvas, drag reorder.
  - Guesser: Text field with inline debounced keyboard autocomplete (`/emojinary/emoji-search/`).
- **Timing Parameters**:
  - `turn_duration`: 60s default (options: 30s, 45s, 60s, 90s, 120s, 180s).
  - `turn_start_time`: Authoritative server epoch timestamp stored in Redis.
- **Victory Condition**:
  - $\text{Winner} = \arg\max_{p \in P} (\text{Score}(p))$ upon completion of `max_rounds`.

---

### 2.2 Word Impostor (`impostor`)

- **Player Cardinality**: Minimum 3, maximum 24, default room capacity 8.
- **State Machine Phases**:
  1. `lobby`: Setting configuration, category pack selection, player joins.
  2. `clue_giving`: Sequential round-robin clue turns; players speak or submit subtle clues.
  3. `voting`: Group discussion and simultaneous ballot voting to eject a suspect.
  4. `steal`: If the ejected player is an Impostor, a 30s window opens to guess the Citizen word.
  5. `reveal`: Roles, secret words, lethal taboo words, and point deltas revealed.
  6. `gameover`: Match concludes after `max_rounds` (default 5).
- **Poison Modes**:
  - `undercover_blind`: Impostor receives an opposing semantic word without knowing their role.
  - `undercover_informed`: Impostor is informed they are the Impostor and sees their opposing word.
  - `poisoned_citizen`: One loyal citizen ("The Drunk") receives a skewed third word without knowing they are poisoned.
  - `classic_blank`: Impostor receives a blank card (Mr. White) with no word.
- **Input Modalities**:
  - Mobile tactile card: Tap-and-hold to peek with privacy blur.
  - Clue submission: Single text field with anti-spoiler verbatim checks.
  - Moderator oral clue logging: `#clue-speaker-select` with `"by_mod": true`.
  - Voting ballot: Touch list of active suspects.

---

### 2.3 Codenames (`codenames`)

- **Player Cardinality**: Minimum 2 (1v1 duel), recommended 4–12, engine supports up to 30+.
- **Team Allocation**:
  - **Red Team** vs **Blue Team**.
  - Roles per team: exactly 1 **Spymaster** and 1+ **Field Operatives**.
- **Board Configuration**:
  - 5×5 grid containing 25 cards selected from the active word pack.
  - Starting team (chosen randomly): 9 agent cards.
  - Second team: 8 agent cards.
  - Neutral civilians: 7 cards.
  - Assassin (💀): exactly 1 card.
- **State Machine Phases**:
  1. `lobby`: Team selection, Spymaster assignment, pack selection.
  2. `spymaster_clue`: Active Spymaster inputs a one-word clue + number of cards.
  3. `operative_guess`: Operatives discuss and tap cards on the grid.
  4. `gameover`: Triggered immediately when all agents of one team are uncovered or Assassin is chosen.
- **Victory Conditions**:
  - $\text{Win}_{\text{standard}}$: Reveal all assigned agent cards before the opposing team.
  - $\text{Loss}_{\text{instant}}$: Tapping the Assassin card grants immediate victory to the opponent.

---

### 2.4 Stop! / Tutti Frutti (`stop`)

- **Player Cardinality**: Minimum 2, maximum 32, default room capacity 8.
- **Category & Letter Mechanics**:
  - Server randomly selects 1 letter from `EASY_LETTERS` (or `ALL_LETTERS` if configured).
  - 5 categories active per round (drawn from DB categories or Party packs).
- **State Machine Phases**:
  1. `lobby`: Rule configuration, pack toggles, custom category entry.
  2. `playing`: Active round; players type valid words starting with the target letter.
  3. `rush`: Initiated when the first player taps **STOP!**; 10-second synchronized timer starts.
  4. `validation`: Round ends; entries populate the community validation matrix for verification.
  5. `round_summary`: Scores computed and added to cumulative leaderboard.
  6. `gameover`: Match concludes after `max_rounds` (default 8).
- **Input Modalities**:
  - 5 contiguous text fields with letter autofocus and autocomplete disabled.
  - Giant prominent **STOP!** button enabled only when required fields are filled.
  - Host validation grid with direct toggle switches (`valid`, `invalid`, `clash`).

---

### 2.5 Don't Say the Same Thing as Me (`dontsay`)

- **Player Cardinality**: Minimum 2, maximum 32, default room capacity 8.
- **Game Modes**:
  - `classic`: Standard secret anti-clash; players aim to submit unique valid answers.
  - `the_me`: One designated player ("The ME") sets a secret word; other players are eliminated if they match it.
  - `oral_table`: Spoken living-room mode with community adjudication.
- **State Machine Phases**:
  1. `lobby`: Pack selection, collision penalty mode (`classic` vs `harsh`), pacing selection.
  2. `the_me_submitting`: (In `the_me` mode only) "The ME" player locks their forbidden word.
  3. `submitting`: All active players secretly submit one answer.
  4. `revealed`: Answers clustered via fuzzy evaluator; collisions and uniqueness highlighted.
  5. `round_summary`: Points awarded, eliminations logged.
  6. `gameover`: Triggered after `max_rounds` or when elimination conditions are met.

---

### 2.6 Rank It! (*ito*) (`rankit`)

- **Player Cardinality**: Minimum 2, maximum 16, default room capacity 8.
- **Card Pool & Spectrum Mechanics**:
  - Cards drafted from a discrete uniform range: integers $1 \dots 100$ without replacement.
  - Level-based card distribution: Level $L$ deals $L$ cards per player (or fixed 1, 2, 3 cards).
  - Subjective theme drawn from `RANKIT_PROMPTS` (1 = Absolute Minimum, 100 = Absolute Maximum).
- **State Machine Phases**:
  1. `lobby`: Configuration of starting lives, target levels, pack theme.
  2. `staging`: 4-second countdown with card dealing animation.
  3. `playing`: Clue discussion, card placement onto central Timeline, swap proposals.
  4. `level_success`: Timeline revealed in ascending order; level cleared.
  5. `victory`: All target levels cleared with $\ge 1$ life remaining.
  6. `gameover`: Team lives reach 0.

---

### 2.7 SmartN (`smartn`)

- **Player Cardinality**: Minimum 1, maximum 32, default room capacity 8.
- **Card Structure & Trivia Types**:
  - Each question card has exactly $N$ hidden answer items (typically 10 capsules).
  - Supported question types:
    - `order`: Chronological, numerical, or rank ordering (capsules #1 to #10).
    - `true_false`: Fact verification (capsules evaluated as True or False).
    - `number`: Numerical estimation and exact value matching.
    - `match`: Pair associations between prompts and answers.
- **State Machine Phases**:
  1. `lobby`: Mode selection (`multi_device` vs `single_device`), pack selection, target score.
  2. `playing`: Active turn player picks a capsule or banks points.
  3. `round_summary`: Card answers fully revealed; round scores reviewed.
  4. `gameover`: A player attains or exceeds `target_score` (default 20 points).

---

### 2.8 Lupus in Tabula (`lupus`)

- **Player Cardinality**: Minimum 4, maximum 35+, default room capacity 12.
- **Core Factions**:
  - **Town (Villagers / Civilians)**: Objective is elimination of all Werewolves and hostile threats.
  - **Werewolves (Pack / Mafia)**: Objective is parity or majority over living Town.
  - **Neutral / Solitary**: Specialized win triggers (Serial Killer, Jester, Obsessive Lovers).
- **State Machine Phases**:
  1. `lobby`: Seating assignment, deck customization, role balance meter.
  2. `night`: Sequential role actions guided by GM Cockpit script or automated timers.
  3. `dawn`: Death announcement report, Limbo status updates, Mayor veto review.
  4. `day_discussion`: Free-form debate, circular turn order, raised hands.
  5. `day_nomination`: Suspect nomination via hand raise or direct GM tally.
  6. `day_defense`: Nominated suspects give timed defense speeches.
  7. `day_voting`: Secret or public ballot execution trial.
  8. `day_verdict`: Execution announcement, Martyrdom booby trap triggers.
  9. `gameover`: Evaluated by `check_win_condition` across all factions.

---

### 2.9 Secret Santa & Target Matcher (`secretsanta`)

- **Player Cardinality**: Minimum 2, maximum 64, default room capacity 12.
- **Theme Presets**:
  - 🎁 `secretsanta`: Holiday gift exchange with budget, exchange deadline, and wishlist notes.
  - 🎯 `secretassassin`: Party elimination game with secret targets and trigger words.
  - 🤝 `secretbuddy`: Workplace or camp acts of kindness.
  - 🎲 `custom`: General 1-to-1 pairing for challenges or tasks.
- **State Machine Phases**:
  1. `lobby`: Participant registration, exclusion matrix editing, wishlist updates.
  2. `matched`: Derangement executed; secret targets assigned and persisted in Redis.
- **Privacy Controls**:
  - "Tap & Hold to Peek" 3D wax seal curtain preventing shoulder surfing on mobile devices.
  - Offline participant selector allowing single devices to be passed around family members.

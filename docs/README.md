# Party Games Documentation Hub (Diátaxis Architecture)

Welcome to the comprehensive documentation suite for the multiplayer party games platform on `marco-silva.com`.

This documentation is architected strictly according to the **[Diátaxis documentation framework](https://diataxis.fr/)**, separating technical writing into four distinct quadrants based on the reader's mode of interaction:

```
                      Practical Steps / Action
                                 ▲
                                 │
              TUTORIALS          │        HOW-TO GUIDES
          (Learning-oriented)    │     (Problem/Task-oriented)
                                 │
Acquisition of skill ────────────┼──────────── Application of skill
(Study / Learning)               │             (Work / Problem-solving)
                                 │
              EXPLANATION        │          REFERENCE
        (Understanding-oriented) │     (Information-oriented)
                                 │
                                 ▼
                     Theoretical / Cognition
```

---

## 🧭 The 4 Diátaxis Quadrants

### 1. [Tutorials](tutorials/) (*Learning-Oriented Lessons*)
Lessons designed for beginners, guiding them through a zero-friction, step-by-step experience from initial room setup to completing a game round:
- **[Getting Started with Party Games](tutorials/tutorial-getting-started-with-party-games.md)**: A complete first-timer walkthrough for creating a room, inviting friends via QR, and playing a live match.
- **[Hosting Your First Lupus / Werewolf Night](tutorials/tutorial-hosting-your-first-lupus-werewolf-night.md)**: Beginner guide for a new Game Master orchestrating role reveal, the first night phase, and day voting.
- **[Playing SmartN in Couch Mode](tutorials/tutorial-playing-smartn-couch-mode.md)**: How to pass around a single smartphone as the physical "Smartbox" toy during dinner or game night.
- **[Running a Secret Santa Exchange](tutorials/tutorial-running-a-secret-santa-exchange.md)**: Quickstart guide to creating an exchange room, collecting friend wishlists, pairing targets, and peeking privately.

---

### 2. [How-To Guides](how-to/) (*Problem-Oriented Recipes*)
Goal-directed, recipe-style guides for competent organizers, Game Masters, and players solving specific challenges:
- **[How to Host Secret Santa with Exclusions](how-to/how-to-host-secret-santa-with-exclusions.md)**: Setting forbidden pairings (partners, roommates, siblings), custom budgets, and deadline dates.
- **[How to Game Master Lupus with Advanced Roles](how-to/how-to-gamemaster-lupus-werewolf-with-advanced-roles.md)**: Configuring asymmetric roles, running defense speeches, handling ties, and exporting JSON replays.
- **[How to Calibrate Clues in Rank It! (ito)](how-to/how-to-calibrate-clues-in-rank-it-ito.md)**: Discussing subjective spectrums and placing cards from 1 to 100 in ascending order without naming numbers.
- **[How to Run a High-Speed Stop! Race](how-to/how-to-run-high-speed-stop-race.md)**: Customizing category decks, configuring clash penalties, setting timer pressure, and moderating disputes.
- **[How to Play Don't Say Anti-Hivemind](how-to/how-to-play-dontsay-anti-hivemind.md)**: Running both typed and oral/speed modes while avoiding groupthink collisions.
- **[How to Use SmartN GM Drawer & Overrides](how-to/how-to-use-smartn-gm-drawer-and-overrides.md)**: Accessing hidden GM controls, adjusting target points mid-game, adding couch players, and overriding disputed answers.

---

### 3. [Reference](reference/) (*Information-Oriented Specifications*)
Authoritative, dry, and exhaustive technical descriptions of the platform machinery:
- **[Party Games Overview & Rules](reference/reference-party-games-overview-and-rules.md)**: Comprehensive comparison matrix across all 9 games (player counts, duration, win conditions, input styles, language support).
- **[Scoring Formulas & Point Matrices](reference/reference-scoring-formulas-and-point-matrices.md)**: Mathematical scoring formulas for Stop!, Don't Say, SmartN (basket vs permanent points), and Rank It! (lives & life tokens).
- **[Lupus Role Catalogue](reference/reference-lupus-role-catalogue.md)**: Full specification for all 25+ roles (team alignment, aura, night priority order 1..10, action triggers, and win conditions).
- **[Decks & Question Packs Catalogue](reference/reference-decks-and-question-packs.md)**: Complete catalog of question packs across SmartN (164 trivia cards), Rank It! (100 spectrum topics), Stop! categories, and Word Impostor pairs.
- **[Matching Algorithms & Constraints](reference/reference-matching-algorithms-and-constraints.md)**: Mathematical specifications for derangements, directed Hamiltonian cycles ($p_1 \to p_2 \dots \to p_n \to p_1$), and randomized MRV backtracking.
- **[WebSocket Actions & URL Routes](reference/reference-websocket-actions-and-url-routes.md)**: Complete API specification for clean URLs (`/play/`), WebSocket message types, schemas, and session keys.

---

### 4. [Explanation](explanation/) (*Understanding-Oriented Architecture & Essays*)
Deep architectural essays, game theory analysis, and party dynamics:
- **[Party Game Psychology & Group Dynamics](explanation/explanation-party-game-psychology-and-group-dynamics.md)**: Why push-your-luck risk curves (SmartN), consensus calibration (ito), and social deception (Impostor & Lupus) create different party energies.
- **[Anti-Hivemind Game Design](explanation/explanation-anti-hivemind-game-design.md)**: Game theory of collision penalties, and how Levenshtein edit distance and Unicode normalization balance fairness with speed.
- **[Combinatorics of Secret Santa](explanation/explanation-combinatorics-of-secret-santa.md)**: Why naive shuffles fail, why 2-cycles ($A \leftrightarrow B$) ruin gift exchanges, and how directed Hamiltonian cycles guarantee optimal matching.
- **[Zero-Spoiler Security Architecture](explanation/explanation-zero-spoiler-security-architecture.md)**: How server-side projection via `get_sanitized_player_view` on Django Channels prevents unrevealed state from ever reaching client DOM or memory.
- **[Evolution of Party Game URLs & WebSockets](explanation/explanation-evolution-of-party-game-urls.md)**: The architectural transition from legacy name-in-URL paths to clean session-first URLs, and tuning Daphne Redis socket timeouts.

---

## 📚 Foundation for Technical Blog Posts
This documentation hub provides the verified technical foundation for upcoming long-form blog posts on Marco's site covering:
1. *Designing Anti-Hivemind Games: The Joy of Penalizing Groupthink*
2. *The Mathematics of Secret Santa: Directed Hamiltonian Cycles in Practice*
3. *Push-Your-Luck Psychology: Building Real-Time Trivia for Couches & Phones*
4. *Zero-Spoiler Architecture: Securing Real-Time Hidden Role Games with Django Channels*

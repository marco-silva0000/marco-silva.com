# AGENTS.md — codenames (Codenames Deduction Grid Engine)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `codenames/` module.

---

## 1. Overview & Mechanics

`codenames` is a team-based word deduction game:
- Two teams (**Red Team** vs **Blue Team**) compete to identify all of their secret agent words on a 5x5 grid (25 cards).
- **Spymasters**: One Spymaster per team sees the secret affiliations of all 25 cards (Red, Blue, Neutral Civilian, and 1 Assassin).
- **Clue Giving**: The active Spymaster gives a one-word clue followed by a number (e.g. *"Animals: 2"*).
- **Field Operatives**: The team's operatives discuss and tap cards on the board to guess their team's agents.
- **The Assassin (💀)**: Guessing the Assassin card results in **instant loss** for that team!
- **Victory**: First team to reveal all of their agent cards wins the match.

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `codenames/game_state.py` | State lifecycle, Redis persistence, 5x5 grid generation, team assignment, clue state, card reveals, victory check. |
| `codenames/words.py` | Curated multi-language word lists (English, Portuguese, Spanish, etc.) with semantic variety. |
| `codenames/consumers.py` | Async WebSocket consumer handling team selection, Spymaster roles, clue submission, and card clicks. |
| `templates/codenames/game.html` | Client interface, tactile 5x5 grid, Spymaster toggle view, remaining score counters, clue log. |
| `codenames/tests.py` | Unit tests for grid generation, Spymaster projection isolation, turn progression, and assassin triggers. |

---

## 3. Core Architectural Invariants

### 1. Spymaster vs. Operative Zero-Spoiler Projection
In `get_sanitized_player_view`:
- If `viewer_role == "spymaster"` or `phase == "gameover"`:
  - Each card's `affiliation` (`red`, `blue`, `neutral`, `assassin`) is visible.
- If `viewer_role == "operative"`:
  - For unrevealed cards (`card["revealed"] == False`):
    - `affiliation` MUST be set to `None`.
  - Revealed cards retain their true affiliation so the board history is visible.

### 2. Strict Turn Progression & Guess Limits
- Operatives may make up to `clue.number + 1` guesses per turn.
- An incorrect guess (hitting a civilian or opponent card) immediately ends their turn and flips the card.
- Hitting the **Assassin (💀)** card immediately sets `phase = "gameover"`, awarding victory to the opposing team!

### 3. Color-Blind Text Badges
- Cards must render text affiliation tags (`🔴 RED`, `🔵 BLUE`, `⬜ CIVILIAN`, `💀 ASSASSIN`) alongside color backgrounds for accessibility.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`CodenamesConsumer`)

```json
// Join a team and role
{"action": "join_team", "team": "red", "role": "spymaster"}

// Spymaster submits clue
{"action": "submit_clue", "word": "Fruit", "number": 2}

// Operative guesses a card
{"action": "guess_card", "index": 12}

// Operatives pass remaining guesses
{"action": "end_turn"}
```

---

## 5. Test Execution

Run all Codenames tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest codenames/tests.py
```
Lint & Format:
```bash
uv run ruff check codenames/ && uv run ruff format --check codenames/
```

# AGENTS.md — stop (Stop! / Tutti Frutti Speed Category Game)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `stop/` module.

---

## 1. Overview & Mechanics

`stop` is a rapid-fire multiplayer word race based on the classic game *Stop!* (also known as *Basta*, *Tutti Frutti*, or *Categories*):
- Each round selects a random active **Letter** and 5–6 **Categories** (e.g. *Country, Fruit, Animal, Name, Movie*).
- Players race against time to type valid words starting with the letter for each category.
- **The STOP Call**: The first player to finish their sheet taps the giant **STOP!** button, triggering a tense 10-second final countdown rush for all opponents!
- **Scoring & Clash**:
  - Unique valid answer: `+10 points`
  - Clashing valid answer (identical to an opponent's word): `+5 points` (or 0 in Zero Clash mode)
  - Invalid answer: `0 points`
- A shared validation grid displays all entries, allowing host adjudication and community laughter.

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `stop/game_state.py` | State lifecycle, Redis persistence, letter selection, answer normalization, scoring, rush timers. |
| `stop/categories.py` | Category packs (`mix`, `classic`, `kids`, `geography`, `pop_culture`, `geek`), letter validation dictionary. |
| `stop/consumers.py` | Async WebSocket consumer handling real-time inputs, STOP triggers, validation toggles, and scoring. |
| `templates/stop/game.html` | Fast-typing mobile input layout, interactive STOP button, synchronized rush timer, validation grid. |
| `stop/tests.py` | Unit tests for letter validation, word normalization, clash detection, rush countdown, and scoring. |

---

## 3. Core Architectural Invariants

### 1. Guarding Early Round Termination
In `call_stop`:
- Once a player calls STOP and enters the 10-second rush countdown (`phase == "stopped"`), additional calls to STOP must be ignored to prevent canceling the countdown timer early.

### 2. Normalized First Letter Matching
- Answers must begin with the round's designated letter:
  - Account for accents/diacritics (e.g. `É` matches `E`, `Ç` matches `C`) via `starts_with_letter()` in `stop/categories.py`.

### 3. Validation Matrix Projection
- During `revealed` phase, answers are structured into a 2D matrix (`categories x players`) so every player can see what their opponents wrote and arbitrate disputed entries.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`StopConsumer`)

```json
// Submit partial or completed answers dictionary
{"action": "submit_answer", "answers": {"Animal": "Lion", "Country": "Laos"}}

// Player hits STOP!
{"action": "call_stop"}

// Host toggles entry validity
{"action": "toggle_validity", "player_id": "p1", "category": "Fruit"}

// Host toggles clash status
{"action": "toggle_clash", "player_id": "p1", "category": "Fruit"}

// Advance to next round with new letter
{"action": "next_round"}
```

---

## 5. Test Execution

Run all Stop! tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest stop/tests.py
```
Lint & Format:
```bash
uv run ruff check stop/ && uv run ruff format --check stop/
```

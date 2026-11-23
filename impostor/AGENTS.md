# AGENTS.md — impostor (Word Impostor / Undercover Party Game)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `impostor/` module.

---

## 1. Overview & Mechanics

`impostor` is a secret word deduction party game (similar to *Undercover* / *Spyfall*):
- Most players receive a secret **Citizen Word** (e.g. *"Coffee"*).
- One or two players secretly receive an **Impostor Word** (e.g. *"Tea"*) or a blank card (Mr. White).
- In **Poisoned Citizen ("The Drunk") Mode**, one loyal citizen receives a slightly skewed third word without knowing they are poisoned!
- Players take turns giving subtle, one-word or one-phrase clues.
- After clue loops, players vote on who to eliminate.
- **Lethal Word Steal**: If caught, the Impostor has one final opportunity to guess the Citizen word and steal victory!

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `impostor/game_state.py` | State lifecycle, Redis persistence, role assignment, clue cycles, voting tally, lethal word steal. |
| `impostor/consumers.py` | Async WebSocket consumer handling clue submission, voting consensus, steal attempts, and blind redraws. |
| `impostor/word_pairs.py` | Hand-curated semantic word pairs categorized by theme (Food, Objects, Places, Animals, Nature, Pop Culture). |
| `templates/impostor/game.html` | Client interface, secret word reveal card, seating circle, clue history, voting ballot, steal modal. |
| `impostor/tests.py` | Unit tests for role distribution, word pair selection, clue looping, steal attempts, and consensus voting. |

---

## 3. Core Architectural Invariants

### 1. Absolute Secret Word & Role Isolation
In `get_sanitized_player_view`:
- Each client MUST only receive their own assigned card:
  - `view["my_card"]`: Contains the player's secret word and role.
  - Other players' roles and words MUST remain `None` until `phase == "round_summary"` or `gameover`.
- Never expose the Impostor identity or the opposing word in global room broadcasts during `clue_giving` or `voting` phases!

### 2. Poison Word Verbatim Guard
- In `poisoned_citizen` mode, players must be guarded from submitting their secret word verbatim as their clue (`normalize_text(clue) == normalize_text(assigned_word)`).

### 3. Blind Redraw Support
- If players find the current word pair uninspiring, the Host can trigger `blind_redraw`.
- The engine picks a new pair and redistributes roles without revealing either word to the host.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`ImpostorConsumer`)

```json
// Submit text clue
{"action": "submit_clue", "clue": "Roasted beans"}

// Confirm verbal/oral clue was spoken at table
{"action": "spoken_clue"}

// Cast vote against suspect
{"action": "cast_vote", "suspect_id": "p2"}

// Host triggers voting phase
{"action": "start_voting"}

// Impostor attempts lethal word steal
{"action": "submit_steal_guess", "guess": "coffee"}

// Host blind redraws word pair
{"action": "blind_redraw"}
```

---

## 5. Test Execution

Run all Word Impostor tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest impostor/tests.py
```
Lint & Format:
```bash
uv run ruff check impostor/ && uv run ruff format --check impostor/
```

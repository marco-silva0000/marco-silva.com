# AGENTS.md — smartn (Push-Your-Luck Smart Trivia Engine)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `smartn/` module.

---

## 1. Overview & Mechanics

`smartn` is a real-time multiplayer push-your-luck trivia party game engine:
- Each card has $N$ hidden answers (typically 10 capsules) covering a prompt.
- **Push-Your-Luck**: Opening a correct answer adds +1 point to the player's round basket. The player can choose to **Pass & Bank** their basket points safely or continue. Opening an incorrect answer busts the player (losing their basket) and eliminates them for the rest of the card.
- **Order (1 to 10 Sequence) Mode**: Players pick any capsule in any order and select its predicted sequence rank (`#1` to `#N`). Revealed ranks are dynamically disabled.
- **Single-Device Couch Pass & Play**: A single device can be passed around the couch; offline players (`is_couch: true`) participate in the turn order without individual devices.
- **Direct Tap-to-Override**: Host or couch players can tap ANY revealed capsule on ANY question type to open `#modal-override-outcome` and flip the result between `Correct (+1 pt)` and `Wrong (Bust)`.

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `smartn/game_state.py` | State lifecycle, Redis persistence, `pick_capsule`, `pass_turn`, `host_arbitrate`, `_deal_next_card`, `get_sanitized_player_view`. |
| `smartn/consumers.py` | Async WebSocket consumer handling client actions and broadcasting sanitized snapshots. |
| `smartn/questions.py` | Question deck loader, pack filtering (`mix`, `geo`, `science`, `media`, `food`, `sports`, `history`), and type filtering (`order`, `true_false`, `number`, `match`). |
| `smartn/decks/` | Curated fact-checked question banks (`geo.py`, `science.py`, `media.py`, `food.py`, `sports.py`, `history.py`). |
| `templates/smartn/game.html` | High-density tactile frontend, `#modal-order-rank`, `#modal-override-outcome`, GM slide-out drawer, optimistic click locking. |
| `smartn/tests.py` | Unit tests for game flow, zero-spoiler projection, rank picking, couch player management, and outcome overrides. |

---

## 3. Core Architectural Invariants

### 1. Zero-Spoiler State Sanitization
In `get_sanitized_player_view`:
- For every capsule in `state["card"]["items"]`:
  - If the capsule is NOT in `revealed_capsules` and the round is NOT in `round_summary` or `gameover`:
    - `value` MUST be `None`.
    - `is_correct` MUST be `None`.
    - `explanation` MUST be `None`.
    - `guessed_value` MUST be `None`.
- Never broadcast raw card items to clients during the `playing` phase!

### 2. Universal Shuffling on Card Deal
In `_deal_next_card(state)`:
- Items on **all** question types (`order`, `number`, `match`, `true_false`) MUST be shuffled via `random.shuffle(items)` and re-indexed `item["slot"] = idx` ($1 \dots N$).
- Never deal cards in authored order, or chronological year and rank sequence will leak across physical slots 1..10!

### 3. Click Locking & Idempotent Actions
- Frontend must maintain `isPickingSlot = true` during capsule reveal requests with a 3-second failsafe timeout.
- Backend `pick_capsule` and `pass_turn` must handle duplicate rapid clicks idempotently without raising red error toasts.

### 4. No Inline Crown Emojis (`👑`)
- Never render inline crown buttons in `.capsule-actions` or capsule rows. Host arbitration on revealed capsules is triggered by tapping the capsule directly.

### 5. Revealed Capsule Outcome Override
In `host_arbitrate`:
- Must support overriding already revealed capsules.
- Flipping Wrong $\rightarrow$ Correct: Restores player status to `active`, awards +1 pt to round basket (or score in `round_summary`).
- Flipping Correct $\rightarrow$ Wrong: Sets player status to `busted`, resets basket to 0, advances turn if it is that player's turn (or deducts 1 from banked score if in `round_summary`).
- Automatically resolves target player from prior `revealed_by` if `target_player_id` is omitted.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`SmartNConsumer`)

```json
// Pick capsule
{"action": "pick_capsule", "slot": 3, "prediction": "#1"}

// Pass & Bank points
{"action": "pass_turn"}

// Direct outcome override (Host / Couch mode)
{"action": "host_arbitrate", "slot": 1, "mark_correct": false, "target_player_id": "p1"}

// Add offline couch player
{"action": "add_offline_player", "name": "Bob"}

// Update settings (Host only)
{"action": "update_settings", "settings": {"pack": "geo", "type_filter": "order", "mode": "single_device"}}

// Advance round
{"action": "next_round"}

// Reset to lobby
{"action": "reset_game"}
```

---

## 5. Test Execution

Run all SmartN tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest smartn/tests.py
```
Lint & Format:
```bash
uv run ruff check smartn/ && uv run ruff format --check smartn/
```

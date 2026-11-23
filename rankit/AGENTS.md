# AGENTS.md — rankit (Rank It! / ito Cooperative Party Game)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `rankit/` module.

---

## 1. Overview & Mechanics

`rankit` is a real-time cooperative multiplayer party game based on the popular Japanese game *ito*:
- Each player secretly receives numbered cards drafted randomly from 1 to 100 without duplicates.
- The team is presented with a subjective spectrum theme (1 = absolute MIN, 100 = absolute MAX).
- Players communicate clues and relative rankings without ever speaking numbers.
- Players place cards onto the shared central Timeline in perceived ascending order.
- Placed cards remain face-down while the group discusses and proposes swaps.
- Once the group is satisfied, the Host triggers the reveal. The timeline reveals left-to-right. Any descending card loses a team life heart! Surviving all levels clears the game.

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `rankit/game_state.py` | State lifecycle, Redis persistence, `deal_level`, `play_card`, `retract_card`, `propose_swap`, `reveal_timeline`, `get_sanitized_player_view`. |
| `rankit/consumers.py` | Async WebSocket consumer handling client actions and broadcasting sanitized snapshots. |
| `rankit/prompts.py` | Spectrum prompt bank across 7 categories (Classic, Everyday, Superpowers, Food, Scary, Deep, and opt-in 18+ Spicy/NSFW). |
| `templates/rankit/game.html` | Interactive spectrum display, drag-and-drop / click-to-play hand, timeline visualization, swap modal. |
| `rankit/tests.py` | Unit tests for card dealing, zero-spoiler sanitization, swap proposals, timeline reveals, life tracking, and gameover conditions. |

---

## 3. Core Architectural Invariants

### 1. Zero-Spoiler Secret Number Masking
In `get_sanitized_player_view`:
- For every card in each player's `hand`:
  - If `not card.get("played")` and `pid != viewer_id` and `phase not in ("gameover", "victory")`:
    - `card["number"]` MUST be set to `None`.
- For placed cards on the timeline:
  - If `timeline_revealed` is `False` and `phase not in ("gameover", "victory")`:
    - Card number MUST remain hidden to prevent cheating via browser inspection.

### 2. Swap Consensus Engine
- Any player can propose swapping two timeline cards (`propose_swap`, passing `card_id_a` and `card_id_b`).
- Sets `state["pending_swap"] = {"card_id_a": ..., "card_id_b": ..., "proposer_id": ...}`.
- Host approves (`approve_swap`) or any player can dismiss (`reject_swap`).

### 3. Level Progression & Cleared Level Tracking
- Always store `cleared_level` when advancing rounds so modal banners accurately celebrate the cleared level (e.g. "Level 1 Cleared!") while preparing "Level 2".
- Cards dealt per player scales with level if `cards_per_player == "level_based"` (Level 1: 1 card, Level 2: 2 cards, Level 3: 3 cards).

### 4. Opt-In Adult / NSFW Card Guard
- Adult / spicy 18+ prompts are strictly guarded behind `allow_nsfw: True` in settings. Default is `False`. Never deal NSFW prompts unless the host explicitly enables the toggle.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`RankItConsumer`)

```json
// Set textual clue for a card in hand
{"action": "set_clue", "card_id": "c1", "clue": "Room temperature water"}

// Play card onto timeline at index
{"action": "play_card", "card_id": "c1", "index": 0}

// Take card back into hand prior to reveal
{"action": "retract_card", "card_id": "c1"}

// Propose swapping two timeline cards
{"action": "propose_swap", "card_id_a": "c1", "card_id_b": "c2"}

// Host approves swap
{"action": "approve_swap"}

// Reject pending swap
{"action": "reject_swap"}

// Host shifts card left/right on timeline
{"action": "move_timeline_card", "card_id": "c1", "direction": "left"}

// Host initiates timeline reveal
{"action": "reveal_timeline"}

// Host advances to next level
{"action": "play_again"}
```

---

## 5. Test Execution

Run all Rank It! tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest rankit/tests.py
```
Lint & Format:
```bash
uv run ruff check rankit/ && uv run ruff format --check rankit/
```

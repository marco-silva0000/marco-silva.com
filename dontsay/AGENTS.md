# AGENTS.md — dontsay ("Don't Say the Same Thing as Me" Party Game)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `dontsay/` module.

---

## 1. Overview & Mechanics

`dontsay` is an anti-hivemind word collision party game:
- Players receive a category prompt (e.g. *"Name a European capital"*, *"Name a green fruit"*).
- Players secretly submit one answer before the timer expires.
- **Collision Rule**: Players who submit matching or similar answers **clash** and receive 0 points (or -50 in Harsh mode).
- **Uniqueness Rule**: Players who submit unique valid answers score +100 points (+50 obscurity bonus for rare answers).
- **"The ME" Mode**: A designated player ("The ME") submits their answer first. All other players must submit answers that do NOT collide with "The ME". Players who collide with "The ME" are eliminated until 1 survivor remains!

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `dontsay/game_state.py` | State lifecycle, Redis persistence, answer clustering, clash detection, scoring, AI adjudication. |
| `dontsay/consumers.py` | Async WebSocket consumer handling secret submissions, oral rounds, arbitration, and prompt suggestions. |
| `gamerooms/prompt_engine/` | Prompt generation, linguistic synthetics, cardinality brackets, and fuzzy similarity evaluator. |
| `templates/dontsay/game.html` | Client interface, countdown animations, synchronized submission, reveal cards, host arbitration grid. |
| `dontsay/tests.py` | Unit tests for answer clustering, clash detection, "The ME" mode, prompt filtering, and scoring. |

---

## 3. Core Architectural Invariants

### 1. Zero-Spoiler Hidden Submissions
In `get_sanitized_player_view`:
- During `submitting` or `the_me_submitting` phases, no player may see another player's answer text:
  - `answers[other_pid]["raw_answer"]` MUST be `None`.
  - `answers[other_pid]["has_submitted"]` is `True` to show a green checkmark without spoiling content.
- Answers are only revealed during the `revealed` or `round_summary` phases.

### 2. "The ME" Mode Elimination Status
- In `the_me` game mode, eliminated players must receive `"eliminated": True` in `view["viewer"]`.
- The frontend uses this to lock input and display the elimination banner instead of hanging on the answer form.

### 3. Fuzzy Clustering & Similarity Evaluation
- Use `cluster_answer_keys` and `are_similar_answers` from `gamerooms.prompt_engine.evaluator`.
- Normalizes accents, casing, punctuation, and handles plurals (e.g., "apple" vs "apples", "Paris" vs "paris!").
- Host retains manual override authority: `toggle_validity` and `toggle_clash`.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`DontSayConsumer`)

```json
// Submit answer
{"action": "submit_answer", "answer": "Lisbon"}

// "The ME" submits initial trap answer
{"action": "submit_the_me_answer", "answer": "London"}

// Host triggers reveal phase
{"action": "reveal_round"}

// Host toggles clash status on answer
{"action": "toggle_clash", "player_id": "p1"}

// Host toggles validity on answer
{"action": "toggle_validity", "player_id": "p1"}

// Advance to next round
{"action": "next_round"}
```

---

## 5. Test Execution

Run all Don't Say tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest dontsay/tests.py
```
Lint & Format:
```bash
uv run ruff check dontsay/ && uv run ruff format --check dontsay/
```

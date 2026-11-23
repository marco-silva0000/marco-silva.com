# AGENTS.md — emojinary (Emoji Pictionary Party Game Engine)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `emojinary/` module.

---

## 1. Overview & Mechanics

`emojinary` is an emoji-based Pictionary party game:
- One player (the Drawer) receives a secret prompt (e.g. *"Titanic"*, *"Space Station"*, *"Cooking Pizza"*).
- The Drawer can ONLY communicate by placing emojis onto a canvas grid.
- All other players race to type their guesses into chat in real-time.
- The engine performs fuzzy matching against the prompt and aliases; correct guesses score points for both the guesser and the drawer!
- **Game Modes**:
  - `round_robin`: Players rotate drawing turns.
  - `best_guess`: A single secret prompt is given to all drawers simultaneously; players vote on the most expressive sequence.

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `emojinary/game_state.py` | State lifecycle, Redis persistence, prompt generation, round rotation, guess evaluation, scoring. |
| `emojinary/consumers.py` | Async WebSocket consumer handling real-time emoji canvas updates, chat/guess unification, timer pause/resume. |
| `emojinary/emoji_search.py` | Fast emoji semantic search index for client keyboard autocomplete. |
| `templates/emojinary/game.html` | Canvas grid, emoji palette selector, live guess feed, synchronized timer bar. |
| `emojinary/tests.py` | Unit tests for prompt selection, guess evaluation, fuzzy alias matching, and round-robin scoring. |

---

## 3. Core Architectural Invariants

### 1. Secret Word Isolation
In `get_sanitized_player_view`:
- If `viewer_id != drawer_id` and `phase == "guess"`:
  - `state["current_word"]` MUST be masked as `None`.
  - The drawer sees their assigned prompt; guessers only see category hints (e.g. *"Movie"*, *"Object"*).

### 2. Unified Chat / Guess Evaluation
In `_handle_unified_chat_or_guess`:
- During `guess` phase in Round Robin mode, any message typed by an active guesser into the chat input is treated as a **guess attempt**.
- If a chat message contains the secret word (spoiler guard), it must be censored via `censor_spoilers()` before broadcasting to the room.

### 3. Spectator & Disconnection Safety
- Spectators are blocked from drawing emojis or scoring points on guesses.
- If the active drawer disconnects, the engine pauses or skips to the next player without corrupting round counters.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`EmojinaryConsumer`)

```json
// Add emoji to drawing canvas
{"action": "draw_emoji", "emoji": "🚢"}

// Clear drawing canvas
{"action": "clear_canvas"}

// Submit guess
{"action": "guess", "text": "titanic"}

// Admin pauses/resumes timer
{"action": "timer_control", "command": "pause"}
```

---

## 5. Test Execution

Run all Emojinary tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest emojinary/tests.py emojinary/test_scenarios.py
```
Lint & Format:
```bash
uv run ruff check emojinary/ && uv run ruff format --check emojinary/
```

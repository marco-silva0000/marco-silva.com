# AGENTS.md — gamerooms (Shared Party Game Foundation)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `gamerooms/` module.

---

## 1. Overview & Responsibilities

`gamerooms/` provides the shared infrastructure and foundation across all 8 party games in `marco-silva.com`:
- **Room Lifecycle**: Database-backed `Room` model (`gamerooms/models.py`) storing room codes, titles, game types, language, and status.
- **Prompt Engine**: `GamePrompt` model and submission pipeline (`gamerooms/prompt_engine/`) for crowdsourced, curated, and synthetic prompts.
- **Player Colors & Avatars**: Centralized 12-color accessible palette (`PLAYER_PALETTE`), color assignment (`assign_distinct_player_color`), and initials extraction (`get_player_initials`) in `gamerooms/player_colors.py`.
- **QR Code Generation**: Real-time SVG/PNG QR code generator in `gamerooms/qr.py`.
- **Localization**: Language support, locale validation, and direction helpers in `gamerooms/language_support.py`.
- **Security & Rate Limiting**: Input sanitization, token validation, and rate limiting in `gamerooms/security.py`.

---

## 2. Architecture & Key Files

| File | Purpose |
| :--- | :--- |
| `gamerooms/models.py` | `Room` (database room entity with 8-char uppercase code) and `GamePrompt` (trivia & party prompts). |
| `gamerooms/player_colors.py` | `PLAYER_PALETTE` (12 accessible hex codes + contrast colors), initials generator, and color allocation logic. |
| `gamerooms/qr.py` | `generate_qr_svg(url)` and `generate_qr_png_base64(url)` for join codes. |
| `gamerooms/language_support.py` | Supported locales (`en`, `pt`, etc.), normalization, and fallback logic. |
| `gamerooms/security.py` | CSRF guards, room password checks, and spectator token validation. |
| `gamerooms/prompt_engine/` | Dynamic prompt deck manager, cardinality brackets, and fuzzy answer evaluators. |
| `gamerooms/views.py` | Room creation view (`/games/create/`), join view, and QR landing pages. |
| `gamerooms/tests.py` | Unit tests for room creation, player colors, prompts, and security checks. |

---

## 3. Core Invariants & Rules for Agents

1. **Room Codes are 8-Character Uppercase Hex**:
   - `Room.code` is always an 8-character uppercase string (e.g. `2A073334`, `E761C083`).
   - All consumer routing and state lookups must call `code.upper()`.

2. **Zero-Collision Color Allocation**:
   - When a player joins any party game, assign a distinct color via `assign_distinct_player_color(existing_players)` from `gamerooms.player_colors`.
   - Never hardcode arbitrary hex codes into player records. Always use `PLAYER_PALETTE` entries (`hex` and `contrast`).

3. **Database vs. In-Memory State Separation**:
   - `Room` model in SQLite/PostgreSQL is for room registration, discovery, and HTTP entry routing.
   - Live game state (turns, scores, secrets, timer) is strictly stored in **Redis** (or fallback in-memory dictionary) within the specific game engine (`<game>/game_state.py`). Never save transient per-second game state to the Django database!

4. **Prompt Engine Cardinality Brackets**:
   - When handling `GamePrompt`, respect `cardinality_bracket`:
     - `broad` ($N \ge 18$)
     - `medium` ($10 \le N \le 22$)
     - `tight` ($4 \le N \le 12$)
     - `narrow` ($N \le 8$ - Sudden death / high collision)

---

## 4. Test Execution

Run the gamerooms test suite:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest gamerooms/tests.py gamerooms/test_security_fuzz.py
```
Linting:
```bash
uv run ruff check gamerooms/ && uv run ruff format --check gamerooms/
```

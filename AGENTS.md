# Agent Guidelines & Architecture Map — marco-silva.com

This document serves as the master entrypoint, architectural blueprint, and index of agent instructions for all autonomous AI agents and developers working on `marco-silva.com`.

---

## 1. System Overview & Technology Stack

`marco-silva.com` is Marco Silva's production web platform hosted on a single-node **k3s** Kubernetes cluster on Proxmox VM [[115 debian]] (`192.168.1.115`, namespace `marco-silva`):
- **Runtime & Language**: Python 3.13, Django 5.x.
- **ASGI & WebSockets**: Daphne + Django Channels (serving both HTTP and low-latency WebSockets).
- **In-Memory Game State**: Redis with a robust dictionary-based local memory fallback when Redis is absent.
- **Relational Database**: PostgreSQL in production (SQLite supported locally via `USE_SQLITE=1`).
- **CMS & Portfolio**: Wagtail CMS (blog) and `django-photologue` (RAW photo portfolio with EXIF extraction).
- **Personal Tools**: Planz calendar, ICS calendar generator with AI prompt extraction.

---

## 2. Party Game Fleet & Per-Game Knowledge Hubs

The repository features 8 fully independent, real-time party game engines built on top of a shared foundational infrastructure (`gamerooms/`).

Each game directory contains dedicated **Agent Instructions (`AGENTS.md`)** for operational rules, schemas, and invariants, as well as **User Documentation (`README.md`)** adhering to the Diátaxis framework:

| Module | Game Name & Mechanics | Agent Guide | User & Dev Docs |
| :--- | :--- | :--- | :--- |
| **`gamerooms/`** | **Shared Foundation**: Room lifecycle, QR code generator, 12-color accessible palette, GamePrompt engine. | [`gamerooms/AGENTS.md`](gamerooms/AGENTS.md) | [`gamerooms/README.md`](gamerooms/README.md) |
| **`smartn/`** | **SmartN**: 10-capsule push-your-luck trivia, sequence rank picker (1..10), couch pass & play, direct tap outcome overrides. | [`smartn/AGENTS.md`](smartn/AGENTS.md) | [`smartn/README.md`](smartn/README.md) |
| **`rankit/`** | **Rank It! (*ito*)**: Cooperative 1–100 spectrum game, clue discussion, swap consensus, team life hearts, multi-level progression. | [`rankit/AGENTS.md`](rankit/AGENTS.md) | [`rankit/README.md`](rankit/README.md) |
| **`dontsay/`** | **Don't Say**: Anti-hivemind collision, fuzzy clustering, "The ME" elimination mode, trap words, host arbitration. | [`dontsay/AGENTS.md`](dontsay/AGENTS.md) | [`dontsay/README.md`](dontsay/README.md) |
| **`impostor/`** | **Word Impostor**: Secret word deduction, Poisoned Citizen ("The Drunk"), lethal word steal, consensus voting. | [`impostor/AGENTS.md`](impostor/AGENTS.md) | [`impostor/README.md`](impostor/README.md) |
| **`lupus/`** | **Lupus in Tabula**: Werewolf / Mafia engine, 25+ roles, GM Cockpit, circular seating map, dawn report. | [`lupus/AGENTS.md`](lupus/AGENTS.md) | [`lupus/README.md`](lupus/README.md) |
| **`stop/`** | **Stop! (*Tutti Frutti*)**: Rapid category-letter speed race, synchronized rush countdown, validation grid. | [`stop/AGENTS.md`](stop/AGENTS.md) | [`stop/README.md`](stop/README.md) |
| **`codenames/`** | **Codenames**: 5x5 grid deduction, Red vs Blue teams, Spymaster view, Assassin card. | [`codenames/AGENTS.md`](codenames/AGENTS.md) | [`codenames/README.md`](codenames/README.md) |
| **`emojinary/`** | **Emojinary**: Real-time emoji Pictionary, canvas drawing, unified chat/guess evaluation, round-robin rotation. | [`emojinary/AGENTS.md`](emojinary/AGENTS.md) | [`emojinary/README.md`](emojinary/README.md) |

---

## 3. Universal Architectural Invariants

### 1. The Zero-Spoiler Projection Standard
Across all game engines, secret state (e.g. secret words, unrevealed cards, hidden roles, unpicked trivia values) must **NEVER** be broadcast over WebSockets to unauthorized clients.
- Always implement `get_sanitized_player_view(state, viewer_id)` in `game_state.py`.
- Mask secret values with `None` on the server before transmitting JSON. Never rely on CSS `display:none` or client-side JavaScript filtering to hide secrets!

### 2. State Storage & Persistence Separation
- **Persistent Room Data**: Managed via Django models (`Room`, `GamePrompt`) in PostgreSQL/SQLite.
- **Transient Live Game State**: Stored in Redis (keyed by room code) via `get_game(code)` and `save_game(code, state)` in `<game>/game_state.py`. Never create database tables for live round states, turn timers, or baskets.

### 3. Accessible Player Identity & Color Palette
- When players join any game, their avatar color must be allocated via `assign_distinct_player_color(existing_players)` from `gamerooms.player_colors`.
- Initials must be derived via `get_player_initials(name)`.
- Player avatars must be rendered using `renderPlayerAvatarHtml()` or `.player-badge` classes with contrast text.

### 4. Tactile Latency & Click Locking
- Mobile party games suffer from rapid double-tapping. All action buttons (revealing capsules, calling STOP, submitting votes, ending turns) must implement client-side in-flight click locking (e.g. `isPickingSlot = true` with a 3s failsafe timeout).
- Backend consumers must handle duplicate actions idempotently without throwing error banners.

---

## 4. Mandatory Development Protocols

Whenever implementing changes across the repository:

1. **Version Counter & Changelog**:
   - Increment `VERSION_COUNTER` in `website/version.py`.
   - Update `VERSION` in the repo root (e.g. `v171`).
   - Append detailed bullet points in `CHANGELOG.md` under the version header.

2. **Diátaxis Documentation Standard**:
   - All documentation must adhere to the Diátaxis framework (strictly separating Reference, Explanation, How-To, and Tutorials).
   - Zero mode mixing.

3. **Mandatory Test Verification**:
   - Always run the relevant test suite before pushing:
     ```bash
     USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest <game>/tests.py
     ```
   - Run linter and formatting:
     ```bash
     uv run ruff check <game>/ && uv run ruff format --check <game>/
     ```

4. **Homelab Audit Log**:
   - Every system or game feature deployment must be recorded in `~/vault/40 Operations/Action Log.md`.

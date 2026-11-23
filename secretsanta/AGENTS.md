# AGENTS.md — secretsanta (Secret Santa & Target Matcher Engine)

This document contains operational instructions, architecture invariants, matching schemas, and debugging guides for AI coding agents modifying the `secretsanta/` module.

---

## 1. Overview & Mechanics

`secretsanta` is a real-time multiplayer target matching and gift exchange engine:
- **Zero-Spoiler Guarantee**: No participant or observer ever receives another player's secret assignment via WebSocket or DOM. The server strictly strips `matches` and other players' `target_id`.
- **Derangement / Hamiltonian Cycle Engine**: Guarantees zero self-assignments ($\forall p, \text{target}(p) \neq p$). Avoids isolated 2-cycles when $N \ge 3$ by constructing a single unified cycle. Supports custom exclusion graphs (e.g. couples, roommates).
- **Multi-Theme Presets**:
  - 🎁 **Secret Santa**: Holiday gift exchange with spending budget, exchange deadline, and wishlist notes.
  - 🎯 **Secret Assassin**: Party elimination game with secret target and trigger words.
  - 🤝 **Secret Buddy / Angel**: Workplace or camp acts of kindness.
  - 🎲 **Custom / Random Match**: General 1-to-1 pairing for challenges, study buddies, or tasks.
- **"Tap & Hold to Peek" Privacy Shield**: Tactile curtain preventing screen snooping on shared couch devices or group viewing.
- **Offline / Couch Participants**: Allows hosts to register friends/family without individual phones (`is_offline: true`), with a dedicated "Viewing as:" switcher for pass-and-play.

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `secretsanta/game_state.py` | State lifecycle, Redis persistence, `solve_matching`, `generate_matches`, `reset_to_lobby`, `get_sanitized_player_view`, `reveal_all_admin`. |
| `secretsanta/consumers.py` | Async WebSocket consumer handling client actions (`join`, `chat`, `update_wishlist`, `set_exclusions`, `generate_matches`, etc.) and broadcasting sanitized snapshots. |
| `secretsanta/routing.py` | WebSocket URL patterns for `/ws/secretsanta/<str:code>/`. |
| `secretsanta/views.py` | Main room view, personal reconnect redirect, and player QR code generator. |
| `templates/secretsanta/game.html` | Responsive mobile-first interface with 3D wax seal / privacy shield, theme switcher, wishlist editors, and exclusion modals. |
| `secretsanta/tests.py` | Unit tests for matching algorithm, graph exclusions, state mutations, zero-spoiler projection, and WebSocket communication. |

---

## 3. Core Architectural Invariants

### 1. Strict Zero-Spoiler State Sanitization
In `get_sanitized_player_view(state, viewer_id)`:
- `state["matches"]` MUST NEVER be included in the returned dictionary.
- In `view["players"]`, the `target_id` field MUST NOT be present.
- `view["my_target"]` MUST ONLY be populated for `viewer_id` when `state["phase"] == "matched"`.
- If an unauthenticated or spectator client requests state (`viewer_id is None`), `view["my_target"]` is `None`.
- For offline players, `view["offline_targets"]` is ONLY populated if `viewer_id` is an administrator.

### 2. Matching Engine Guarantees (`solve_matching`)
- **No Self-Pairs**: $\forall p, \text{matches}[p] \neq p$.
- **Bijection**: Every participant gives to exactly one person and receives from exactly one person.
- **Exclusion Compliance**: If $q \in \text{exclusions}[p]$, then $\text{matches}[p] \neq q$.
- **Hamiltonian Cycle Priority**: The engine first tries up to 400 random directed Hamiltonian cycle permutations. If graph constraints make a single cycle impossible, it falls back to randomized backtracking with MRV (Minimum Remaining Values) heuristic.
- **Graceful Error Handling**: If exclusions make a valid matching impossible, it returns `(False, "...")` without raising unhandled exceptions or corrupting state.

### 3. Real-Time Wishlist Synchronization
- Players can edit their wishlist before and after matches are drawn.
- When player $B$ updates their wishlist, the giver $A$ (for whom $\text{target}(A) = B$) sees the update immediately on their card via WebSocket broadcast.

### 4. Reconnect & Couch Ergonomics
- Sessions store `secretsanta_player_<CODE>` token.
- Offline players have `is_offline: true`. The host can view their secret cards using the "Couch / Shared Device Envelope Selector".

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`SecretSantaConsumer`)

```json
// Join room
{"action": "join", "name": "Alice", "token": "uuid", "is_admin": true}

// Update personal wishlist
{"action": "update_wishlist", "wishlist": "Books, coffee beans, warm socks"}

// Host: Draw secret matches
{"action": "generate_matches"}

// Host: Add offline couch player
{"action": "add_offline_player", "name": "Grandma"}

// Set pairing exclusions
{"action": "set_exclusions", "player_id": "p_1234", "excluded_ids": ["p_5678"]}

// Host: Update theme or settings
{"action": "update_settings", "settings": {"theme": "assassin", "budget": "20€"}}

// Host: Reset room to lobby
{"action": "reset_to_lobby"}

// Host: Master reveal (emergency inspection)
{"action": "reveal_all_admin"}
```

---

## 5. Verification & Testing

Always run tests before committing changes:

```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest secretsanta/ -v
uv run ruff check secretsanta/
uv run ruff format --check secretsanta/
```

# AGENTS.md — lupus (Lupus in Tabula / Werewolf Social Deduction Engine)

This document contains operational instructions, architecture invariants, and reference schemas for AI coding agents modifying the `lupus/` module.

---

## 1. Overview & Mechanics

`lupus` is a comprehensive social deduction engine based on *Lupus in Tabula* (Werewolf / Mafia):
- **Phases**: `lobby`, `dealing`, `night`, `dawn`, `day_nomination`, `day_defense`, `day_voting`, `day_verdict`, `gameover`.
- **GM Cockpit**: The Game Master possesses a dedicated operational dashboard with manual role overrides, life/death toggles, circular seating visualizer, night action queue, and timer controls.
- **Seating**: Circular / U-table interactive seating map (`figure_u`) with visual pointers, raised hands, and suspect status.
- **Role Ecosystem**: Over 25 specialized roles across Villagers, Werewolves, and Independent Factions (e.g., Seer, Medium, Bodyguard, Possessed, Owl, Werewolf Cub, Martyr, Angel, Detective, Watson).

---

## 2. Key Files Map

| File | Purpose |
| :--- | :--- |
| `lupus/game_state.py` | Core engine (240KB): state transitions, role actions, night queue resolution, voting tallies, victory check. |
| `lupus/roles.py` | Complete role definitions, faction allegiances, night action priorities, and aura checks. |
| `lupus/consumers.py` | Async WebSocket consumer with segregated GM action handlers and player action handlers. |
| `lupus/settings_schema.py` | Deck presets, timer configurations, and role distribution balance meters. |
| `templates/lupus/game.html` | Client UI: GM cockpit tabs, circular table seat nodes, night action modal, voting ballot. |
| `lupus/tests.py` | Massive test suite (235KB) covering night action ordering, role abilities, day trials, and GM overrides. |

---

## 3. Core Architectural Invariants

### 1. Faction & Role Information Masking
In `get_sanitized_player_view`:
- **Regular Players**: Can only see their own role card and team allegiance.
- **Werewolves**: Can see the names and roles of fellow pack members, but not innocent villagers' roles.
- **Dead Players / Spectators**: May see roles only if the GM settings have `reveal_roles_on_death: True`.
- **Game Master (`is_gm: True`)**: Receives the complete unmasked state, including all hidden roles, pending night choices, and private notes.

### 2. Night Action Priority Resolution
Night actions must resolve in strict canonical order in `resolve_night`:
1. Protective wards & Bodyguard saves.
2. Info-gathering roles (Seer, Detective, Medium).
3. Werewolf pack kill consensus.
4. Secondary kills (Sorcerer, Martyrdom).
5. Dawn tally and death announcement.

### 3. Ghost Message Moderation
- Dead players can submit a single ghost message (`submit_ghost_message`).
- It is queued for the GM and must be explicitly approved (`approve_ghost_message`) before broadcasting to living players to prevent unauthorized spoilers.

---

## 4. WebSocket Protocol Reference

### Inbound Actions (`LupusConsumer`)

```json
// GM changes game phase
{"action": "change_phase", "phase": "night"}

// Player performs secret night ability
{"action": "night_action", "target_id": "p4", "action_type": "kill"}

// Player votes during day nomination
{"action": "vote_nominate", "target_id": "p2"}

// Player casts final lynch ballot
{"action": "vote_final", "vote": "guilty"}

// GM resolves night queue into dawn report
{"action": "resolve_night"}

// GM manually toggles player life/death
{"action": "set_status", "player_id": "p3", "alive": false}
```

---

## 5. Test Execution

Run all Lupus tests:
```bash
USE_SQLITE=1 USE_INMEMORY_CHANNELS=1 uv run pytest lupus/tests.py
```
Lint & Format:
```bash
uv run ruff check lupus/ && uv run ruff format --check lupus/
```

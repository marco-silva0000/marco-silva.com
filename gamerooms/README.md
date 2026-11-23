# Gamerooms: Shared Party Game Foundation

`gamerooms` is the foundational Django app powering the party game platform on `marco-silva.com`. It provides room lifecycle management, real-time QR code generation, accessible player color assignment, multi-language routing, and a crowdsourced prompt engine.

---

## 1. Reference

### Models (`gamerooms/models.py`)

#### `Room`
Represents an active game room session.
- `code` (*CharField(8), unique, uppercase*): Public room identifier (e.g., `2A073334`).
- `title` (*CharField(100)*): Human-readable room title.
- `game_type` (*CharField(50)*): Target game engine slug: `codenames`, `dontsay`, `emojinary`, `impostor`, `lupus`, `rankit`, `smartn`, `stop`.
- `language` (*CharField(12)*): Primary room language (e.g., `en`, `pt`).
- `password` (*CharField(100), optional*): Optional room access password.
- `status` (*CharField*): `open`, `running`, or `finished`.
- `max_players` (*PositiveIntegerField*): Capacity limit (default: 8).

#### `GamePrompt`
Centralized question and prompt deck.
- `prompt_id` (*CharField(100), unique*): Identifier prefix (e.g. `sub_...`).
- `text` (*CharField(300)*): Base English prompt text.
- `translations` (*JSONField*): Keyed dictionary `{lang_code: translated_text}`.
- `domain` (*CharField*): `mix`, `geo`, `media`, `food`, `nature`, `history`, `weird`, `custom`.
- `cardinality_bracket` (*CharField*): `broad` ($N \ge 18$), `medium` ($10 \le N \le 22$), `tight` ($4 \le N \le 12$), `narrow` ($N \le 8$).
- `sample_answers` (*JSONField*): Canonical answer list for automated evaluation.
- `status` (*CharField*): `approved`, `pending_review`, `rejected`, `archived`.
- `times_used` (*PositiveIntegerField*): Frequency counter for deck balancing.

### Accessible Player Color Palette (`gamerooms/player_colors.py`)

Contains 12 high-contrast, WCAG-compliant colors ensuring distinct player identification across dark and light game themes:

| Color ID | Hex Code | Name | Contrast Text |
| :--- | :--- | :--- | :--- |
| `crimson` | `#ef4444` | Crimson | `#ffffff` |
| `orange` | `#f97316` | Orange | `#ffffff` |
| `amber` | `#f59e0b` | Amber | `#1f2937` |
| `emerald` | `#10b981` | Emerald | `#ffffff` |
| `teal` | `#14b8a6` | Teal | `#ffffff` |
| `cyan` | `#06b6d4` | Cyan | `#ffffff` |
| `blue` | `#3b82f6` | Blue | `#ffffff` |
| `indigo` | `#6366f1` | Indigo | `#ffffff` |
| `purple` | `#8b5cf6` | Purple | `#ffffff` |
| `pink` | `#ec4899` | Pink | `#ffffff` |
| `rose` | `#f43f5e` | Rose | `#ffffff` |
| `slate` | `#64748b` | Slate | `#ffffff` |

### QR Code Generator (`gamerooms/qr.py`)
- `generate_qr_svg(url: str) -> str`: Returns an inline SVG string for direct template injection.
- `generate_qr_png_base64(url: str) -> str`: Returns base64-encoded PNG data URI for image tags.

---

## 2. Explanation

### In-Memory Redis State vs. Relational Database
Party games require sub-50ms latency for real-time actions (tapping trivia capsules, timer countdowns, live word collision detection). Storing round-by-round state transitions in an ACID relational database introduces table locking, slow disk I/O, and unnecessary write amplification.

Instead, the architecture strictly decouples:
1. **PostgreSQL/SQLite**: Persists only room creation, credentials, and curated prompts.
2. **Redis In-Memory State**: Manages transient active player sets, turns, hands, baskets, and secret cards. If Redis restarts or is unavailable in development, an in-memory dictionary fallback maintains full functionality.

---

## 3. How-To Guides

### How to Assign Distinct Colors to Joining Players
```python
from gamerooms.player_colors import assign_distinct_player_color, get_player_initials

# Inside game state engine:
existing_colors = [p["color"] for p in state["players"]]
new_player_color = assign_distinct_player_color(existing_colors)
new_player_initials = get_player_initials(player_name)
```

### How to Register a New Game Type
1. Add game slug to `Room.game_type` choices in `gamerooms/models.py`.
2. Add routing URL pattern in `gamerooms/urls.py` linking `/games/<slug>/`.
3. Implement the game app under `<slug>/` with its own `game_state.py`, `consumers.py`, and `templates/<slug>/game.html`.

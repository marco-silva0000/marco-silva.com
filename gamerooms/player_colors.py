"""Centralized player color palette, initials extraction, and badge helpers.

Provides shared styling, avatar initials, distinct auto-assigned colors, and
reusable chat formatting across party games.
"""

import re
from typing import Any

PLAYER_PALETTE: tuple[dict[str, str], ...] = (
    {"id": "crimson", "hex": "#ef4444", "name": "Crimson", "contrast": "#ffffff"},
    {"id": "orange", "hex": "#f97316", "name": "Orange", "contrast": "#ffffff"},
    {"id": "amber", "hex": "#f59e0b", "name": "Amber", "contrast": "#1f2937"},
    {"id": "emerald", "hex": "#10b981", "name": "Emerald", "contrast": "#ffffff"},
    {"id": "teal", "hex": "#14b8a6", "name": "Teal", "contrast": "#ffffff"},
    {"id": "cyan", "hex": "#06b6d4", "name": "Cyan", "contrast": "#ffffff"},
    {"id": "blue", "hex": "#3b82f6", "name": "Blue", "contrast": "#ffffff"},
    {"id": "indigo", "hex": "#6366f1", "name": "Indigo", "contrast": "#ffffff"},
    {"id": "purple", "hex": "#8b5cf6", "name": "Purple", "contrast": "#ffffff"},
    {"id": "pink", "hex": "#ec4899", "name": "Pink", "contrast": "#ffffff"},
    {"id": "rose", "hex": "#f43f5e", "name": "Rose", "contrast": "#ffffff"},
    {"id": "slate", "hex": "#64748b", "name": "Slate", "contrast": "#ffffff"},
)

DEFAULT_PLAYER_COLOR = "#3b82f6"
HEX_COLOR_REGEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_valid_color_hex(color_str: str | None) -> bool:
    """Verify whether a string is a valid CSS hex color code."""
    if not color_str:
        return False
    return bool(HEX_COLOR_REGEX.match(color_str.strip()))


def get_player_initials(name: str | None) -> str:
    """Extract clean 1 or 2 letter uppercase initials from a player name.

    Examples:
        'Marco Silva' -> 'MS'
        'Alice Wonder' -> 'AW'
        'Player 1' -> 'P1'
        'Gamer' -> 'G'
        '' -> '?'
    """
    if not name:
        return "?"
    tokens = [re.sub(r"[^a-zA-Z0-9]", "", t) for t in name.strip().split() if t]
    tokens = [t for t in tokens if t]
    if not tokens:
        raw = re.sub(r"[^a-zA-Z0-9]", "", name)
        return raw[0].upper() if raw else "?"
    if len(tokens) == 1:
        first = tokens[0]
        return first[0].upper()
    return (tokens[0][0] + tokens[-1][0]).upper()


def assign_distinct_player_color(existing_players: Any = None) -> str:
    """Assign an unused color from PLAYER_PALETTE to prevent collisions.

    If all 12 colors are occupied, cycles through the palette using player count.
    Accepts a dict of players, a list of player dicts, or a collection of hex strings.
    """
    if not existing_players:
        return PLAYER_PALETTE[0]["hex"]

    used_colors = set()
    count = 0
    if isinstance(existing_players, dict):
        count = len(existing_players)
        for p in existing_players.values():
            if isinstance(p, dict) and p.get("color"):
                used_colors.add(p["color"].lower())
            elif isinstance(p, str):
                used_colors.add(p.lower())
    elif isinstance(existing_players, (list, tuple, set)):
        count = len(existing_players)
        for p in existing_players:
            if isinstance(p, dict) and p.get("color"):
                used_colors.add(p["color"].lower())
            elif isinstance(p, str):
                used_colors.add(p.lower())

    # Find first palette color not currently in use
    for entry in PLAYER_PALETTE:
        if entry["hex"].lower() not in used_colors:
            return entry["hex"]

    # Wrap around if room has more than 12 players
    idx = count % len(PLAYER_PALETTE)
    return PLAYER_PALETTE[idx]["hex"]


def get_color_entry(hex_code: str | None) -> dict[str, str]:
    """Retrieve full palette dictionary or fallback with safe contrast."""
    if not hex_code:
        return PLAYER_PALETTE[0]
    clean = hex_code.strip().lower()
    for entry in PLAYER_PALETTE:
        if entry["hex"].lower() == clean:
            return entry
    return {"id": "custom", "hex": hex_code, "name": "Custom", "contrast": "#ffffff"}

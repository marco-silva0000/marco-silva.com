# Changelog

All notable changes to `marco-silva.com` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v116] - 2026-11-10

### Changed
- **Inline Extended Role Pills for Tuning & Variations**:
  - Replaced separate tuning sub-cards with seamless inline-extending pill chips in the lobby deck builder grid (`.role-toggle-chip.extended`).
  - **Mayor**: Pill extends when active to include an inline mode toggle (`📢 Public (Immune) ⇄` vs `🕵️ Hidden ⇄`).
  - **Sniper / Vigilante**: Pill extends when active to display danger (`💥`) and silver (`✨`) bullet steppers inline.
  - **Angel**: Pill extends when active to include an inline `+🗡️ Death Angel` add-on toggle button.
  - **Serial Killer**: Pill extends when active to toggle between `🔪 Solo Win ⇄` and `🎯 Wolf Hunter ⇄`.
  - Removed separate detached chips for Death Angel and Wolf Hunter, keeping the role selection grid tight, cohesive, and perfectly aligned across mobile and desktop.

## [v115] - 2026-11-10

### Added
- **Pre-Game Role Card Tuning UI**: Integrated role tuning controls directly on role chips/cards in the pre-game deck builder instead of the room creation page:
  - **Vigilante / Sniper Bullets Stepper**: Live steppers for Danger Bullets and Silver Bullets directly under the active Sniper card, automatically syncing to settings and player inventories.
  - **Mayor Variation Selector**: Live toggle between **Public Mayor** and **Hidden Mayor** on the Mayor card.
- **Public Mayor Lynching Immunity**:
  - A Public Mayor cannot be voted out by town execution ("public mayor can't be voted out"). If the Public Mayor receives the highest vote tally, executive immunity activates, the execution fails, and the town proceeds to night peacefully.
  - Public Mayor identity is confirmed publicly to all players and retains double voting power (`2x`).
- **Hidden Mayor Mechanic**:
  - Hidden Mayor keeps their role secret, votes with standard `1x` weight, and can be voted out normally (or exercise their 1-time pardon veto at night).
- **Lobby Grid Additions**: Added `Death Angel` to the Good Team toggle grid and `Wolf Hunter` to the Neutral Team toggle grid with custom pill rendering in the deck roster.

### Changed
- **Create Room Page Streamlining**: Removed danger and silver bullet inputs from `templates/lupus/create.html` in favor of in-lobby role card tuning.
- **Roster Tag Labels**: Dynamic deck roster tags now display tuned parameters (e.g. `🎯 Sniper (1D, 0S)`, `🎖️ Public Mayor`, `🎖️ Hidden Mayor`).

## [v114] - 2026-11-10

### Added
- **Night 0 & Day 0 Initial Sequence**: Introduced peaceful Night 0 (weapons holstered; wolves meet, lovers awaken, Watson identifies Detective, Hacker scans suspects) followed by Day 0 (discussion only, voting locked). Normal lethal night begins on Night 1; Day 1 reveals Hacker intel and unlocks voting.
- **Death Angel Role (`death_angel`)**: Good-aligned role dependent on a living Angel. Can directly strike a player in Limbo to permanent death. Can strike from Limbo! (Demotes to Citizen if room lacks an Angel).
- **Wolf Hunter Role (`wolf_hunter`)**: High-stakes lone hunter. If they strike a wolf at night, the wolf dies; if they strike a non-wolf, the hunter dies of backfire instead.
- **Quantified Role Reveal on Death**: Settings option (`0`: None, `1`: Alignment, `2`: Faction, `3`: Full Role). In Limbo games, revelation strictly triggers on permanent death ("death death"), never during Limbo.
- **Quantified Sniper Ammo**: Separate danger bullets and silver bullets pools configurable in settings and tracked per player inventory.
- **Integrated Limbo Night Stage (`limbo_angel_guess`)**: Dedicated night stage before Dawn Review where the GM processes limbo souls one-by-one for their Angel guess. If the Angel is dead, all remaining limbo souls pass permanently to death at dawn.
- **Real-Time Player Pointing**: Players can point at other players from mobile (`Alice 👉 Bob`); displayed live in the GM cockpit and auto-cleared on phase/stage shifts.
- **GM Coroner's Report / Gazette Leak**: Game Master can leak a fallen player's alignment or full role directly to the Town Gazette.
- **Tutorial Categorization**: Grouped all roles in the tutorial into 4 distinct categories: 🟢 Good, 🔴 Bad, 🟡 Neutral/Solo, and 🟣 Add-on/Midgame.

### Changed
- **Simplified Alignment Wording**: Simplified Detective inspection and logs from `"Good / Innocent"` to `"Good"` and `"Evil / Enemy"` to `"Evil"`.
- **Cupid & Lovers Cleanup**: Removed duplicate `obsessive_lover` from dealable decks; Cupid creates obsessive lovers dynamically while `lover` represents starting Innocent Lovers.
- **Midgame Add-ons Segregation**: Marked `traveler`, `ghost`, `disgruntled_ghost`, and `successor` as midgame-only, preventing them from being dealt in pre-game decks.
- **Unassigned Role Card**: Hidden the "How to Play My Role" guide button when a player has no role assigned.

## [v113] - 2026-11-10
- Active rooms hub at `/games/lupus/` and `/lupus/` redirects.
- Demo players named after their roles with lobby role pre-assignment & name-based auto-assignment.
- Danger bullet backfire fix (shooter dies of guilt, innocent target survives unharmed).

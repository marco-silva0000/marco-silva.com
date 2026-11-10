# Changelog

All notable changes to `marco-silva.com` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

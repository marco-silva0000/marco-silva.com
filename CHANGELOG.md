# Changelog

All notable changes to `marco-silva.com` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v120] - 2026-11-10

### Changed
- **Distinct Role Emojis Across UI and Game State**:
  - **Alpha Wolf (`alpha_wolf`)**: Updated emoji to Gorilla `🦍` (replacing `👑`), distinguishing pack leadership from royalty/host icons.
  - **Framer (`framer`)**: Updated emoji to Face with Spiral Eyes `😵‍💫` (replacing `🎭`), visually highlighting hypnotic misdirection.
  - **Death Angel (`death_angel`)**: Updated emoji to Skull `💀` (replacing `👼🗡️`), cleanly signifying execution of souls hovering in Limbo.
  - **Mayor (`mayor`)**: Updated emoji to Man Judge `👨‍⚖️` (replacing `🎖️`), reinforcing daytime executive voting authority and immunity.
  - **Distinguished Lover Emojis**:
    - **Innocent Lovers (`lover`)**: Revolving Hearts `💞` for the bonded Town citizen couple across deck chips, pre-assign modal, night stages, table nodes, and secret notes.
    - **Cupid (`cupid`)**: Bow & Arrow `🏹` for the neutral matchmaker who binds obsessive lovers.
    - **Obsessive Lovers (`obsessive_lover` / Cupid victims)**: Heart on Fire `❤️‍🔥` across player secret cards, table seat nodes, and victory game over announcements.
    - **Wolf Hunter (`wolf_hunter`)**: Bow & Wolf `🏹🐺` distinguishing solo vigilante hunting from Cupid's matchmaker bow.

## [v119] - 2026-11-10

### Fixed
- **Mayor Veto Status Check**: Fixed conditional evaluation order in the GM night stage view so that when nobody was executed yesterday (`last_lynched_id is None`), it accurately displays `ℹ️ Nobody was executed yesterday. No victim available to pardon.` rather than erroneously warning that the Mayor had already vetoed the person.
- **Hacker Intel Announcement**: Decoupled Hacker Intel dawn reporting from hardcoded Round 1: Intel is now announced on the dawn immediately following the scan regardless of round number, and marked as announced.
- **Full Resolution Report in Activity Log**: Dawn resolution reports are now systematically appended to the GM Live Activity Log (`state["events_log"]`), detailing all night casualties, Limbo transitions, silenced players, Hacker intel, and Gazette bulletins.

### Added
- **Dual Witch Potions Selection**:
  - Redesigned Witch night interface to feature two dedicated, independent targets:
    - **🧪 Revive Potion**: Restores souls currently in Limbo back to living status (or saves tonight's wolf attack victim).
    - **☠️ Poison Potion**: Targets living players only.
  - The Witch stage is always callable by the GM for natural bluffing and table scripts; if the Witch is not alive, any recorded actions silently no-op during night resolution without revealing dead roles.
- **Final Night Stage Transition**:
  - Transformed the "Next Stage &rarr;" button on the final Dawn Review summary stage into `☀️ Wake Town (Resolve Night)` with green accent styling, executing `resolveNight()` seamlessly.

## [v118] - 2026-11-10

### Added
- **Death Angel Standalone Role Card**:
  - Separated Death Angel from being an Angel add-on into an independent Good Team role card in the deck builder.
  - Removed mandatory Angel requirement / demotion to citizen: Death Angel can now be assigned and dealt in games without an Angel (acting harmlessly like a citizen if no souls enter Limbo).
  - Updated pre-assignment manual modal with complete role listings including Framer and Cupid (Matchmaker).
- **Game History Archiving & Full Gazette Reset**:
  - `return_to_lobby` archives completed games into `state["game_history"]` capturing game number, timestamp, rounds played, winner, and full player rosters with roles, factions, and survival statuses.
  - Gazette submissions (`news_bulletins`, `approved_news_bulletins`), player bulletin limits (`last_news_post_round`, `used_dead_news_bulletin`), and player finger points are thoroughly wiped clean upon returning to the lobby or starting a new game.

### Changed
- **Ring Table Seating with GM Podium**:
  - Streamlined table layouts to exclusively use the open **Ring Table** (with GM podium anchored at the bottom) and the accessible **Card List** view, removing the overlapping Figure U mode.
  - Symmetrically distributed seats along an elliptical arc without corner overcrowding or node overlaps.
- **Eye-Contact / Recognition Night Stages**:
  - Non-targeting night stages (`lovers_meet`, `watson_intro`, `wolves_meet`) are designated as `no_target: True`.
  - GM night stage view hides target selection dropdowns and displays clear visual-check banners (`👀 Visual / Eye-Contact Only (No target action required)`), preventing accidental target registrations when tapping seats.
- **Hacker Night Scheduling**:
  - Hacker scan is strictly scheduled for Round 0 (Night 0) only, with scan intel announced on Day 1 dawn, eliminating redundant Night 1 scan steps.
- **Live Finger Pointers Placement**:
  - Relocated live finger pointers box right inside the Phase & Round controls card for instant visibility when the GM conducts table votes or suspect accusations.

## [v117] - 2026-11-10

### Added
- **Mayor Vote-Canceling Power Toggle (`mayor_can_cancel_vote`)**:
  - Both Public and Hidden Mayors can independently have the power to cancel the vote (executive pardon veto) enabled or disabled.
  - Added inline toggle to Mayor role chip in deck builder (`[ ⚖️ Cancel: ON ⇄ ]` vs `[ 🚫 Cancel: OFF ⇄ ]`).
  - Synced to player role descriptions and night execution veto permissions.
- **Pre-Assignment List & Indicators**:
  - Added missing roles `death_angel` and `wolf_hunter` to pre-assignment role picker modal.
  - Added dynamic status banner in modal showing player's current pre-assignment (`🎯 Currently Pre-assigned` vs `🎲 Random / Unassigned`).
  - Added active highlight (`✓ [Role] [Assigned]`) on current pre-assignment and subtle claimant tags (`[Role] (Pre-assigned: Alice)`) when a role is already claimed by another player at the table.
  - Added live header badge (`🎯 X Pre-assigned`) and seating node highlights (`.u-seat-node.is-preassigned`) on table diagram.
  - Enhanced name auto-assign keywords for `death_angel` ("death angel", "dark angel") and `wolf_hunter` ("wolf hunter", "lone hunter").

### Changed
- **Divider-Based GM Dashboard Layout**:
  - Replaced bulky enclosed card boxes (`.card-box`) with sleek horizontal section dividers (`.gm-section`).
  - Eliminated side whitespace padding to maximize horizontal density for role grids, table seating diagrams, and player controls on both mobile and desktop.

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

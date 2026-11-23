---
title: How to Use SmartN GM Drawer and Overrides
description: Step-by-step instructions for operating the slide-out GM drawer in SmartN, adjusting winning targets, adding couch players mid-match, and overriding capsule outcomes.
tags: [howto, smartn, trivia, couch-mode, gamemaster]
---

# How to Use SmartN GM Drawer and Overrides

This guide explains how to use the Game Master (GM) slide-out drawer and direct capsule override modal in SmartN on `marco-silva.com`. It covers managing single-device couch pass-and-play, adjusting victory score targets, adding offline players mid-game, and correcting disputed trivia answers.

---

## Prerequisites

Before accessing GM controls and overrides:
1. Create a SmartN room at `/games/create/?game=smartn`.
2. Connect as the host at `/games/smartn/<CODE>/play/`.
3. Start a match with at least **1 player** (solo mode) or **2+ players** (couch or multi-device).

---

## Procedure

### Step 1: Open the Slide-Out GM Drawer

The GM drawer is designed to keep host administrative tools hidden from couch players sharing a single phone, preventing spoilers and screen clutter:

1. On the game board screen, tap the **⚙️ GM Controls** button located in the top corner (or invoke `toggleGmDrawer()`).
2. The **GM Slide-Out Drawer** (`#gm-drawer`) animates smoothly from the left edge of the screen.
3. Review the available host quick actions:
   - **📱 Toggle Single Device Mode**: Switch on-the-fly between individual phone sync and single-phone couch pass-and-play.
   - **⏩ Force Next Card / Skip**: Immediately discard an unsuitable or contentious card and deal the next question.
   - **👑 Manual Capsule Override**: Access the global arbitration panel.
   - **🔄 Return to Lobby**: Abort the active match and return all players to room setup.

---

### Step 2: Configure Scoring Targets Mid-Match or in Lobby

1. In the lobby settings (or via the settings drawer):
   - Locate the **Target Score** dropdown (`target_score`).
   - Select the desired victory threshold: `10`, `15`, `20` (Standard), `25`, or `30` points.
2. If playing a casual quick match, lower the target to **10 points** (approx. 2–3 cards).
3. If playing an extended dinner party session, raise the target to **25 or 30 points** (approx. 5–7 cards).
4. Save the setting; the score progress bar on all devices immediately recalculates toward the new goal.

---

### Step 3: Add Offline Couch Players Mid-Match

If a friend arrives late or wants to join after the game has already started:

1. Open the **GM Slide-Out Drawer** (tap **⚙️ GM Controls**).
2. Scroll to the **🛋️ Add Couch Player Mid-Match** section at the bottom of the drawer.
3. Type the new player's name into the input field (e.g., *"Carlos"*).
4. Tap the **➕** button (or press Enter).
5. The player is instantly registered with `is_couch: true`:
   - They appear in the scoreboard with 0 points.
   - They are dynamically inserted into the turn rotation for the current card.
   - The active round, unrevealed capsules, and other players' banked points are preserved without interruption.
6. Tap the **&times;** button at the top of the drawer to close the menu.

---

### Step 4: Correct Disputed Answers Using Direct Capsule Overrides

During trivia play, players often debate technicalities (e.g., a verbal answer was correct but the player tapped the wrong sequence slot in an `order` card, or a date spelling was disputed). SmartN allows hosts to override any revealed capsule directly on the board:

1. On the main game board, identify the revealed capsule in dispute.
2. **Tap directly on the revealed capsule row** (do not look for inline buttons or crowns; tapping the capsule triggers the modal directly).
3. The **⚖️ Override Capsule Outcome** modal (`#modal-override-outcome`) opens.
4. Verify the **Target Player**:
   - The dropdown (`#override-player-select`) automatically defaults to the player who opened this capsule (`revealed_by`).
   - If another player answered verbally on a shared couch, select their name from the dropdown.
5. Apply the desired correction:
   - **To forgive a bust and award a point**:
     - Click **✅ Mark as CORRECT (+1 pt)**.
     - The player's status immediately switches from `busted` back to `active`.
     - +1 point is restored to their round basket.
     - The capsule glows green.
   - **To penalize an invalid guess**:
     - Click **💥 Mark as WRONG (Bust)**.
     - The player's status switches to `busted`.
     - Their round basket resets to 0.
     - The turn advances immediately to the next player in the rotation.
     - The capsule indicator flashes red.
6. The modal closes automatically, and the updated round state is broadcast to all players.

---

## Verification

To verify that GM operations and overrides were applied correctly:
1. **Drawer Addition Check**: Open the scoreboard drawer or view the top roster bar; confirm that the newly added couch player appears in the turn sequence.
2. **Override Status Check**:
   - Inspect the affected capsule on the board: verify that its border reflects the updated state (Green for Correct, Red for Wrong).
   - Check the player's active basket indicator: confirm that +1 point was added or the basket was zeroed out.
   - Confirm that the live event log appends: *"👑 Host arbitrated Slot N: marked as Correct/Wrong"*.

---

## Troubleshooting & Edge Cases

### Accidentally Overriding an Outcome During Round Summary

- **Cause**: An override was applied after all 10 capsules were revealed and the round concluded.
- **System Behavior & Recovery**:
  - The engine's `host_arbitrate` handler supports post-round summary arbitration.
  - When marked Correct in summary, the +1 point applies directly to the player's **permanent match score** (rather than the temporary round basket).
  - When marked Wrong, 1 point is deducted from their permanent score.
  - To undo an accidental click, simply tap the capsule again and click the opposite outcome button.

### Accidental Tap on an Unrevealed Capsule

- **Cause**: The host meant to open the GM drawer but tapped an unrevealed capsule.
- **Safety Guarantee**:
  - Tapping an **unrevealed** covered capsule counts as a gameplay guess for the active player.
  - The outcome override modal (`#modal-override-outcome`) **only opens on already revealed capsules**.
  - Always tap the dedicated **⚙️ GM Controls** button at the top corner to manage room settings without touching board capsules.

### Turn Rotation Skips a Player in Couch Mode

- **Cause**: A couch player was marked busted by mistake and the turn automatically advanced to the next player.
- **Resolution**:
  1. Immediately tap the busted capsule row.
  2. In the override modal, click **✅ Mark as CORRECT (+1 pt)**.
  3. The player is unbusted and returned to `active` standing.
  4. Have the restored player take their next turn or click **Pass & Bank** safely.

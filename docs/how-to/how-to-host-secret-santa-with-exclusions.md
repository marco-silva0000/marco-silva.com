---
title: How to Host Secret Santa with Exclusions
description: Step-by-step instructions for configuring forbidden gift pairings, setting budgets and deadlines, and managing complex exclusion graphs.
tags: [howto, secretsanta, party-games, pairing-engine]
---

# How to Host Secret Santa with Exclusions

This guide explains how to organize a Secret Santa gift exchange on `marco-silva.com`, set up forbidden pairings (spouses, partners, or siblings), specify event parameters (budget and deadline), and resolve graph constraint errors.

---

## Prerequisites

Before configuring exclusions and drawing matches:
1. An active Secret Santa room created via `/games/create/?game=secretsanta`.
2. Host access on the room dashboard (`/games/secretsanta/<CODE>/play/`).
3. At least **3 participants** joined via `/games/<CODE>/` or added as offline couch participants. (Mathematical derangements with exclusions require $N \ge 3$).

---

## Procedure

### Step 1: Access the Organizer Settings

1. In the room lobby, locate the **⚙️ Organizer Settings** panel above the participant roster.
2. In the **Spending Budget** field, input the agreed spending limit (e.g., `25€` or `$30`).
3. In the **Exchange Deadline** field, input the event date or gift reveal deadline (e.g., `2026-12-25`).
4. Select the active theme preset. Verify **🎁 Secret Santa** is selected (or choose **🎯 Secret Assassin** / **🤝 Secret Buddy** if running an alternative event).
5. Click **💾 Update Settings**. The new budget and deadline guidelines broadcast immediately to all connected participant screens.

---

### Step 2: Configure Pairing Exclusions

Exclusions prevent specific participants from drawing one another (for example, partners who share finances or coworkers who exchanged gifts last year). Exclusions in this engine are **directed** ($A \to B$ means "$A$ cannot be assigned to give a gift to $B$").

1. Locate the **Connected Participants** roster table in the lobby.
2. In the participant row for the person you wish to restrict (e.g., Alice), click the **🚫 Excl** button.
3. The **Pairing Exclusions** modal opens for that participant.
4. Check the box next to any participant Alice must not draw (e.g., Bob).
5. Click **Save Exclusions**.
6. **Configure the Reciprocal Pair** (if mutual exclusion is required):
   - By default, excluding Bob from Alice prevents Alice from drawing Bob, but does not prevent Bob from drawing Alice.
   - To make the exclusion mutual, find Bob's row in the roster, click **🚫 Excl**, check the box next to Alice, and click **Save Exclusions**.
7. Repeat this process for any additional pairs (roommates, family members, previous year matches).

> [!NOTE]
> The active exclusion count updates immediately on the participant's row (e.g., `🚫 1 excluded`).

---

### Step 3: Add Offline or Couch Participants (Optional)

If a participant is present in person without a smartphone (such as a child or grandparent):
1. In the lobby, click **➕ Add Offline Player**.
2. Type their display name into the modal input and click **Confirm**.
3. The offline player appears in the roster with an `🛋️ Offline` badge.
4. Open their **🚫 Excl** modal to configure any restrictions following Step 2.

---

### Step 4: Draw Secret Matches

1. Verify that all participants have entered the room and that exclusion counts are accurate.
2. Click the primary action button: **🎲 Draw Secret Matches**.
3. The backend matching algorithm processes the graph:
   - It attempts to construct a single directed **Hamiltonian cycle** ($p_{\pi(1)} \to p_{\pi(2)} \to \dots \to p_{\pi(N)} \to p_{\pi(1)}$) respecting all exclusions.
   - If a single cycle is impossible due to graph topology, it falls back to randomized backtracking with the Minimum Remaining Values (MRV) heuristic.
4. Once completed, the lobby transitions to the **Matched** phase.

---

### Step 5: Verify Assignments Privately

1. Each participant's device updates to show a wax-sealed envelope labeled with their name.
2. Instruct participants to **press and hold** the envelope icon on their phone screen.
   - The wax seal animates open, displaying the name of their recipient and their recipient's live wishlist notes.
   - Releasing the screen instantly snaps the envelope shut, preventing nearby observers from snooping.
3. For offline participants:
   - On the host device, open the **Viewing as:** envelope selector at the bottom of the screen.
   - Select the offline participant's name (e.g., "Grandma").
   - Hand the device to Grandma so she can press and hold to view her secret target privately.

---

## Verification

To confirm that the match completed successfully and that exclusions were honored:

1. **Roster Status Check**: In the host view, verify that every player row displays a green **Matched** badge.
2. **Deterministic Constraint Audit (Admin Only)**:
   - If a participant suspects an algorithm error, the host can scroll to the admin footer and click **🔍 Master Match Audit (Host Only)**.
   - A modal displays the complete assignment table ($A \to B, B \to C, \dots$).
   - Verify that no excluded pairings appear in the assignment table.
   - Close the modal immediately to maintain room secrecy.

---

## Troubleshooting & Edge Cases

### Matching Fails with "Exclusion constraints make a valid draw impossible"

- **Cause**: The exclusion graph is over-constrained. For example, in a 4-person group, if two couples each mutually exclude their partner and cross-exclude another player, no derangement exists without self-pairings.
- **Resolution**:
  1. Click **Dismiss** on the error banner.
  2. Review the roster exclusion counts.
  3. Relax one or more non-essential exclusions (e.g., allow cross-pairings between friends, keeping only direct partner exclusions).
  4. Alternatively, add one or more neutral participants ($N + 1$) to increase graph degrees.
  5. Click **🎲 Draw Secret Matches** again.

### Participant Disconnects or Loses Session Token

- **Cause**: A participant accidentally cleared their mobile browser cache or switched devices.
- **Resolution**:
  1. Have the participant navigate to the room URL (`/games/secretsanta/<CODE>/play/`).
  2. In the participant roster on the host screen, click the **🔗 QR / Reconnect** button next to the disconnected participant.
  3. Have the participant scan their individual reconnect QR code or use the recovery link.
  4. Their browser session re-binds to their unique player token, restoring access to their assigned envelope without requiring a redraw.

### Redrawing Matches After Room Reset

- **Cause**: A new person joined late after matches were already drawn.
- **Resolution**:
  1. In the host admin footer, click **🔄 Reset Room to Lobby**.
  2. All existing matches are cleared; participants return to the lobby view with their wishlists intact.
  3. Have the new participant join via `/games/<CODE>/`.
  4. Configure any necessary exclusions for the new participant.
  5. Click **🎲 Draw Secret Matches** to generate a new valid matching.

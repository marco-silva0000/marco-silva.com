---
title: How to Game Master Lupus with Advanced Roles
description: Step-by-step instructions for orchestrating Lupus in Tabula matches with advanced roles, defense timers, tie-breaker runoffs, and replay export.
tags: [howto, lupus, werewolf, social-deduction, gamemaster]
---

# How to Game Master Lupus with Advanced Roles

This guide explains how to moderate a match of Lupus in Tabula (Werewolf) using the Game Master (GM) Cockpit on `marco-silva.com`. It covers configuring advanced asymmetric roles (Alpha Wolf, Framer, Bodyguard, Medium), conducting timed defense speeches, managing tie-breaker revotes, and exporting the complete game replay.

---

## Prerequisites

Before starting the game session:
1. Create a Lupus room at `/games/create/?game=lupus`.
2. Connect to the room as the designated Game Master (`/games/lupus/<CODE>/play/`).
3. Ensure at least **5 players** have joined via `/games/<CODE>/` or scanned the room QR code. (Matches with advanced roles operate best with 7–16 players).

---

## Procedure

### Step 1: Configure the Role Deck and Asymmetric Powers

1. On the GM Cockpit screen, locate the **Role Deck Configuration** card.
2. Select a base preset (e.g., `Standard Pack`, `Paranoia`, or `Chaos`) or build a custom deck:
   - **Alpha Wolf (`alpha_wolf`)**: Add to evil faction. The Alpha Wolf hunts with the pack but registers as **"Good"** when inspected by the Detective, creating a false-cleared leader.
   - **Cursed Shaman / Framer (`framer`)**: Add to evil faction. Each night, the Framer targets a townsperson. If the Detective inspects that townsperson on the same night, the target registers as **"Evil"**.
   - **Bodyguard (`bodyguard`)**: Add to town faction. Wards one player each night against werewolf attacks (cannot target the same player on consecutive nights).
   - **Detective (`detective`)**: Add to town faction. Inspects one player's aura each night (Good vs Evil).
   - **Medium (`medium`)**: Add to town faction. Inspects the spiritual residue of the player eliminated during the previous day's trial to confirm whether they were a werewolf.
3. Observe the **Balance Meter** at the top of the deck editor. Ensure the net score remains within the **Balanced (-1 to +2)** range.
4. Set rule toggles:
   - **Defense Speech Timer**: Set to `30s` (or `45s` for larger groups).
   - **Max Tie Runoffs**: Set to `1` (standard tournament rule: 1 runoff revote before acquittal).
   - **Reveal Roles on Death**: Toggle `True` (public knowledge) or `False` (hardcore deception).
5. Click **🃏 Deal Roles**. Players receive their secret role cards and tactical guides on their devices.

---

### Step 2: Orchestrate the Night Phase

1. In the GM Cockpit, click **🌙 Start Night**.
2. Announce to the room: *"Night falls on the village. Close your eyes."*
3. The server prompts active night roles simultaneously on their personal devices:
   - Priority 1: Bodyguard selects a player to protect.
   - Priority 2: Framer selects a player to frame.
   - Priority 3: Detective selects a target to inspect.
   - Priority 4: Werewolf pack and Alpha Wolf vote on a consensus kill target.
4. Monitor the **Night Action Queue** in the GM Cockpit. As roles lock in their choices, their status updates with a green checkmark.
5. Once all choices are submitted, click **☀️ Resolve Night**.
6. The engine processes priorities, evaluates protections against kills, and generates the **Dawn Casualty Report**.
7. Click **Announce Dawn**. Read the narrative report aloud to the table (e.g., *"The sun rises. Player Bob was found torn to pieces in the town square."*).

---

### Step 3: Conduct Day Nominations and Timed Defense Speeches

1. Transition to the discussion phase by clicking **🗣️ Open Day Discussion**.
2. Allow 2–3 minutes of open debate among living players.
3. When accusations crystallize, click **⚖️ Open Nominations**.
4. Living players select their prime suspect on their phones. The live nomination tally displays in the Cockpit.
5. When nominations close, the top-voted candidates enter the defense stage:
   - Click **🎤 Proceed to Defense (Candidate 1)**.
   - The server activates the **Defense Banner** on the candidate's phone and starts the **30-second countdown timer**.
   - The candidate speaks without interruption to prove their innocence.
   - If the candidate finishes early, click **Next Defense** to activate the next accused player.
6. Once all nominated candidates have spoken, click **🗳️ Proceed to Final Voting**.

---

### Step 4: Manage Lynch Voting and Tie-Breaker Runoffs

1. During the final vote, all living players choose between the nominated candidates (or vote to Abstain / Skip).
2. Click **Close Polls & Tally**.
3. **Scenario A: Decisive Plurality**
   - The suspect with the most votes is eliminated.
   - If the Medium is in play, their night queue primes to investigate this eliminated player on the upcoming night.
   - Click **Confirm Execution** to proceed to the next night.
4. **Scenario B: First Tie (Runoff Revote)**
   - If two or more candidates receive identical top vote counts, the engine automatically triggers a **Runoff Revote**:
     - The tie counter increments (`voting["tie_count"] = 1`).
     - Non-tied candidates are removed from the ballot.
     - Living players cast a tie-breaker vote exclusively between the tied suspects.
5. **Scenario C: Second Tie (Village Acquittal)**
   - If the runoff vote also results in equal votes, the engine invokes the second tie rule:
     - The verdict displays: `🕊️ No one gets eliminated today (Acquittal on second tie)`.
     - No player is executed.
     - Click **Proceed to Night** to advance the match.

---

### Step 5: Export and Verify Game Replays

After the match concludes (or during an active game for debugging):
1. In your browser address bar on the GM device, navigate to:
   ```
   /games/lupus/<CODE>/export-replay/
   ```
2. The browser automatically downloads a deterministic replay file: `lupus_replay_<code_lower>.json`.
3. To inspect and verify the match tape locally using the CLI:
   ```bash
   python -m lupus.replay --file /path/to/lupus_replay_<code_lower>.json --summary
   ```
4. To verify that all state transitions executed deterministically without rule violations:
   ```bash
   python -m lupus.replay --file /path/to/lupus_replay_<code_lower>.json --verify
   ```
5. To generate a reproducible Robot Framework test suite from the replay:
   ```bash
   python -m lupus.replay --file /path/to/lupus_replay_<code_lower>.json --to-robot tests/robot/lupus/suites/reproduced_game.robot
   ```

---

## Verification

To verify that the match was moderated properly:
1. **Sanitization Check**: Inspect any spectator or dead player's device during the night phase. Verify that unrevealed roles, pending target choices, and wolf votes are masked (`None`).
2. **Deterministic Replay Audit**: Run `python -m lupus.replay --file lupus_replay_<code_lower>.json --verify`.
   - The terminal must output:
     ```
     ✅ Replay verified cleanly! All N player statuses and outcomes match 100%.
     ```

---

## Troubleshooting & Edge Cases

### A Night Action Hangs Because a Player Fell Asleep or Closed Their Phone

- **Cause**: An active night role (e.g., Bodyguard) has disconnected or failed to submit an action, preventing the GM queue from closing.
- **Resolution**:
  1. In the GM Cockpit, open the **Night Override Drawer**.
  2. Find the pending role row with the flashing yellow spinner.
  3. Click **Force Auto-Select (Random)** or **Skip Player Action**.
  4. The queue marks the step complete and enables the **☀️ Resolve Night** button.

### Ghost Player Sends an Inappropriate or Spoilering Message

- **Cause**: Dead players have access to the `submit_ghost_message` channel to send final spectral clues.
- **Resolution**:
  1. Ghost messages do NOT post directly to the village. They enter the GM Cockpit **Pending Ghost Messages** queue.
  2. Review the text:
     - If it contains game-breaking role spoilers, click **🗑️ Reject / Mute Ghost**.
     - If it is thematic roleplay, click **📢 Approve & Broadcast**.

### Overriding a False Lynch Decision

- **Cause**: The GM realizes an unintended vote was submitted due to a misclick, or wants to grant a narrative pardon.
- **Resolution**:
  1. In the GM Cockpit, open the **Roster Management** tab.
  2. Locate the affected player.
  3. Toggle the **Alive / Dead** switch to `Alive`.
  4. The player's device immediately re-enables their daytime discussion and voting interfaces.

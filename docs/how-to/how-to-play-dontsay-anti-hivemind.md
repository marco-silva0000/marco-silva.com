---
title: How to Play Don't Say Anti-Hivemind
description: Step-by-step instructions for hosting Don't Say in both typed and living room oral modes, avoiding groupthink collisions, and scoring anti-hivemind rounds.
tags: [howto, dontsay, word-games, anti-hivemind, party-games]
---

# How to Play Don't Say Anti-Hivemind

This guide explains how to host "Don't Say the Same Thing as Me" on `marco-silva.com`. It covers hosting both synchronized typed mode and oral/speed living-room mode, second-order strategies for avoiding hivemind collisions, and scoring rounds with obscurity bonuses and host arbitration.

---

## Prerequisites

Before starting the round:
1. Create a Don't Say room at `/games/create/?game=dontsay`.
2. Connect as the host at `/games/dontsay/<CODE>/play/`.
3. Connect at least **3 players** (up to 16+) via `/games/<CODE>/` or the room QR code.

---

## Procedure

### Step 1: Select Game Mode and Pacing

1. In the room lobby, open the **⚙️ Game Settings** panel.
2. Select your **Game Mode**:
   - `classic` (Default Typed): Secret typed submissions. Unique answers score **+100 pts** (+50 obscurity bonus). Collisions score **0 pts**.
   - `harsh` (High Stakes Typed): Secret typed submissions. Collisions incur a **-50 pts penalty**.
   - `the_me` (Elimination Typed): A rotating player is designated "The ME" and secretly sets a trap answer. All other players submit answers; anyone who matches "The ME" is eliminated until one champion survives.
   - `oral_table` (Living Room Oral): No typing required on phones. The host reads the prompt aloud, runs a synchronized 3-2-1 verbal countdown, and adjudicates shouted answers directly from the couch.
3. Select your **Category Pacing**:
   - `funnel`: Rounds progressively narrow category cardinality (Wide $\to$ Medium $\to$ Sudden Death Narrow).
   - `narrow`: High-collision narrow categories exclusively (e.g., *"Suits in a deck of cards"*).
   - `random`: Unconstrained category mix.
4. Click **Start Match**.

---

### Step 2: Host Typed Mode (Classic, Harsh, or The ME)

1. The prompt appears on all screens (e.g., *"Name an Italian dish"*).
2. A 45-second timer begins ticking down.
3. **Player Strategy for Avoiding Collisions**:
   - Avoid Tier 1 obvious crowd favorites (*Pizza*, *Pasta*), which almost always collide.
   - Beware of Tier 2 "clever middle ground" traps: if you think of *Risotto* because it feels less obvious than *Pizza*, three other players are likely thinking the exact same thing!
   - Aim for Tier 3 valid but distinct answers (*Ossobuco*, *Polenta*, *Arancini*) to claim both the unique +100 score and the +50 obscurity bonus.
4. As players submit, green checkmarks appear on the host roster (`has_submitted: true`), while the actual words remain strictly hidden by zero-spoiler projection.
5. In **The ME** mode:
   - "The ME" must submit first. Once their trap is locked, the submission form opens for the rest of the players.
6. When all players have submitted (or time runs out), click **✨ Reveal Round**.

---

### Step 3: Host Oral Table Mode (Living Room Pass & Play)

1. When `oral_table` mode is active, the game transitions to the `oral_speaking` phase.
2. Read the prompt displayed on your host screen aloud to the room: *"Name a green fruit!"*
3. Click the **📢 3-2-1 Verbal Countdown** button.
   - An audio chime and visual 3-2-1 sequence flashes on all screens.
4. On "GO!", players shout their answers aloud simultaneously (or in speed order around the couch).
5. Open the **Oral Adjudication Modal** on the host screen:
   - For each player who shouted a unique valid answer, toggle **Unique (+100)**.
   - For players who shouted identical or equivalent items, toggle **Clash (0 pts)**.
   - For players who submitted rare answers, check **Obscurity Bonus (+50)**.
6. Click **Confirm Oral Verdicts**. Scores and rankings update immediately.

---

### Step 4: Arbitrate Disputed Answers and Clashes (Typed Mode)

During the reveal phase, the engine automatically clusters matching answers using phonetic and Levenshtein similarity algorithms (e.g., grouping *"apple"* and *"apples"*, or ignoring case/accents):

1. Inspect the revealed cards on the host dashboard:
   - **Green Cards**: Unique valid answers (**+100 pts**, plus **+50 pts** if an obscurity star appears).
   - **Grey/Strikethrough Cards**: Clashing hivemind collisions (**0 pts** in Classic, **-50 pts** in Harsh).
   - **Red Cards**: Invalid answers (**0 pts**).
2. **Host Manual Overrides**:
   - If the engine failed to cluster two synonyms (e.g., *"Couch"* and *"Sofa"*):
     - Click **Toggle Clash** on both cards. The engine re-clusters them as a collision.
   - If the engine mistakenly flagged a valid slang term or regional name as invalid:
     - Click **Toggle Validity** to restore the card to valid standing.
3. Once all disputes are settled, click **Next Round** to advance to the next prompt.

---

## Verification

To verify that scoring executed accurately:
1. Check the post-round score summary:
   - Unique winners receive **+100** (or **+150** with obscurity).
   - Clashing players receive **0** (or **-50** in Harsh mode).
   - In "The ME" mode, eliminated players display an `💀 Eliminated` tag and cannot submit in subsequent rounds until a new match starts.
2. Verify that the cumulative leaderboard updates deterministically across all connected player devices.

---

## Troubleshooting & Edge Cases

### Fuzzy Matcher Clustered Two Different Concepts

- **Cause**: Two distinct words had a low edit distance (e.g., *"Peach"* and *"Poach"*).
- **Resolution**:
  1. In the reveal cards view, find the falsely clustered player card.
  2. Click **Unlink / Split Clash**.
  3. The card immediately separates into its own standalone unique card and receives +100 points.

### "The ME" Submits an Invalid Answer

- **Cause**: "The ME" player submitted a word that does not match the prompt category.
- **Resolution**:
  1. On the reveal screen, the host taps **Invalidate The ME**.
  2. The round is declared void, and "The ME" role passes to the next player in the rotation without penalizing other participants.

### Offline Player Unable to Type in Time

- **Cause**: Mobile network latency or slow typing during the 45-second timer.
- **Resolution**:
  1. In room settings before the round, increase **Round Timer** to `60s` or `90s`.
  2. Alternatively, switch the room to **Living Room Oral Mode (`oral_table`)** so participants can participate verbally without relying on mobile typing.

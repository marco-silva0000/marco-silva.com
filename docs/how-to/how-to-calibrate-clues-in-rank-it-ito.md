---
title: How to Calibrate Clues in Rank It! (ito)
description: Step-by-step instructions for giving subjective spectrum clues without numbers, debating relative card orders, and placing 1–100 cards on the timeline.
tags: [howto, rankit, ito, cooperative, party-games]
---

# How to Calibrate Clues in Rank It! (ito)

This guide explains how to formulate subjective scale clues without naming numbers, debate relative placements with teammates, and arrange cards from 1 to 100 in ascending order on the shared timeline in Rank It! (*ito*).

---

## Prerequisites

Before starting the round:
1. Join or host a Rank It! room at `/games/rankit/<CODE>/play/`.
2. Ensure at least **2 players** (up to 10) are connected via `/games/<CODE>/`.
3. The host has dealt Level 1 cards and the spectrum prompt is displayed at the top of the screen.

---

## The Golden Rule of ito

> [!CAUTION]
> **Zero Number Communication**: You may NEVER state your number, reference the 1–100 scale, state percentages, use mathematical operators, or use coded numeric slang (such as *"I'm in the low twenties"*, *"halfway point"*, or *"three out of ten"*). All communication must be expressed through subjective, qualitative clues fitting the prompt.

---

## Procedure

### Step 1: Analyze Your Secret Card and the Spectrum

1. Inspect your hand at the bottom of your screen. Look at your secret numeric card value ($1 \dots 100$).
2. Read the central **Spectrum Prompt** banner:
   - Left end ($1$): Absolute minimum, mildest, least significant extreme.
   - Right end ($100$): Absolute maximum, most extreme, supreme version.
3. Establish your mental anchors:
   - $1$: Theoretical zero of that category (e.g., *Prompt: "Scariest Animals"*; $1 \approx$ a sleepy newborn kitten).
   - $50$: Average, everyday, neutral baseline (e.g., a stray dog or honeybee).
   - $100$: Unstoppable, mythic dread (e.g., a colossal venomous prehistoric sea serpent).

---

### Step 2: Formulate and Input Your Clue

1. Formulate a concise clue that reflects where your number falls between the extremes.
   - **For Low Cards (1–25)**: Think of trivial, harmless, or microscopic examples.
   - **For Mid-Low Cards (26–49)**: Think of modest, mildly noticeable things.
   - **For Mid-High Cards (51–75)**: Think of significant, undeniably impactful things.
   - **For High Cards (76–100)**: Think of legendary, earth-shattering, or apex examples.
2. In the **My Clue** text field below your card, type your chosen description (e.g., *"A warm cup of black tea"* for a spice prompt).
3. Tap **💾 Save Clue** (or press Enter).
4. Your clue appears as a public text badge below your player avatar on the group screen, while your number remains secret.

---

### Step 3: Calibrate Relative Spectrum Placements Verbally

1. Once all players have published their clues, open group conversation.
2. Compare clues by establishing direct relative comparisons:
   - Ask clarifying comparative questions: *"Is your 'Wasabi peas' hotter or milder than my 'Jalapeño salsa'?"*
   - Probe intensity: *"On a scale of daily annoyance, is 'Stepping on a wet sock' worse than 'Running out of coffee'?"*
   - Test micro-distinctions: *"How hot is your tea? Freshly boiled or sitting on the desk for 10 minutes?"*
3. Through conversation, establish a tentative left-to-right order of clues from lowest to highest.

---

### Step 4: Place Cards on the Central Timeline

1. When the group agrees who holds the lowest clue, that player taps their card in hand and clicks **▶️ Play on Timeline** at the leftmost position (Slot 0).
2. The card lands face-down on the shared timeline, showing only the player's avatar and clue label.
3. Subsequent players place their cards one by one into the remaining open slots from left to right.
4. **Inserting Into the Middle**:
   - If a player realizes their clue belongs between two already placed cards, they can select the insertion slot between those two cards. The timeline automatically shifts existing cards to the right.

---

### Step 5: Adjust Order Using Swaps and Retractions

1. If discussion reveals two cards were placed in the wrong order:
   - Any player can tap Card A and Card B on the timeline, then click **🔄 Propose Swap**.
   - A yellow highlight banner appears indicating the proposed exchange to all players.
   - The room host clicks **✅ Approve Swap** to exchange their positions. (Any player can click **❌ Reject** to cancel).
2. **Retracting a Card**:
   - If you placed a card prematurely and wish to reconsider, tap your card on the timeline and click **↩️ Retract Card** to pull it back into your hand.

---

### Step 6: Trigger the Timeline Reveal

1. Verify that all dealt cards for the round have been placed on the timeline.
2. The host clicks **✨ Reveal Timeline**.
3. Cards flip sequentially from left to right with audio-visual cues:
   - Each card displays its revealed secret number.
   - If Card $(k) \ge$ Card $(k-1)$, the card glows green (**Success**).
   - If Card $(k) <$ Card $(k-1)$, the card flashes red (**Inversion Clash**), and the team loses **1 Life Heart** (❤️).

---

## Verification

To verify that the round succeeded:
1. Observe the timeline summary at the conclusion of the reveal sequence:
   - If all cards are in non-descending order ($C_1 \le C_2 \le \dots \le C_N$), the screen displays **🎉 Level Cleared!**.
   - The team's remaining life hearts (❤️) remain intact.
2. The host clicks **Next Level** to deal $N+1$ cards per player for the next round.

---

## Troubleshooting & Edge Cases

### Clue Inversion / Card Clash Occurred During Reveal

- **Cause**: Subjective disagreement or miscalibration (e.g., one person considered "Scorpions" scarier than "Grizzly Bears", but held a lower number).
- **Resolution**:
  1. Inspect the revealed numbers on the clash modal to see where the perception gap occurred.
  2. If the team still has life hearts remaining (❤️ $\ge 1$), the team remains in the game.
  3. Click **Continue to Next Level**.
  4. Spend an extra 30 seconds calibrating adjacent clues before committing placements in subsequent rounds.

### A Player Accurately Guessed Their Card Value by Accident

- **Cause**: A player said something too mathematically specific (e.g., *"I am literally at 85%"*).
- **Penalty / Recovery**:
  1. The group should mutually discard that card and redraw, or agree to incur a voluntary penalty.
  2. In the host settings, the host can reset the level by clicking **🔄 Redeal Level** to generate fresh random numbers and a new spectrum topic.

### Disconnected Player with Unplayed Card on Timeline

- **Cause**: A participant lost Wi-Fi connection with a card still in their hand.
- **Resolution**:
  1. In the host menu, click **Skip Disconnected Hand**.
  2. The server discards the offline player's remaining unplayed card from the round calculation so the remaining team can trigger the timeline reveal.

---
title: How to Run a High-Speed Stop! Race
description: Step-by-step instructions for customizing category decks, setting countdown pressure, tuning duplicate clash penalties, and arbitrating disputed words in Stop! (Tutti Frutti).
tags: [howto, stop, word-games, speed-race, categories]
---

# How to Run a High-Speed Stop! Race

This guide explains how to host a rapid-fire word race in Stop! (*Tutti Frutti* / *Basta*) on `marco-silva.com`. It covers customizing category packs, setting timer pressure and letter filters, configuring clash penalties, and arbitrating disputed submissions using the post-round validation grid.

---

## Prerequisites

Before starting the match:
1. Create a Stop! room at `/games/create/?game=stop`.
2. Connect as the host at `/games/stop/<CODE>/play/`.
3. Ensure at least **2 players** (up to 16+) have joined via `/games/<CODE>/` or the room QR code.

---

## Procedure

### Step 1: Configure Category Packs and Round Count

1. In the room lobby, locate the **⚙️ Game Settings** panel.
2. Select your preferred **Category Pack**:
   - `classic`: Standard categories (*Country, Animal, Fruit/Plant, Name, Object, City*).
   - `pop_culture`: Entertainment topics (*Celebrity, Movie, Song/Band, Brand, TV Show, Fictional Character*).
   - `geek`: Gaming and tech (*Video Game, Superhero/Villain, Sci-Fi/Fantasy Term, Tech Brand, Board Game*).
   - `geography`: Travel and world topics (*Country, Capital, River/Ocean, Mountain/Island, Language*).
   - `kids`: Simplified, accessible categories for younger players.
   - `mix`: Randomized selection drawing from all available packs.
3. Set the **Categories Per Round** to `5` or `6` depending on screen size and target round speed.
4. Set the **Target Rounds** (default: `5` rounds).

---

### Step 2: Configure Clash Penalties and Letter Pool

1. Locate the **Duplicate Clash Rule** selector:
   - `shared` (Standard): Duplicate valid answers receive half points (**+5 points** each).
   - `zero_clash` (Cutthroat): Any collision yields **0 points**, rewarding obscure vocabulary.
   - `first_steals` (Speed Demon): The player who called STOP gets full points (**+10 points**); identical answers by opponents yield **0 points**.
   - `none` (Casual): No penalty for duplicates; all valid answers receive **+10 points**.
2. Set the **Alphabet Letter Filter**:
   - **Standard Alphabet** (Recommended): Excludes difficult letters (`K`, `W`, `X`, `Y`, `Z`) to maintain rapid round tempo.
   - **Full Alphabet**: Includes all 26 letters for hardcore word masters.

---

### Step 3: Run the Live Word Race and the STOP! Call

1. In the lobby, click **🚀 Start Round 1**.
2. The server spins the letter wheel and reveals the active letter (e.g., **"Letter: M"**).
3. Players quickly type answers into the category input boxes on their phones.
4. **The STOP! Call**:
   - As soon as any player completes their sheet, they smash the giant red **🛑 STOP!** button at the bottom of their screen.
   - Calling STOP immediately triggers a synchronized **10-second countdown rush timer** on all other players' devices.
   - Opponents must type frantically or submit whatever answers they have completed before the 10 seconds expire.
   - When the timer hits 0, inputs lock automatically, and the round transitions to the **Validation Phase**.

---

### Step 4: Arbitrate Disputed Words in the Validation Grid

Once the round ends, the screen displays the **2D Validation Grid** (`Categories` $\times$ `Players`). The engine automatically runs word normalization (handling accents and case) and dictionary checks.

1. Review the rows in the validation matrix with the players:
   - Green items: Validated unique words (**+10 pts**).
   - Orange/Yellow items: Duplicate clash words (**+5 pts** or **0 pts** based on your clash rule).
   - Red items: Invalid, blank, or wrong-letter entries (**0 pts**).
2. **Override Disputed Words**:
   - If a player submitted a valid regional dialect word, clever slang, or minor typo that the automated dictionary flagged red:
     - Tap directly on the word cell in the grid.
     - The cell toggles from **Red (Invalid)** to **Green (Valid)**.
     - The player's score recalculates immediately across all connected scoreboards.
3. **Resolve Duplicate Collisions**:
   - If two players wrote synonymous terms that were not detected as collisions (e.g., *"Automobile"* vs *"Auto"*), tap the **Clash** toggle on the cell to enforce the clash penalty.
4. Verify the **All-Complete Bonus**:
   - If the player who called STOP had all categories validated as correct, verify that the **+5 All-Complete Bonus** is awarded.
5. Click **Next Round** to spin a new letter and continue the match.

---

## Verification

To verify that the round scoring processed accurately:
1. Inspect the **Live Scoreboard** at the bottom of the validation screen:
   - Unique valid words score **+10**.
   - Clashing words reflect the chosen clash penalty (**+5** or **0**).
   - Overridden words update total scores without page refresh.
2. Verify that the **Leaderboard Ranking** sorts descending by cumulative match points.

---

## Troubleshooting & Edge Cases

### Player Hits STOP by Mistake with Blank Fields

- **Cause**: A player accidentally tapped the STOP button before filling in answers.
- **Resolution**:
  1. The 10-second rush timer cannot be paused once initiated. Let the 10-second countdown conclude.
  2. In the validation grid, the premature player will have empty red cells for unfilled categories and will not receive the +5 all-complete bonus.
  3. If all players agree to void the round due to an obvious misclick, the host can click **Redo Round** to spin a new letter with identical settings.

### Accented Letters or Foreign Characters Disputed

- **Cause**: Words like *"Éléphant"* or *"São Paulo"* matching letter *E* or *S*.
- **System Behavior**:
  - The engine's `starts_with_letter()` normalizes Unicode diacritics automatically (`É` $\to$ `E`, `Ç` $\to$ `C`).
  - If a player claims a word matches phonetically but uses a different letter (e.g., *"Photo"* for *F*), the host should enforce standard spelling rules and tap the cell to mark it **Invalid (Red)**.

### Client-Side Double Tap on the STOP Button

- **Cause**: An eager player rapidly double-tapped the STOP button during the rush.
- **System Protection**:
  - The client UI implements click locking (`isCallingStop = true`), and the backend WebSocket consumer (`StopConsumer`) handles idempotent calls. The 10-second countdown runs cleanly without restarting or crashing.

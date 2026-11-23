# Stop!: Categories & Letter Speed Race

Stop! (also known internationally as *Basta*, *Tutti Frutti*, or *Guggenheim*) is a classic pencil-and-paper speed word game modernized into an energetic, responsive multiplayer web app.

---

## 1. Reference

### Game Specifications
- **Player Count**: 2 to 16+ players.
- **Round Duration**: 30–90 seconds.
- **Letter Selection**: Automatically spins a random letter from the alphabet (excluding difficult letters like Q, X, Z unless enabled).
- **Category Packs**: Classic, Geography, Pop Culture, Kids, Geek & Gaming, Mixed.

### Scoring System
- **Unique Valid Word**: `+10 points`
- **Shared / Clashing Valid Word**: `+5 points` (or 0 in Zero Clash mode)
- **Invalid / Empty / Wrong Letter**: `0 points`
- **All Categories Completed Bonus**: `+5 bonus points` to the player who called STOP if all their entries were valid!

### Clash Rules
- `shared`: Standard rules. Duplicate answers receive half points (5 pts).
- `first_steals`: The fastest player receives full points, subsequent matches receive 0.
- `zero_clash`: Collisions are penalized with 0 points.
- `none`: No collision penalty; all valid words receive full 10 points.

---

## 2. Explanation

### Speed vs. Obscurity Dilemma
The defining mechanic of Stop! is the tactile urgency of the STOP button:
- Do you write common words quickly (e.g. *Cat, Carrot, Canada*) and smash STOP to catch your friends empty-handed?
- If you do, you risk getting half points (5 pts) due to shared collisions!
- Or do you take an extra 5 seconds to think of obscure words (*Chinchilla, Clementine, Cambodia*) for full 10-point payouts?

---

## 3. How-To Guides

### How to Arbitrate Words in the Validation Grid
1. After the round ends, the **Validation Grid** opens, showing every player's words per category.
2. The engine automatically checks if words match the letter and common dictionaries.
3. If a player submits a valid local word or clever slang that the dictionary missed:
   - The Host can tap the word directly to toggle between **Valid (Green)** and **Invalid (Red)**.
   - Point totals update in real-time across all connected devices!

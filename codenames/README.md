# Codenames: Secret Agent Word Deduction

Codenames is a world-renowned cooperative and competitive word deduction game adapted for real-time online play. Two rival Spymasters know the secret identities of 25 agents. Their teammates must decipher one-word clues to contact their secret operatives before the enemy team does.

---

## 1. Reference

### Grid Composition (5x5 Board = 25 Cards)
- **Starting Team (Red or Blue)**: 9 Agent Cards
- **Second Team**: 8 Agent Cards
- **Bystanders (Civilian)**: 7 Neutral Cards
- **The Assassin**: 1 Fatal Card (💀)

### Clue Giving Rules
- A clue consists of **exactly ONE word** and **ONE number** (e.g. *"Galaxy: 3"*).
- The number tells your operatives how many cards on the board relate to that clue.
- **Illegal Clues**: You may not say any form or derivative of a visible card on the board (e.g., cannot say *"Play"* if *"Player"* is on the board).

### Turn Resolution
- Operatives tap cards one at a time.
- If they tap their team's color: They may guess again (up to `number + 1` guesses).
- If they tap a neutral Civilian: Their turn immediately ends.
- If they tap an opponent's card: Their turn ends, and they accidentally give the other team a point!
- If they tap the **Assassin (💀)**: Their team **instantly loses the game**!

---

## 2. Explanation

### The Semantic Challenge
Codenames is a battle of cognitive association:
- Finding a clue that connects *Apple* and *Tree* is easy (Score: 2).
- Finding a clue that connects *Apple*, *Gravity*, and *Knight* requires creative lateral thinking (*"Newton"* or *"Camelot"*) while carefully avoiding words that might tempt your team toward the fatal Assassin!

---

## 3. How-To Guides

### How to Play as Spymaster
1. When joining the lobby, click **Join as Spymaster** under your chosen team (Red or Blue).
2. During your turn, you will see the full colored grid displaying all agent identities.
3. Enter your clue word and count into the clue bar and click **Submit Clue**.
4. Watch live as your operatives discuss and select cards on the board!

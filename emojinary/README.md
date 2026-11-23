# Emojinary: Real-Time Emoji Pictionary Party Game

Emojinary is a creative party game of visual communication and rapid deduction. Like classic Pictionary, one player attempts to communicate a secret word or phrase—but instead of a pen and paper, their only tools are emojis!

---

## 1. Reference

### Game Specifications
- **Player Count**: 2 to 16+ players.
- **Round Duration**: 60–120 seconds per drawing turn.
- **Game Modes**:
  - `round_robin`: Players take turns being the Drawer. Guessers compete for fastest correct guess.
  - `best_guess`: Every player receives the same secret prompt simultaneously and creates their best emoji sequence; the room votes on their favorites.
- **Categories**: Movies, Objects, Actions & Verbs, Famous People, Places & Monuments, Animals & Nature.

### Scoring Breakdown
- **Fastest Correct Guess**: `+100 points`
- **Second Correct Guess**: `+75 points`
- **Subsequent Correct Guesses**: `+50 points`
- **Drawer Bonus**: `+25 points` per player who successfully guesses their clue!

---

## 2. Explanation

### The Joy of Constrained Expression
Emojis are a universal language, but they lack precise syntax. A drawer communicating *"Jurassic Park"* might place:
`🦖 🌴 🚙 😱`
Guessers must rapidly synthesize the narrative: Dinosaur + Jungle + Car + Screaming person = *Jurassic Park*! The engine uses fuzzy semantic matching so slight variations ("jurassic park" vs "jurassic") register smoothly.

---

## 3. How-To Guides

### How to Play as Drawer
1. When your turn starts, your secret word and category appear at the top of your screen.
2. Use the built-in emoji keyboard or search bar to find expressive emojis.
3. Click or tap an emoji to place it onto your canvas.
4. Watch the live chat feed on the side as your friends shout out guesses!

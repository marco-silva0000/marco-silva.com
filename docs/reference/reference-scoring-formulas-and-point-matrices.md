---
title: Reference - Scoring Formulas and Point Matrices
tags: [reference, scoring, formulas, algorithms, party-games, matrices]
created: 2026-11-24
updated: 2026-11-24
---

# Reference: Scoring Formulas and Point Matrices

This document specifies the exact mathematical models, point allocation matrices, time decay curves, and penalty schedules across all games in the platform.

---

## 1. Stop! (Categories & Letter Speed Race)

Points are calculated on round termination based on two orthogonal dimensions: **Answer Uniqueness** and **Submission Speed**.

### 1.1 Uniqueness and Speed Bonus Schedule

For all valid answers evaluated as unique (group size $= 1$ in the cluster matrix):

$$\text{Points}_{\text{unique}}(r) = \begin{cases} 
15 & \text{if } r = 1 \text{ (10 base + 5 speed bonus)} \\
13 & \text{if } r = 2 \text{ (10 base + 3 speed bonus)} \\
11 & \text{if } r = 3 \text{ (10 base + 1 speed bonus)} \\
10 & \text{if } r \ge 4 \text{ (10 base + 0 bonus)}
\end{cases}$$

Where $r \in \mathbb{N}^+$ represents the ordinal rank of the player among all unique valid submissions, ordered ascending by elapsed submission time ($\text{elapsed\_ms}$).

### 1.2 Collision & Duplicate Clash Matrix

When two or more players submit words belonging to the same semantic/spelling cluster ($\text{cluster\_size} \ge 2$), points are governed by `clash_rule`:

| `clash_rule` Setting | Submitter Condition | Points Awarded | Status String | UI Badge |
| :--- | :--- | :--- | :--- | :--- |
| **`shared`** (Default) | All players in duplicate cluster | `+5` | `clash_shared` | `💥 Duplicate Clash (+5 pts)` |
| **`first_steals`** | Fastest submitter in duplicate cluster | `+10` | `clash_stolen` | `⚡ First on Duplicate! (+10 pts)` |
| **`first_steals`** | Subsequent (slower) duplicates | `0` | `clash_beaten` | `💥 Duplicate — Too Slow (0 pts)` |
| **`zero_clash`** | All players in duplicate cluster | `0` | `clash_zero` | `💥 Duplicate Clash (0 pts)` |
| **`none`** | All players in duplicate cluster | `+10` | `clash_none` | `✨ Valid Answer (+10 pts)` |

### 1.3 Invalidation & Penalties

| Submission State | Points | Status String | UI Badge |
| :--- | :--- | :--- | :--- |
| **Wrong Initial Letter** | `0` | `wrong_letter` | `❌ Doesn't start with “{letter}” (0 pts)` |
| **Community Vetoed** | `0` | `vetoed` | `👎 Vetoed (0 pts)` |
| **Host Overridden (Invalid)** | `0` | `vetoed` | `👎 Vetoed (0 pts)` |
| **Unanswered / Timeout** | `0` | `missing` | `⌛ No Answer (0 pts)` |

---

## 2. Don't Say the Same Thing as Me

Scoring in `dontsay` depends on whether the match is running in **Classic (Anti-Hivemind)** or **The ME (Elimination)** mode.

### 2.1 Classic Mode Point Schedule

$$\text{Score}_{\text{round}}(p) = \begin{cases}
150 & \text{if valid, unique, and } \text{is\_obscure} \land \text{allow\_obscurity\_bonus} \\
100 & \text{if valid, unique, and not obscure} \\
0 & \text{if valid, clashing, and } \text{collision\_mode} = \text{"classic"} \\
-50 & \text{if valid, clashing, and } \text{collision\_mode} = \text{"harsh"} \\
0 & \text{if invalid or unsubmitted}
\end{cases}$$

Cumulative match scores are floored at zero:

$$\text{Score}_{\text{total}}(p) = \max\left(0, \sum_{i=1}^{R} \text{Score}_{\text{round}, i}(p)\right)$$

### 2.2 "The ME" Mode Elimination and Mastermind Formulas

In `the_me` mode, a designated player $M$ submits a forbidden anchor word $W_M$.

#### Regular Participants ($p \neq M$):

$$\text{Outcome}(p) = \begin{cases}
\text{Eliminated } (\text{Score} \mathrel{-}= 50 \text{ if harsh, else } 0) & \text{if } W_p \approx W_M \\
\text{Safe } (\text{Score} \mathrel{+}= 100 \text{ or } 150 \text{ obscure}) & \text{if } W_p \not\approx W_M \land \text{Valid}(W_p) \\
\text{Invalid } (\text{Score} \mathrel{+}= 0) & \text{if } \neg\text{Valid}(W_p)
\end{cases}$$

#### The ME Player ($M$):

$$\text{Points}_{\text{round}}(M) = \begin{cases}
100 \times |V| & \text{if } |V| \ge 1 \quad (\text{where } V \text{ is the set of eliminated victims}) \\
50 & \text{if } |V| = 0 \quad (\text{consolation bonus for avoiding all collisions})
\end{cases}$$

---

## 3. SmartN (Push-Your-Luck Trivia)

SmartN tracks two point registries per player: **Round Basket** ($B_p \in \mathbb{N}$) and **Banked Score** ($S_p \in \mathbb{N}$).

### 3.1 State Transitions and Basket Mechanics

| Player Action | Capsule Outcome | Basket Delta | Banked Score Delta | Player Status Transition |
| :--- | :--- | :--- | :--- | :--- |
| **Pick Capsule** | **Correct** | $B_p \leftarrow B_p + 1$ | $S_p \leftarrow S_p$ | Remains `active` |
| **Pick Capsule** | **Wrong (Bust)** | $B_p \leftarrow 0$ | $S_p \leftarrow S_p$ | `active` $\to$ `busted` (Out for round) |
| **Pass Turn** | N/A | $B_p \leftarrow 0$ | $S_p \leftarrow S_p + B_p$ | `active` $\to$ `passed` (Safe for round) |

### 3.2 Automated Round-End Banking

When all $N$ capsules on the active card are revealed, any player remaining in the `active` status automatically banks their unbanked points:

$$\forall p \in P, \quad \text{if } \text{Status}(p) = \text{"active"} \implies S_p \leftarrow S_p + B_p, \quad B_p \leftarrow 0$$

### 3.3 Match Victory Condition

Match termination is evaluated immediately following any round conclusion:

$$\text{GameOver} \iff \max_{p \in P}(S_p) \ge T \quad (T = \text{target\_score}, \text{ default } 20)$$

---

## 4. Rank It! (*ito*)

Rank It! evaluates cooperative survival based on strictly ascending placement of cards on the central Timeline.

### 4.1 Inversion Clash Detection

Let the revealed timeline be an ordered sequence of cards:

$$T = \langle c_1, c_2, \dots, c_m \rangle, \quad \text{where } c_i = (\text{player}_i, \text{number}_i), \quad \text{number}_i \in [1, 100]$$

A clash occurs at index $i$ ($2 \le i \le m$) if and only if:

$$\text{number}_i < \text{number}_{i-1}$$

The total clash count $K$ for the reveal is:

$$K = \sum_{i=2}^{m} \mathbb{I}\left(\text{number}_i < \text{number}_{i-1}\right)$$

### 4.2 Team Life Heart Deduction

Starting lives $L_0 \in [1, 5]$ (default 3). Following a timeline reveal:

$$L_{\text{new}} = \max(0, L_{\text{current}} - K)$$

$$\text{State}_{\text{match}} = \begin{cases}
\text{gameover} & \text{if } L_{\text{new}} = 0 \\
\text{victory} & \text{if } L_{\text{new}} > 0 \land \text{Level} \ge \text{target\_levels} \\
\text{level\_success} & \text{if } L_{\text{new}} > 0 \land \text{Level} < \text{target\_levels}
\end{cases}$$

### 4.3 Level Progression & Card Dealing Schedule

| Level ($k$) | Cards Per Player (`level_based`) | Hand Size Example (5 Players) | Timeline Cards ($m$) |
| :--- | :--- | :--- | :--- |
| **Level 1** | 1 card | 5 total cards | 5 |
| **Level 2** | 2 cards | 10 total cards | 10 |
| **Level 3** | 3 cards | 15 total cards | 15 |
| **Level $k$** | $k$ cards | $k \times |P|$ total cards | $k \times |P|$ |

---

## 5. Emojinary (Emoji Pictionary)

### 5.1 Real-Time Guess Decay Formula

In `round_robin` mode, points awarded to a successful guesser decrease linearly over time:

$$\text{Points}_{\text{guesser}}(t) = \max\left(2, 10 - \left\lfloor \frac{t}{7} \right\rfloor\right) + \text{Bonus}_{\text{first}}$$

Where:
- $t \ge 0$ is the elapsed turn time in seconds ($\text{time.time}() - \text{turn\_start\_time}$).
- $\text{Bonus}_{\text{first}} = 2$ if the player is the first participant to guess correctly in the current round ($\text{len}(\text{guessed}) = 0$), and $0$ otherwise.

#### Decay Step Function:

| Elapsed Seconds ($t$) | Base Points ($10 - \lfloor t/7 \rfloor$) | First Guesser Score ($+2$) | Subsequent Guesser Score ($+0$) |
| :--- | :--- | :--- | :--- |
| **0.0s – 6.9s** | 10 | **12** | **10** |
| **7.0s – 13.9s** | 9 | **11** | **9** |
| **14.0s – 20.9s** | 8 | **10** | **8** |
| **21.0s – 27.9s** | 7 | **9** | **7** |
| **28.0s – 34.9s** | 6 | **8** | **6** |
| **35.0s – 41.9s** | 5 | **7** | **5** |
| **42.0s – 48.9s** | 4 | **6** | **4** |
| **49.0s – 55.9s** | 3 | **5** | **3** |
| **$\ge$ 56.0s** | 2 (Floor) | **4** | **2** |

### 5.2 Drawer Points

For every distinct player $p$ who submits a correct guess during the active turn:

$$\text{Score}_{\text{drawer}} \leftarrow \text{Score}_{\text{drawer}} + 3$$

### 5.3 Best Guess Mode

- Winning drawing selected by consensus vote: $\text{Creator Score} \leftarrow \text{Creator Score} + 10$.
- Drawer recognition bonus: $+3$ points.

---

## 6. Word Impostor

Points in `impostor` are awarded at the conclusion of the `voting` and `steal` phases during `_finalize_reveal`:

| Match Outcome String | Description | Loyal Citizen Points | Poisoned Citizen Points | Impostor Points |
| :--- | :--- | :--- | :--- | :--- |
| **`citizens_win`** | Impostor correctly identified and eliminated; lethal steal failed | `+2` | `+2` (or `+3` if unejected) | `0` |
| **`impostor_poisoned`** | Poisoned Citizen ejected by mistake; Citizens recover and deny Impostor | `+2` | `+2` | `0` |
| **`impostor_win`** | Loyal Citizen wrongfully ejected; Impostor survived | `0` | `0` | `+3` |
| **`impostor_survived`** | Impostor survived tied vote or vote timeout | `0` | `0` | `+3` |
| **`impostor_steal`** | Caught Impostor correctly guessed the Citizen word during the 30s steal window | `0` | `0` | `+3` |

---

## 7. Codenames

Codenames operates on a binary win/loss terminal model:

$$\text{Result}(\text{Team}) \in \{\text{Victory}, \text{Defeat}\}$$

### Card Allocation Model

$$\text{Total Grid Cards} = 25 = N_{\text{start}} + N_{\text{second}} + N_{\text{neutral}} + N_{\text{assassin}}$$

$$\begin{cases}
N_{\text{start}} = 9 & (\text{Red or Blue, chosen randomly}) \\
N_{\text{second}} = 8 & (\text{Remaining opposing team}) \\
N_{\text{neutral}} = 7 & (\text{Innocent Civilians}) \\
N_{\text{assassin}} = 1 & (\text{Lethal Assassin Card 💀})
\end{cases}$$

### Terminal Conditions

1. **Agent Clearance**: $\text{Remaining}(\text{Team}_i) = 0 \implies \text{Team}_i \text{ Wins}$.
2. **Assassin Contact**: $\text{Operatives}(\text{Team}_i) \text{ tap Assassin} \implies \text{Team}_i \text{ Loses Instantly } (\text{Team}_j \text{ Wins})$.

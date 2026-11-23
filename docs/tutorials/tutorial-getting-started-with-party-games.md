---
title: Getting Started with Party Games on marco-silva.com
tags: [tutorial, party-games, gamerooms, beginner, onboarding]
category: tutorials
created: 2026-11-24
updated: 2026-11-24
---

# Tutorial: Getting Started with Party Games on marco-silva.com

Welcome! In this tutorial, we will take our very first steps with the party games platform on `marco-silva.com`. Together, we will create a game room, invite friends using a dynamic QR code, explore the lobby, and play through a quick first round on our phones and laptops.

By the end of this lesson, you will know how to launch any party game on the platform and get a room full of players connected in under two minutes—with zero apps to download and zero accounts to register.

---

## What We Will Achieve

We will:
1. Open the game hub and create a new **Emojinary** game room.
2. Join the room lobby as the host on our laptop.
3. Connect a second player using a smartphone camera and QR code.
4. Start the game and play through our first drawing and guessing round.

---

## Step 1: Open the Party Games Hub

Let's begin by opening our web browser on our computer or tablet.

1. Navigate to:
   ```
   https://marco-silva.com/games/
   ```
   *(If you are developing locally, navigate to `http://localhost:8000/games/`)*

2. Notice the party games dashboard. It displays the active game catalog, including Emojinary, Lupus in Tabula, SmartN, Secret Santa, Stop!, and Word Impostor.

---

## Step 2: Create Our First Game Room

Now let's create a room for our session.

1. Click the **Create Room** button (or navigate directly to `/games/create/`).
2. Fill in the room creation form with the following details:
   - **Room Title**: Type `Friday Game Night`.
   - **Game**: Select **Emojinary (Emoji Pictionary)** from the dropdown.
   - **Language**: Select **English (en)**.
   - **Password**: Leave this empty for now (no password needed).
   - **Anti-Bot Question**: Answer the quick math question displayed on the screen (for example, if it asks `5 + 3`, enter `8`).
3. Click **Create Room**.

Notice that the browser immediately redirects us to the join page for our new room.

---

## Step 3: Join the Lobby as Host

Now that our room exists, let's step inside as the game host.

1. In the **Player Name** field, type your name: `Marco`.
2. Click **Join Room**.

Notice the screen transforms into our live room lobby:
- At the top of the screen, we see an **8-character Room Code** (such as `2A073334`).
- In the center, we see a crisp, high-contrast **QR Code**.
- In the player roster, our name appears with a colored circle badge displaying our initials (`M`) and an assigned palette color.
- A crown icon next to our name confirms that we are the room host.

---

## Step 4: Connect a Friend via Smartphone

Now let's bring a friend into the room using their mobile phone.

1. Pick up a smartphone and open its built-in camera app.
2. Point the camera at the QR code displayed on the laptop screen.
3. Tap the link notification that appears on the phone. The phone opens the join page at:
   ```
   https://marco-silva.com/games/2A073334/
   ```
4. On the phone screen, enter the player name `Sarah` and tap **Join Room**.

Look at both screens:
- On Sarah's phone, the lobby displays the connected player roster.
- On our laptop screen, Sarah's avatar and initials (`S`) instantly appear in the player list without needing to refresh the page.

---

## Step 5: Start the Game

With both players ready in the lobby, let's start the match.

1. On the laptop (the host screen), locate the primary action button: **Start Game**.
2. Click **Start Game**.

Notice what happens immediately on both screens:
- The lobby smoothly transitions into the active **Round 1** game arena.
- One player is designated as the active **Drawer**, while the other is designated as the **Guesser**.
- A synchronized countdown timer appears at the top of both screens.

---

## Step 6: Play Our First Round

Let's experience how real-time play works between the two devices.

1. **The Drawer's Turn**:
   - Look at the phone of the player designated as the Drawer. A secret prompt card appears (for example: `Pizza Party 🍕`).
   - Below the canvas, tap emoji buttons (such as 🍕, 🎉, 🥳) to place them onto the drawing canvas.
   - Look at the laptop screen: Notice the emojis appear on the laptop canvas in real time as Sarah taps them on her phone.

2. **The Guesser's Turn**:
   - On the laptop screen, look at the guess input box below the canvas.
   - Type `Pizza party` and press **Enter** (or click **Guess**).

3. **Watch the Result**:
   - Notice that the system instantly validates the guess!
   - A celebratory banner announces: *"Marco guessed correctly!"*.
   - Points are awarded on the scoreboard, and winning confetti animates across both screens.

---

## Milestone Checkpoint

Congratulations! We have completed our first party games session:
- We created a room on `marco-silva.com/games/`.
- We used the dynamic QR code to connect a phone in seconds.
- We observed real-time WebSocket synchronization across devices.
- We completed a full round of Emojinary.

---

## Next Steps

Now that you understand the basic room and lobby workflow, explore our specialized guides:
- [Tutorial: Hosting Your First Lupus (Werewolf) Night](tutorial-hosting-your-first-lupus-werewolf-night.md) — Moderate a 7-player social deduction match using the Game Master Cockpit.
- [Tutorial: Playing SmartN in Couch Mode](tutorial-playing-smartn-couch-mode.md) — Pass a single phone around the couch for a push-your-luck trivia game.
- [Tutorial: Running a Secret Santa Exchange](tutorial-running-a-secret-santa-exchange.md) — Organize a holiday gift exchange with live wishlists and zero-spoiler envelopes.

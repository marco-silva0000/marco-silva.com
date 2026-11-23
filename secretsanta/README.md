# Secret Santa & Target Matcher: Multi-Theme Pairing Engine

A real-time multiplayer gift exchange and target pairing system built on Django Channels, Redis, and WebSockets. Featuring zero-spoiler target projection, Hamiltonian cycle matching with exclusions, live wishlists, and a tactile "Tap & Hold" privacy shield for shared screens.

---

## 1. Reference

### Specifications
- **Participants**: 2 to 50+ participants.
- **Protocols**: HTTP for entry/QR landing; WebSockets (`/ws/secretsanta/<CODE>/`) for real-time orchestration.
- **State Storage**: Redis with fallback to Django cache (`secretsanta:game:<CODE>`), 30-day room persistence.
- **Zero-Spoiler Projection**: Client views never contain the global assignment mapping or other players' target IDs.

### Supported Themes

| Theme ID | Display Name | Icon | Role Name | Action Prompt | Default Budget |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `secretsanta` | Secret Santa | 🎁 | Secret Santa | You are giving a gift to: | `20€ / $20` |
| `assassin` | Secret Assassin | 🎯 | Secret Agent | Your secret target is: | *(None)* |
| `buddy` | Secret Buddy / Angel | 🤝 | Secret Angel | You are looking after: | `Acts of kindness` |
| `custom` | Custom Match | 🎲 | Participant | Your assigned pair is: | *(None)* |

### Configuration Options (`settings`)

| Key | Default | Options | Description |
| :--- | :--- | :--- | :--- |
| `theme` | `secretsanta` | `secretsanta`, `assassin`, `buddy`, `custom` | Active theme preset. |
| `custom_title` | `Secret Santa` | String ($\le 150$ chars) | Room header title. |
| `budget` | `20€ / $20` | String ($\le 150$ chars) | Spending recommendation or guideline. |
| `event_date` | `""` | String ($\le 150$ chars) | Exchange date or submission deadline. |
| `notes_placeholder`| *(Theme-specific)*| String | Placeholder for participant notes/wishlists. |

---

## 2. Explanation

### Mathematical Pairing & Hamiltonian Cycles
Traditional Secret Santa draws frequently suffer from two flaws:
1. **Self-Draws**: Drawing one's own name requires redrawing the entire bowl.
2. **Disconnected Sub-Loops**: In a group of 10 people, Alice and Bob might draw each other ($A \leftrightarrow B$), while the remaining 8 exchange among themselves. While mathematically valid as a derangement, it diminishes group cohesion.

The Secret Santa engine addresses this by prioritizing **Hamiltonian Cycles**:
- A single directed cycle $p_{\pi(1)} \to p_{\pi(2)} \to \dots \to p_{\pi(N)} \to p_{\pi(1)}$ connects every participant in a single unbroken gift loop.
- When $N \ge 3$, mutual 2-cycles ($A \leftrightarrow B$) are mathematically impossible.
- When exclusion constraints (e.g., spouses who should not gift each other) prevent a single unified Hamiltonian cycle, the engine seamlessly falls back to randomized backtracking with the Minimum Remaining Values (MRV) heuristic to produce a valid derangement.

### Zero-Spoiler Projection Architecture
Privacy is critical during gift planning:
- Many groups share a living room TV or laptop, or have participants looking over each other's shoulders.
- Rather than transmitting the full matching dictionary to the browser and attempting to hide it with CSS, the server executes strict projection sanitization (`get_sanitized_player_view`).
- The payload sent over the WebSocket never contains `matches` or other participants' `target_id`. Even with DevTools open, no participant can inspect another person's assignment.
- The "Tap & Hold to Peek" shield ensures that even when someone looks at your screen, your target remains covered until you deliberately hold down the card.

---

## 3. How-To Guides

### How to Host a Holiday Secret Santa
1. Navigate to `/games/create/?game=secretsanta` and enter a room title (e.g., "Smith Family Christmas").
2. Complete the anti-bot question and click **Create Room**.
3. In the room lobby, share the room link or QR code with your friends and family.
4. Set the **Spending Budget** and **Exchange Date** in the organizer settings.
5. Once all participants have joined, click **🎲 Draw Secret Matches**.

### How to Set Pairing Exclusions (e.g. Couples)
1. In the room lobby, find the participant row in the **Connected Participants** roster.
2. Click the **🚫 Excl** button next to their name.
3. Check the box next to anyone they should NOT be paired with (e.g. their partner).
4. Click **Save Exclusions**. The matching algorithm will respect this restriction during the draw.

### How to Add Offline / Couch Participants
1. If a child, grandparent, or friend without a smartphone is participating in person, click **➕ Add Offline Player** in the lobby.
2. Enter their name (e.g., "Grandma") and click **Add Participant**.
3. After matches are drawn, use the **Couch / Shared Device Envelope Selector** to switch the view to "Grandma".
4. Pass the tablet to Grandma so she can press and hold to view her secret target privately.

---

## 4. Tutorials

### Tutorial: Setting Up Your First Room in 3 Minutes
This tutorial walks through creating and completing a 3-person gift exchange:

1. **Create the Room**:
   - Go to `/games/` on your browser and click **+ Host Room** on the Secret Santa card.
   - Enter your name as the host.
2. **Add Participants**:
   - Have two friends scan your room QR code on their phones, or add them as offline players.
3. **Fill Out Wishlists**:
   - In the **My Wishlist & Preferences** box, type 2 or 3 gift hints (e.g., "Dark chocolate, fantasy novels, wool socks") and click **Save My Wishlist**.
4. **Draw and Reveal**:
   - Click **Draw Secret Matches**.
   - Your screen updates to display a wax-sealed envelope.
   - Press and hold the envelope with your thumb or mouse: it reveals your secret recipient and their wishlist notes!
   - Release your finger: the envelope instantly snaps shut, protecting the surprise.

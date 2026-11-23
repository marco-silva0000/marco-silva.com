---
title: Reference - WebSocket Actions, Channels, and URL Routing
tags: [reference, api, websockets, urls, routing, channels, sessions]
created: 2026-11-24
updated: 2026-11-24
---

# Reference: WebSocket Actions, Channels, and URL Routing

This document provides the canonical API reference for URL routing, WebSocket transport endpoints, client session cookie architectures, client-to-server (C2S) action schemas, and server-to-client (S2C) broadcast events across all game engines.

---

## 1. HTTP URL Routing Architecture

All party games are routed under the `/games/` URL namespace configured in `gamerooms/urls.py` and `website/urls.py`.

### 1.1 Shared Room Platform Routes

| HTTP Route | View Function | Name Identifier | Description |
| :--- | :--- | :--- | :--- |
| `GET /games/` | `gamerooms.views.room_list` | `gamerooms:room-list` | Public lobby browser and room code search |
| `GET /games/create/` | `gamerooms.views.room_create` | `gamerooms:room-create` | Room creation portal (game selection, password, language) |
| `GET,POST /games/<CODE>/` | `gamerooms.views.room_join` | `gamerooms:room-join` | Direct code join landing page and redirector |
| `POST /games/prompts/suggest/` | `gamerooms.views.suggest_prompt` | `gamerooms:suggest-prompt` | Community prompt and question submission API |

### 1.2 Canonical Per-Game URL Patterns

Every party game module implements standard clean URL endpoints:

| URL Pattern | Purpose | Template / Response |
| :--- | :--- | :--- |
| `GET /games/<slug>/<CODE>/play/` | **Primary Gameplay Interface** | `templates/<slug>/game.html` |
| `GET /games/<slug>/<CODE>/reconnect/<TOKEN>/` | Reconnect endpoint; sets session cookie and redirects to `/play/` | HTTP 302 Redirect to `.../play/` |
| `GET /games/<slug>/<CODE>/qr/<TOKEN>/` | Dynamic QR code image generator for mobile device reconnect | `image/svg+xml` |
| `GET /games/<slug>/<CODE>/<NAME>/` | Legacy vanity redirect; seeds display name in session | HTTP 302 Redirect to `.../play/` |
| `GET /games/<slug>/<CODE>/` | Root room fallback | HTTP 302 Redirect to `.../play/` |

### 1.3 Specialized Game Routes

| Game Module | Specialized Route | Description |
| :--- | :--- | :--- |
| **`emojinary`** | `GET /games/emojinary/emoji-search/` | Debounced JSON search API for emoji keyword autocomplete |
| **`emojinary`** | `GET /games/emojinary/<CODE>/replay.json` | JSON match export containing full timeline of canvas submissions |
| **`codenames`** | `GET /games/codenames/<CODE>/replay.json` | JSON match export of grid generation, clues, and guesses |
| **`dontsay`** | `GET /games/dontsay/<CODE>/api/state/` | REST endpoint for diagnostic state inspection |
| **`lupus`** | `GET /games/lupus/<CODE>/gm/` | **GM Cockpit Dashboard**: Unsanitized operator control center |
| **`lupus`** | `GET /games/lupus/<CODE>/export-replay/` | Complete JSON export of match action history |

---

## 2. WebSocket Transport & ASGI Routing

WebSocket traffic is routed through Django Channels in `website/asgi.py`.

### 2.1 WebSocket Endpoint Matrix

| Game Engine | WebSocket Path Pattern | Consumer Class |
| :--- | :--- | :--- |
| **`emojinary`** | `ws://<host>/ws/emojinary/<CODE>/` | `emojinary.consumers.EmojinaryConsumer` |
| **`impostor`** | `ws://<host>/ws/impostor/<CODE>/` | `impostor.consumers.ImpostorConsumer` |
| **`codenames`** | `ws://<host>/ws/codenames/<CODE>/` | `codenames.consumers.CodenamesConsumer` |
| **`stop`** | `ws://<host>/ws/stop/<CODE>/` | `stop.consumers.StopConsumer` |
| **`dontsay`** | `ws://<host>/ws/dontsay/<CODE>/` | `dontsay.consumers.DontSayConsumer` |
| **`rankit`** | `ws://<host>/ws/rankit/<CODE>/`<br>`ws://<host>/ws/games/rankit/<CODE>/` | `rankit.consumers.RankitConsumer` |
| **`smartn`** | `ws://<host>/ws/smartn/<CODE>/`<br>`ws://<host>/ws/games/smartn/<CODE>/` | `smartn.consumers.SmartNConsumer` |
| **`secretsanta`**| `ws://<host>/ws/secretsanta/<CODE>/`<br>`ws://<host>/ws/games/secretsanta/<CODE>/` | `secretsanta.consumers.SecretSantaConsumer` |
| **`lupus`** | `ws://<host>/ws/lupus/<CODE>/` | `lupus.consumers.LupusConsumer` |

### 2.2 Security & Origin Validation

The ASGI pipeline enforces `WebSocketOriginValidator` against incoming connections:
- Inspects the `Origin` header.
- Compares hostname against `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Rejects unauthorized cross-site connections immediately with close code `4403`.

---

## 3. Session Cookie Architecture

Player identity, reconnection recovery, and host moderation rights are anchored in Django session cookies:

| Key Pattern | Value Type | Description |
| :--- | :--- | :--- |
| `f"{slug}_player_{CODE}"` | `str` (16-char hex token) | Secret player credential used to authenticate reconnects and associate with `player_id`. |
| `f"{slug}_admin_{CODE}"` | `bool` (`True`) | Host authorization flag granting access to administrative actions. |
| `f"admin_{CODE}"` | `bool` (`True`) | Legacy fallback admin flag across earlier modules. |

---

## 4. Universal Client-to-Server (C2S) Action Types

All consumers inherit and handle the following standard JSON action packets:

| Action Name | Parameters | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **`join`** | `{"token": str, "name": str, "is_admin": bool}` | Anyone | Initial handshake after WebSocket connection opens. |
| **`chat`** | `{"text": str}` | Participants | Broadcasts public chat message or in-game guess. |
| **`change_color`** | `{"color": str}` | Active Player | Updates avatar color from the 12-color accessible palette. |
| **`toggle_spectator`** | `{}` | Active Player | Toggles participant between player and spectator mode. |
| **`kick_player`** | `{"target_id": str}` | Host / Admin | Removes a disruptive player from the room and state. |
| **`transfer_host`** | `{"target_id": str}` | Host / Admin | Passes `is_admin` host privileges to another participant. |
| **`update_settings`** | `{"settings": dict}` | Host / Admin | Modifies room parameters (timers, packs, rule variants). |
| **`suggest_prompt`** | `{"text": str, "pack": str, ...}` | Anyone | Submits a custom prompt or question to the moderation queue. |

---

## 5. Game-Specific Client-to-Server Actions

### 5.1 Stop! (`stop`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `submit_answer` | `{"category_id": str, "text": str}` | Player | Submits live answer text for an active category. |
| `call_stop` | `{}` | Player | Triggers the 10-second final rush countdown for all players. |
| `round_timeout` | `{}` | Anyone | Signals authoritative timer expiration. |
| `toggle_validity`| `{"player_id": str, "valid": bool}` | Host | Overrides word validity in the validation grid. |
| `toggle_clash` | `{"player_id": str, "is_clash": bool}` | Host | Manually forces or clears duplicate clash status. |
| `redraw_round` | `{}` | Host | Rerolls active categories and letter before submission starts. |
| `next_round` | `{}` | Host | Advances match to the next round sheet. |

### 5.2 Don't Say (`dontsay`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `submit_the_me_answer` | `{"answer": str}` | The ME | Locks secret forbidden anchor word in The ME mode. |
| `submit_answer` | `{"answer": str}` | Player | Secretly submits round answer before timer expires. |
| `adjudicate_oral_round`| `{"results": dict}` | Host | Manually enters oral table eliminations or points. |
| `reveal_round` | `{}` | Host | Ends submission phase and triggers fuzzy clustering. |
| `ai_arbitrate` | `{"clean_key": str}` | Host | Dispatches semantic AI verification for unrecognized words. |

### 5.3 Rank It! (*ito*) (`rankit`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `set_clue` | `{"card_id": str, "clue": str}` | Player | Updates clue text attached to secret numbered card. |
| `play_card` | `{"card_id": str}` | Player | Places card face-down onto the shared Timeline. |
| `retract_card` | `{"card_id": str}` | Player / Host | Takes placed card back into player hand before reveal. |
| `propose_swap` | `{"idx_a": int, "idx_b": int}` | Player | Proposes exchanging two timeline positions during debate. |
| `approve_swap` | `{}` | Host | Approves pending timeline swap proposal. |
| `reject_swap` | `{}` | Player / Host | Dismisses pending timeline swap proposal. |
| `move_timeline_card` | `{"from_idx": int, "to_idx": int}`| Host | Directly shifts card position along the timeline. |
| `reveal_timeline` | `{}` | Host | Triggers left-to-right card reveal and clash verification. |
| `start_level` | `{"level": int}` | Host | Deals cards and starts new spectrum level. |

### 5.4 SmartN (`smartn`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `pick_capsule` | `{"slot": int, "prediction": str}` | Active Player | Opens capsule; prediction used for `order` rank mode. |
| `pass_turn` | `{}` | Active Player | Safely passes and banks unbanked basket points. |
| `host_arbitrate` | `{"slot": int, "is_correct": bool}` | Host | Taps revealed capsule to flip between Correct and Bust. |
| `add_offline_player` | `{"name": str}` | Host | Registers couch participant into the local turn order. |
| `toggle_mode` | `{"mode": "single_device" \| "multi_device"}` | Host | Switches couch pass-and-play mode. |

### 5.5 Secret Santa (`secretsanta`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `update_wishlist` | `{"notes": str}` | Player | Saves wishlist text and gift preferences. |
| `set_exclusions` | `{"exclusions": list[str]}` | Player / Host | Sets list of player IDs this giver cannot be matched with. |
| `generate_matches` | `{}` | Host | Executes Hamiltonian derangement draw. |
| `reset_matches` | `{}` | Host | Clears current assignments and returns room to lobby. |
| `add_offline_player`| `{"name": str}` | Host | Adds family member without individual phone. |

### 5.6 Word Impostor (`impostor`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `submit_clue` | `{"clue": str}` | Active Player | Submits subtle text clue during clue loop. |
| `set_mod_oral_clue` | `{"target_id": str, "clue": str}` | Moderator | Logs spoken clue on behalf of an oral table speaker. |
| `vote_suspect` | `{"suspect_id": str}` | Player | Casts ballot against suspected Impostor. |
| `submit_steal` | `{"guess": str}` | Caught Impostor | Submits final guess for Citizen word to steal victory. |
| `blind_redraw` | `{}` | Host | Rerolls word pair without revealing either word to host. |

### 5.7 Codenames (`codenames`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `select_team` | `{"team": "red" \| "blue"}` | Player | Joins Red Team or Blue Team. |
| `set_spymaster` | `{"team": "red" \| "blue"}` | Player | Claims team's Spymaster view. |
| `submit_clue` | `{"word": str, "count": int}` | Spymaster | Submits clue word and permitted guess count. |
| `reveal_card` | `{"card_id": str}` | Operative | Taps card on 5×5 grid to reveal secret agent affiliation. |
| `pass_turn` | `{}` | Operative | Ends team's guessing turn prematurely. |

### 5.8 Emojinary (`emojinary`)

| Action Name | Key Parameters | Role | Description |
| :--- | :--- | :--- | :--- |
| `draw_emoji` | `{"emoji": str, "x": int, "y": int}` | Drawer | Places emoji onto canvas coordinate. |
| `remove_emoji` | `{"index": int}` | Drawer | Removes placed emoji from canvas. |
| `guess` | `{"msg": str}` | Guesser | Evaluates real-time word guess. |
| `reroll_word` | `{}` | Drawer | Rerolls prompt word during prep phase. |

### 5.9 Lupus in Tabula (`lupus`)

#### GM Cockpit Actions:

| Action Name | Key Parameters | Description |
| :--- | :--- | :--- |
| `record_night_action` | `{"stage_id": str, "target_id": str, "extra": dict}` | Logs night action from player pointing gestures. |
| `resolve_night` | `{}` | Executes all night actions and produces Dawn Report. |
| `set_night_stage` | `{"stage_index": int}` | Navigates GM Cockpit through night wakeup sequence. |
| `start_voting` | `{"system": "secret" \| "public"}` | Begins daytime nomination and execution trial. |
| `proceed_defense` | `{}` | Transitions top nominees to defense speech timer. |
| `proceed_final_vote` | `{}` | Opens final execution ballot. |
| `tally_vote` | `{}` | Computes verdict; executes condemned suspect. |
| `cancel_day_vote_veto`| `{}` | Mayor exercises executive veto to pardon target. |
| `set_status` | `{"player_id": str, "status": "alive" \| "limbo" \| "dead"}` | Directly forces player life status. |
| `trigger_gameover` | `{"winner": str, "reason": str}` | Concludes match and crowns winning faction. |

#### Player Actions:

| Action Name | Key Parameters | Description |
| :--- | :--- | :--- |
| `point_at_player` | `{"target_id": str}` | Sends real-time finger-pointing gesture to GM map. |
| `toggle_hand_raise` | `{}` | Raises hand during day discussion. |
| `vote_nominate` | `{"target_id": str}` | Votes to nominate suspect for defense trial. |
| `vote_final` | `{"suspect_id": str}` | Casts ballot on execution verdict. |
| `guess_angel` | `{"angel_id": str}` | Limbo soul attempts to guess Angel to revive. |
| `submit_ghost_message`| `{"message": str}` | Fallen spirit drafts spectral message for Gazette. |
| `submit_news_bulletin`| `{"message": str, "anonymous": bool}`| Submits news bulletin to Town Gazette. |

---

## 6. Server-to-Client (S2C) Event Matrix

### 6.1 Standard Engine Broadcast Pattern

In games adhering to the zero-spoiler projection standard, the server responds to state changes by transmitting a sanitized JSON state dictionary directly over the WebSocket:

```json
{
  "code": "ABCD1234",
  "phase": "playing",
  "round_num": 1,
  "players": [ ... ],
  "my_card": { ... },
  "version_counter": 171
}
```

### 6.2 Lupus Segregated Event Types

`lupus` separates messages by participant role:

| Event Type Name | Recipient | Payload Contents |
| :--- | :--- | :--- |
| **`gm_state`** | Game Master (`is_gm = True`) | Full unmasked room telemetry (`get_gm_view`), all hidden roles, pending night choices, notes. |
| **`player_state`** | Regular Player | Sanitized player view (`get_sanitized_player_view`) strictly masking secret cards and other roles. |
| **`player_kicked`** | Kicked Client | Notification: `{"type": "player_kicked", "message": str}`. |
| **`dm_received`** | Recipient Player | Private direct message packet: `{"sender": str, "text": str}`. |

### 6.3 Error Event Protocol

When a client submits an invalid, unauthorized, or malformed action:

```json
{
  "type": "error",
  "msg": "Only the host/moderator can approve swap proposals."
}
```

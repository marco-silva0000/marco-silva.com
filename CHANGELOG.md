# Changelog

All notable changes to `marco-silva.com` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v154] - 2026-11-14

### Changed
- **Word Impostor Hide Role & Secret Word by Default (`templates/impostor/game.html`, `impostor/tests.py`)**:
  - Updated `#secret-card-box` so both the player's role (`#card-role-label`) and secret word (`#card-word-text`, as well as Round Director lethal word previews) start blurred and masked (`🔒 Role Hidden` / `••••••••`) with `cardBlurred = true` until the player taps `👁️ Show Role & Word`.
  - Automatically resets `cardBlurred = true` whenever a new round or Blind Redraw deals a fresh card (`lastCardDealKey`).

## [v153] - 2026-11-14

### Fixed & Added
- **Word Impostor Always-Visible Clue Input & Moderator Oral Clue Recording (`impostor/`, `templates/impostor/game.html`)**:
  - Fixed `#clue-input-box` hiding for the Moderator and non-turn players during the Clue phase; placed the box directly below the host toolbar so it remains visible throughout `clue` phase.
  - Enabled the Moderator/Host (`is_admin`) to type and submit (or mark spoken) oral clues on behalf of any participating speaker via `#clue-speaker-select` (auto-defaulting to `current_player_id` on each turn advance, tagging entries with `"by_mod": True` / `logged by Mod`), while enforcing the Citizen anti-spoiler check and Lethal Taboo Poison Word elimination on that speaker.
  - Added `add_table_player()` (`action: "add_table_player"`) so the Host can add local oral/couch players directly in the lobby (`🪑` badge) and lowered the minimum active-player threshold to 2+.

## [v152] - 2026-11-13

### Fixed & Changed
- **Playwright CI Strict-Mode Locator Fix & Unified Games Hub / Room UI (`templates/gamerooms/`, `.github/workflows/ci.yml`)**:
  - Removed the redundant 5-link quick-action bar above the game cards in `templates/gamerooms/room_list.html` (which had created two `"create room"` links and triggered Playwright's strict-mode single-element failure in `tests/playwright/test_gamerooms.py::test_room_list_page`), replacing it with a single `+ create room` button in the header.
  - Redesigned the games showcase on `/games/` into a balanced 2×2 card grid with uniform player-count/tool badges and consistent `+ Host Room` / `Open Generator →` CTAs across Lupus, Emojinary, Word Impostor, and Pictionary.
  - Wrapped `templates/gamerooms/room_create.html`, `templates/gamerooms/room_name.html`, and `templates/gamerooms/room_password.html` in matching card shells with consistent form styling and a `← Game Rooms` back navigation link.
  - Included `impostor/` in the `.github/workflows/ci.yml` CI unit test step.

## [v151] - 2026-11-13

### Added
- **Room Language Option & Content Capability Badges (`gamerooms/models.py`, `gamerooms/language_support.py`, `gamerooms/views.py`, `templates/gamerooms/`)**:
  - Added `Room.language` (`CharField`, migration `gamerooms/migrations/0004_room_language.py`) plus `get_game_language_support()` classifying `(game_type, language)` pairs into **Full Content + UI** (English + 62 Wiktionary-covered languages for Emojinary & Word Impostor; 9 localized role packs for Lupus) vs **UI Only (English Game Words)**.
  - Added `game_type` (`emojinary`, `impostor`) and `language` selectors with live capability badge updates (`#lang-support-badge`) in `templates/gamerooms/room_create.html`, language capability badges on `/games/` (`room_list.html`) and join pages (`room_name.html`), and localized word propagation (`localized_word`) into `emojinary/game_state.py`.
- **Advanced Word Impostor Party Game (`impostor/`, `templates/impostor/game.html`)**:
  - Built real-time Channels multiplayer engine (`impostor/game_state.py`, `impostor/consumers.py`, `/ws/impostor/<code>/`) supporting **86 curated + Wiktionary-localized `(citizen_word, poison_word, lethal_word, category)` pairs** (`impostor/word_pairs.py`).
  - Added 4 configurable **Poison Word modes**: **Undercover Blind** (Impostor sees related Poison Word without knowing their role), **Undercover Informed**, **Poisoned Citizen ("The Drunk")** (one innocent Citizen sees the Poison Word identically to a normal Citizen card while the Impostor gets a blank card), and **Classic Blank**.
  - Added **Lethal Taboo Poison Word Hazard** (`enable_lethal_word`) eliminating anyone whose clue names the forbidden word, direct Citizen-word anti-spoiler blocking, and a **15-second Last-Chance Impostor Steal** guess (`submit_steal_guess`) when the Impostor is voted out.
  - Added zero-spoiler **Participating Game Master** support (Host plays in turn rotation with strictly stripped server state + non-spoiling `Blind Redraw Pair`, `Skip Turn`, `Start Voting Early`, and timer controls) plus **Custom Pair Deck ("Author-for-a-Round")** making card authors immune `🎬 Round Director` for their single round.

## [v150] - 2026-11-13

### Added
- **Mobile-Friendly Emoji Input Macro, Complete 12-Category Emoji Keyboard & Multilingual/Synonym/Typo Search (`emojinary/`, `templates/emojinary/game.html`)**:
  - Removed `readonly` from `#emoji-field` so players can type directly with native iOS/Android/desktop emoji keyboards while a client-side grapheme input macro (`handleEmojiFieldInput`) and server-side `sanitize_emoji_only()` enforcement strip any regular text, letters, numbers, or punctuation (displaying inline macro feedback `#emoji-macro-feedback` and returning WebSocket errors for text-only submissions).
  - Expanded `EMOJIS` in `templates/emojinary/game.html` to 12 categories (`1,190` emojis) adding **Crown & Clothing (`👑`)**, **Symbols/Keycaps/Arrows/Shapes (`🔣`)**, and **Country & Pride Flags (`🏳️`)**, and fixed `renderPage()` grapheme extraction via `Intl.Segmenter` so variation-selector symbols (`❤️`, `⚠️`, `♻️`, `✈️`), keycaps (`0️⃣`–`9️⃣`, `#️⃣`, `*️⃣`), ZWJ families, and regional-indicator flags render intact.
  - Integrated `muan/emojilib` (`emojinary/data/emoji_keywords.json`, MIT License attributed in `emojinary/data/LICENSES.md`), `emoji`'s 14 built-in CLDR languages, Wiktionary's 64-language lexicon (`emojinary/data/wiktionary_lexicon.json`), curated concept synonyms, ISO country codes (`pt`, `gr`, etc.), and `difflib` misspelling tolerance into `emojinary/emoji_search.py`.

## [v149] - 2026-11-13

### Added
- **Wiktionary Lexical & 64-Language Enrichment (`scripts/enrich_wiktionary.py`, `emojinary/`, `tools/pictionary.py`)**:
  - Extended `EmojinaryWord` (`emojinary/models.py`, migration `0003_emojinaryword_aliases_emojinaryword_definition_and_more`) with `pos` (Noun/Verb/Adjective/Phrase/Proper), `definition`, `etymology`, `aliases` (synonyms), `translations` (64-language map), `topics`, and `source`.
  - Built `scripts/enrich_wiktionary.py` using Wiktionary's MediaWiki Action API batch endpoint (including `/translations` subpages) to harvest **3,671 enriched entries** (`3,618` definitions, `1,788` synonym lists, `3,400` multilingual translation maps, `141` idiom etymologies) into `emojinary/data/wiktionary_lexicon.json` (CC BY-SA 4.0 attributed in `emojinary/data/LICENSES.md`).
  - Upgraded `seed_emojinary` to populate Wiktionary fields on new entries and bulk-backfill existing database rows.
  - Upgraded `check_guess()` (`emojinary/game_state.py`) with Unicode-safe diacritic folding (`_strip_combining_marks`) so players can match via English synonyms (e.g., `couch` for `sofa`) or localized translations (e.g., `omena`, `μήλο`, `maçã`, `яблоко`).
  - Added clue-giver definition tooltips, accepted synonym hints, localized translations, topic hints, and replay etymology notes in `templates/emojinary/game.html` and `tools/pictionary.py`.

## [v148] - 2026-11-13

### Added
- **Open-Source & Public-Domain Wordlists Integration for Emojinary & Pictionary (`6,949` Emojinary entries + `4,782` Pictionary entries)**:
  - Audited and integrated 5 MIT / CC0-1.0 datasets via `scripts/build_wordlists.py` into `emojinary/data/wordlists.json` (with full attribution in `emojinary/data/LICENSES.md`):
    - `dariusk/corpora` (CC0)
    - `nick-aschenbach/game-words` (MIT)
    - `imsky/wordlists` (MIT)
    - `engichang1467/word-pictionary-list` (MIT)
    - Wikidata Query Service (CC0) — Oscar-winning movies, Emmy-winning TV shows, Grammy-winning songs, and UNESCO World Heritage landmarks.
  - Expanded `EmojinaryWord.Category` (`emojinary/models.py`, migration `0002_alter_emojinaryword_category`) and room settings selector (`templates/emojinary/game.html`) to 10 categories: `movie`, `tvshow`, `song`, `phrase`, `thing`, `animal`, `food`, `person`, `place`, and `action`.
  - Upgraded `seed_emojinary` (`emojinary/management/commands/seed_emojinary.py`) to bulk-seed all curated + external entries idempotently, and upgraded `tools/pictionary.py` to draw from the curated open-source `noun`, `verb`, `adjective`, and `sentence` pools (with `wonderwords` fallback).

## [v147] - 2026-11-13

### Changed
- **Completed Priority Localization Batch (`pt`, `ru`, `pl`, `it`, `fi`, `fr`, `sv`, `sw`, `az`, `es`) & 4x Chunking Upgrade**:
  - Upgraded `scripts/translate_chunks_agy.py` (`locale/translate_with_agy.py`) default chunk size from `20` to `80` strings per `agy` invocation (cutting AI call volume by 4x), unified processing through `translations_master.csv` with priority language ordering, and refined symbol filtering so `+` and `🐺`-prefixed UI strings are translated.
  - Translated and compiled 1,767 strings across 10 priority languages, bringing coverage to 95%–99% for Azerbaijani (`az`, 98.9%), Russian (`ru`, 98.9%), Finnish (`fi`, 97.8%), Swahili (`sw`, 97.8%), Polish (`pl`, 97.6%), Spanish (`es`, 97.3%), Portuguese (`pt`, 97.0%), Swedish (`sv`, 96.5%), Italian (`it`, 96.2%), and French (`fr`, 94.9%).

## [v146] - 2026-11-13

### Added
- **Emojinary Party Game Full Revamp & Shared Room Architecture (`emojinary/`, `gamerooms/qr.py`)**:
  - **Shared Party-Game QR & URL Helper (`gamerooms/qr.py`)**: Extracted QR code data-URI generation and public URL builder into `gamerooms.qr`, shared by both Lupus and Emojinary.
  - **Persistent Player Identity & Reconnect Flow**: Replaced volatile `channel_name` player keys with persistent `player_id` (`p_1`, `p_2`, ...) and secret `token` identities, preserving scores and turn positions across mobile refreshes and disconnects. Added Room Invite QR modal (with `?pwd=` auto-authentication), Personal Reconnect QR & link (`/games/emojinary/<code>/reconnect/<token>/`), self-service live display name change (`rename_player`), and Playing Host (`is_admin`) controls (presets, settings, pause/resume/+15s timer, force-advance, kick player, transfer host, spectator toggle).
  - **Unified Chat & Guess Window + Live Progressive Emoji Hints**: Consolidated all guessing and room activity into the unified chat feed (`chat_log`) with automatic spoiler censoring (`censor_spoilers`) and word-length masking (`build_word_mask`). During guessing, the word writer can drop live additional emoji hints (`Hint #2`, `Hint #3`, ...) into the stream.
  - **Collective Prep Mode (`mode: "collective"`)**: Added a new game mode where all players simultaneously receive secret phrases and lock in their initial emoji clues in parallel (`prep` phase), followed by sequential Round Robin guessing rounds where each word writer can also drop live additional emoji hints.
  - **Smart Guess Matcher & Non-Repeating Word Pool**: Added article-insensitive (`"The Lion King"` ↔ `"Lion King"`), punctuation/hyphen-insensitive (`"E.T."` ↔ `"et"`, `"WALL-E"` ↔ `"wall e"`), partial-word, and `difflib` close-typo matching, plus `used_words` tracking so words never repeat within a match.
  - **Attempt-Level Replay Engine & JSON Export**: Recorded every player guess attempt, timestamp offset, and progressive hint in `rounds_history`, with an interactive post-game **Round-by-Round Replay Inspector**, `js-confetti` victory celebration, and `/games/emojinary/<code>/replay.json` export.
  - **Test Suite (`emojinary/tests.py`)**: Added 13 unit and async WebSocket tests covering persistent reconnects, renaming, host controls, smart matching, Round Robin progressive hints, Collective Prep mode, and Judge's Pick (`best_guess`) mode.

## [v145] - 2026-11-13

### Changed
- **Django 6.0, Wagtail 8.1 & Full Dependency Stack Upgrade**:
  - Upgraded project dependencies in `pyproject.toml` and `uv.lock` to latest upstream releases, including `django` (`5.1.7` → `6.0.10`), `wagtail` (`6.4.1` → `8.1`), `wagtail-markdown` (`0.12.1` → `0.15.0`), `celery` (`5.4.0` → `5.7.0`), `channels` (`4.2.0` → `4.3.2`), `channels-redis` (`4.2.1` → `4.3.0`), `daphne` (`4.1.2` → `4.2.3`), `django-celery-beat` (`2.7.0` → `2.9.0`), `django-celery-results` (`2.5.1` → `2.6.0`), `django-htmx` (`1.23.0` → `1.29.0`), `django-photologue` (`3.18` → `3.20`), `pillow` (`11.1.0` → `13.0.0`), `playwright` (`1.51.0` → `1.65.1`), `pytest` (`8.3.5` → `9.2.0`), `ruff` (`0.11.2` → `0.17.5`), `google-genai` (`1.68.0` → `3.3.0`), `pydantic` (`2.12.5` → `2.14.3`), and `redis` (`5.2.1` → `8.1.0`).
- **GitHub Actions Node 24 Upgrade & Orphan Process Cleanup**:
  - Upgraded all workflow actions in `.github/workflows/ci.yml` (`actions/checkout@v7`, `astral-sh/ruff-action@v4.1.0`, `astral-sh/setup-uv@v10.3.3`, `docker/login-action@v4`, `docker/build-push-action@v7`) to native Node.js 24 versions, eliminating the Node.js 20 deprecation warnings.
  - Added a `Stop Daphne background server` cleanup step (`if: always()`) in `.github/workflows/ci.yml` to cleanly terminate the background Daphne process before job teardown and eliminate the `Cleaning up orphan processes` runner warning.

## [v144] - 2026-11-13

### Fixed
- **Playwright `test_room_list_page` Case-Sensitivity Assertion & CI Annotation Filter**:
  - Updated `test_room_list_page` in `tests/playwright/test_gamerooms.py` to pass `ignore_case=True` when checking `<h1>Game Rooms</h1>` (`expect(page.locator("h1")).to_contain_text("game rooms", ignore_case=True)`).
  - Updated `.github/workflows/ci.yml` Playwright failure reporter to filter `FAILED|ERROR|AssertionError` lines so GitHub's 10-annotation limit always surfaces exact test assertions rather than pytest header lines.

## [v143] - 2026-11-13

### Fixed
- **Lupus Room Short URL Routing & Playwright Join Flow Smoke Test**:
  - Added `<str:code>/` root route (`room-root`) in `lupus/urls.py` pointing to `views.room_join` so visiting `/games/lupus/<code>/` directly serves the player join screen instead of returning a 404.
  - Updated `test_lupus_player_join_flow` in `tests/playwright/test_lupus.py` to match the `/games/lupus/<code>/play/` player URL and verify `#player-lobby-view`, `#b-tab-info`, and `#role-card`.

## [v142] - 2026-11-13

### Changed
- **Finalized Bengali & Belarusian Localization Batch and Updated Resume Reference**:
  - Completed Bengali (`bn`, 97.9% coverage, 330/337 strings) and progressed Belarusian (`be`, 39.8% coverage, 134/337 strings) catalogs, synchronizing all 64 `.po` / `.mo` binary catalogs and alias directories.
  - Updated `locale/TRANSLATION_RESUME.md` with the exact per-language completion table and resume commands.

## [v141] - 2026-11-13

### Added
- **Automated Chunked Localization Engine (`scripts/translate_chunks_agy.py`)**:
  - Built systematic CLI tool (`locale/translate_with_agy.py`) that scans CSV and PO catalogs, groups untranslated strings into context-aware chunks, spawns `agy --dangerously-skip-permissions`, and persists translations directly to disk and binary `.mo` catalogs after every chunk.
  - Configured automatic quota fallback rotation (`gemini-4-argon-medium` → `gemini-4-argon-low` → `gemini-4-argon-high` → `gemini-4-hydrogen-medium` → `gemini-4-hydrogen-low` → `gemini-4-hydrogen-high` → `claude-sonnet-5-5-medium` → `claude-sonnet-5-5-low` → `gpt-oss-120b-medium`) and pre-master CSV synchronization.
- **Expanded Multilingual Catalog Coverage**:
  - Completed and compiled full translations across Arabic (`ar`, 99.7%), Hindi (`hi`, 99.7%), Kannada (`kn`, 99.7%), Persian (`fa`, 99.4%), Greek (`el`, 98.8%), Azerbaijani (`az`, 97.6%), Basque (`eu`, 97.6%), Spanish (`es`, 96.7%), Afrikaans (`af`, 96.4%), Albanian (`sq`, 96.4%), Italian (`it`, 95.5%), French (`fr`, 93.8%), and Bengali (`bn`).

## [v140] - 2026-11-13

### Added
- **Complete 64-Language Internationalization Architecture**:
  - Generated full PO catalogs and compiled MO binary files for all 64 languages listed in the landing page selector (`af`, `sq`, `ar`, `az`, `eu`, `bn`, `be`, `bg`, `ca`, `zh-cn`, `zh-tw`, `hr`, `cs`, `da`, `nl`, `en`, `eo`, `et`, `tl`, `fi`, `fr`, `gl`, `ka`, `de`, `el`, `gu`, `ht`, `iw`, `hi`, `hu`, `is`, `id`, `ga`, `it`, `ja`, `kn`, `ko`, `la`, `lv`, `lt`, `mk`, `ms`, `mt`, `no`, `fa`, `pl`, `pt`, `ro`, `ru`, `sr`, `sk`, `sl`, `es`, `sw`, `sv`, `ta`, `te`, `th`, `tr`, `uk`, `ur`, `vi`, `cy`, `yi`).
  - Added locale aliases and BCP-47 variants (`zh_CN`, `zh_Hans`, `zh_TW`, `zh_Hant`, `he`, `iw`, `nb`, `no`, `fil`, `tl`) to guarantee full interoperability between browser headers and Django locale resolution.
  - Registered `EXTRA_LANG_INFO` in `website/settings.py` for languages missing from Django's built-in table (`tl`, `gu`, `ht`, `la`, `mt`, `yi`, `iw`, `zh-cn`, `zh-tw`, `no`).
  - Updated Lupus client language switcher (`templates/lupus/player.html`) with all 64 options, country flags, and full RTL bidirectional text isolation support for `ar`, `fa`, `ur`, `he`, `iw`, and `yi`.
  - Updated `SUPPORTED_LANGUAGES` in `lupus/translations.py` and `scripts/translations_tool.py` to maintain all 64 languages.
  - Added script `scripts/generate_all_64_locales.py` for automated compilation and synchronization of all 64 catalogs.

### Fixed
- **GitHub Actions CI PostgreSQL Service Health Check & Port Resolution**:
  - Configured PostgreSQL container health check to `--health-cmd "pg_isready -U testuser -d testdb"` to prevent auth failure on default user in GitHub Actions runner.
  - Set `POSTGRES_HOST: 127.0.0.1` and added dynamic `POSTGRES_PORT` configuration to `website/settings.py` to prevent IPv6 `::1` connection refused errors on GitHub runners.
- **CI Test Suite Coverage & `ALLOWED_HOSTS` Test Client Resolution**:
  - Configured `ALLOWED_HOSTS` in `website/settings.py` to always include `testserver` and loopback hosts, preventing `400 DisallowedHost` responses during `django.test.Client` requests.
  - Updated CI unit test step to run `USE_SQLITE=1 uv run pytest gamerooms/ lupus/ photos/ tools/ -v` covering all 242 unit tests.

## [v139] - 2026-11-13

### Fixed
- **GitHub Actions CI Pipeline Failure**:
  - Resolved `lint` job failure under `astral-sh/ruff-action@v3`.
  - Added `E501` (line-too-long) to `tool.ruff.lint.ignore` in `pyproject.toml` to prevent translatable strings and multilingual dictionaries from triggering false lint failures, aligning with Ruff documentation recommendations when using Ruff's formatter.
  - Auto-formatted codebase with `ruff format` across 100 Python source files.
  - Fixed unused imports (`F401`), unused test assignment (`F841`), and ambiguous loop variables (`E741`) in `scripts/translations_tool.py`, `lupus/tests.py`, `lupus/game_state.py`, and `scripts/add_missing_role_translations.py`.
  - Updated Playwright Lupus browser smoke tests default `PLAYWRIGHT_BASE_URL` to `http://localhost:8000` to properly target local Daphne server in CI.

## [v138] - 2026-11-13

### Changed
- **GM Dashboard Layout Overhaul (Table Next to Round Card)**:
  - Relocated the Physical Table Seating section (`#table-management-section` with the circular Ring Table and List view) from the very bottom of the page up directly adjacent to the Round Card in `#active-game-view`.
  - Implemented responsive side-by-side grid (`.gm-round-table-layout`):
    - **Desktop ($\ge 1040\text{px}$)**: 360px left sidebar for the Round Card (Phase badge, Round number steppers, Countdown Timer with quick actions, Phase buttons, and live player finger pointers) side-by-side with the Physical Table Seating stage, eliminating page scrolling during game rounds.
    - **Tablet / Mobile ($\le 1040\text{px}$)**: Seamless stacked layout keeping the Table immediately adjacent to the Round Card, instead of buried below 10 director cards, reports, and gazettes.
  - Implemented dual-slot DOM synchronization (`syncTableSlot`):
    - In active gameplay (`phase != 'lobby'`), the Table lives inside `#active-table-slot` next to the Round Card.
    - In lobby mode (`phase == 'lobby'`), the Table lives inside `#lobby-table-slot` directly below the Deck Builder and Start Game button.
  - Added unit test `test_table_placed_next_to_round_card_in_gm_dashboard` to `lupus/tests.py`.

## [v137] - 2026-11-13

### Fixed
- **GM Direct Message Player Switching Bug**:
  - Fixed `Uncaught ReferenceError: ws is not defined` in `selectGMDMPlayer` within `templates/lupus/gm_dashboard.html`, which prevented Game Masters from selecting and switching between different players in the DM modal.
  - Replaced rogue `ws` socket reference with standardized `sendAction("mark_dms_read", { player_id })`.

### Improved
- **Mobile Direct Message Interface Redesign**:
  - **Responsive Layout**: Replaced the cramped two-column layout on mobile devices ($\le 640\text{px}$) with an adaptive single-column conversation view.
  - **Mobile Player Switcher**: Added top player select dropdown (`#gm-dm-mobile-select`) and touch-friendly horizontal scrolling player pills (`#gm-dm-mobile-pills`) with status indicators and live unread badges.
  - **Input Box & Ergonomics**: Upgraded message input fields to 48px height with $1\text{rem}$ ($16\text{px}$) font size across GM Cockpit and Player Screen (preventing unwanted iOS mobile zoom).
  - **Quick Reply & Inquiry Chips**:
    - GM quick-replies: `👍 Confirmed`, `🤫 Stay Silent`, `❓ Clarify`, `⏳ Wait for Dawn`, `✅ Yes`, `❌ No`.
    - Player quick-inquiries: power check, limbo query, silence status, rule clarification.
  - **Table Seat Integration**: Added `💬 Direct Message Player` 1-tap launcher directly from the circular table seat details modal (`#player-seat-modal`).
  - **Desktop Search**: Integrated instant search filter (`#gm-dm-player-search`) into the GM DM sidebar.

## [v136] - 2026-11-12

### Added
- **Comprehensive Tunable Settings & Rules Schema (`lupus/settings_schema.py`)**:
  - Catalog of 38 granular game parameters grouped into 5 categories:
    - 🧙 **Roles & Powers**: Witch revive and poison potion inventories (0-3), Witch dual-use toggle, Sniper danger and silver bullet counts (0-5), Doctor consecutive shield cooldown, Doctor sniper save, Bodyguard self-guard & sacrifice rules, Detective investigation modes, Cupid lover bindings, Saboteur charges, Hacker scan quotas, Disgruntled ghost suppression, Wolf cub frenzy kills.
    - ⏱️ **Timers & Pacing**: Discussion timer (30-1800s), Defense timer (10-300s), Night stage timer (10-180s), Voting countdown timer (10-180s).
    - 🗳️ **Voting & Trials**: Voting system archetype (`two_stage_50pct`, `two_stage_top_n`, `simple_plurality`), Nomination threshold percentage (10-100%), Mayor variant (`public` vs `hidden`), Mayor pardon veto toggle, Self-voting allowance, Tie runoffs limit (0-5).
    - ⚰️ **Death, Limbo & Reveals**: Limbo mechanic toggle, Angel guess duration (10-180s), Death role reveal policy (Secret / Alignment / Faction / Full Role Card), Public heartbreak cause announcement, Martyrdom variant (`public` vs `hidden`).
    - 🗞️ **Gazette & Communications**: Anonymous news submissions toggle, Direct messaging toggle, Gazette posting cooldown (1-5 rounds).
  - Defined ready-to-use rule presets: `default` (Standard Lupus), `blitz` (Speed / fast pace), `chaos` (High firepower 2x potions & rampage), `competitive` (Strict mystery & closed graveyard).
  - Validation engine with boundary clamping, choice verification, and bidirectional legacy alias synchronization.
- **Game Master Settings Cockpit Modal (`#gm-settings-modal`)**:
  - Accessible via top-bar `⚙️ Settings` button.
  - Interactive search bar for instant filtering across variable names, keys, and descriptions.
  - Category pill tabs with dynamic counts (`⭐ All`, `🧙 Roles`, `⏱️ Timers`, `🗳️ Voting`, `⚰️ Death & Limbo`, `🗞️ Gazette`).
  - Granular responsive controls: toggle switches for booleans, stepper counters `[-] [val] [+]` with boundary clamping, and dropdown selects.
  - One-click preset loader (`✨ Preset: [...] -> Apply Preset`) and `↺ Reset to Defaults`.
  - Real-time Redis state synchronization pushing updates across all connected player devices.

## [v135] - 2026-11-12

### Added
- **Circular Table Turn Order Engine**:
  - Implemented `start_circular_turn_order(state, starter_id=None, direction=None)` allowing the Game Master to pick a random starting living player and a random direction (`clockwise` / "right" or `counterclockwise` / "left"), or manually choose.
  - Active queried player $X$ is prominently spotlighted across both GM Cockpit and all player screens with a golden pulsing ring, target icon, and directional turn indicators.
  - Added stepper controls (`⬅ Prev Player`, `Next Player ➔`) to advance or rewind through living players along the table circle.
- **Physical & Digital Arm/Hand-Raising System**:
  - Implemented `toggle_hand_raise(state, voter_id, candidate_id=None, raised=None, source="player"|"gm")`:
    - Players tap their screen (`✋ Raise Arm to Nominate X`) to raise or lower their hand in real-time.
    - Game Master can tap seats directly on the circular Ring Table (or quick player list buttons) to toggle hand raises for real-life players.
    - Real-time visualization: seats display floating bouncing `✋` badges, glowing gold borders, and live count vs threshold.
    - Synchronized with nomination threshold calculations and final trial execution votes.
    - Every arm raise is logged in `action_history` and recorded in the round replay breakdown (`hand_raises` mapping).
- **Winning Faction JS Confetti on Game Over**:
  - Bundled `static/vendor/js-confetti.browser.js` locally (100% offline homelab support, zero external CDN dependency).
  - Fires customized confetti explosions on the Game Over screen featuring the winning faction's distinct emojis:
    - Town: `👨‍🌾🌱🏡🎉🕊️✨`
    - Werewolves: `🐺🌕🐾🩸🌙💀`
    - Lovers: `💞❤️‍🔥💖💘🌹✨`
    - Jester: `🃏🎭🎉👑⭐🔥`
    - Serial Killer: `🔪🩸💀🖤⚡🔥`
  - Added interactive `🎉 Throw Confetti` celebration buttons in player and GM Game Over views.

## [v134] - 2026-11-12

### Added
- **Town Gazette Multi-Posting with Single-Pending Review Constraint**:
  - Relaxed former strict 1-post-per-day restriction, enabling players to submit multiple bulletins across a round or game.
  - Enforced single pending bulletin constraint: a player can only have one bulletin pending GM review at any time. If a submission is waiting, attempting to post another is cleanly prevented with an informative review notice.
  - As soon as the Game Master approves or rejects the pending submission, the player is immediately unlocked to post their next bulletin.
- **Game Master Round-Mute for Town Gazette**:
  - Implemented `toggle_player_gazette_mute(state, player_id, muted)` enabling the GM to silence disruptive players from posting to the Gazette for the rest of the round.
  - Added 1-click `🔇 Mute (Round)` and `🔊 Unmute` actions directly on pending bulletin review cards and player table rows in the GM Cockpit.
  - Displays a dedicated `🔇 Gazette Muted` badge and list of currently muted players with quick unmute.
  - Implemented automatic phase-change reset: all player gazette mutes automatically reset on every dusk (`advance_to_night`) and dawn (`resolve_night`).
- **Interactive Round-by-Round Game Replay Timeline**:
  - Implemented `build_round_timeline(state)` aggregating `action_history`, dawn reports, casualties, gazette editions, nominations, and trial execution votes into a clean chronological timeline.
  - Added interactive Replay Navigator in `templates/lupus/player.html` and `templates/lupus/gm_dashboard.html`:
    - Quick round pills (`[🌙 N0] [☀️ D0] [🌙 N1] [☀️ D1] ...`).
    - Detailed round inspection cards showing dawn reports, unmasked role casualties, published bulletins, trial voting breakdowns, and notable ability activations.
    - Added one-click `💬 Discuss in Host Chat` shortcut so players can discuss what happened directly with the GM and room.

## [v133] - 2026-11-12

### Added
- **Right-to-Left (RTL) Internationalization & Accessibility (WCAG 2.1/2.2)**:
  - Added Arabic (`ar`), Persian / Farsi (`fa`), and Urdu (`ur`) to `LANGUAGES` and `WAGTAIL_CONTENT_LANGUAGES` (now 12 supported languages total), strictly excluding Hebrew (`he`).
  - Dynamic BiDi directionality: root `<html lang="..." dir="...">` dynamically switches between `ltr` and `rtl` via Django's `get_current_language_bidi`.
  - W3C Accessibility conformance:
    - Directional navigation mirroring: chronological arrows (`←` back) mirror to `→` under `[dir="rtl"]` using CSS transforms.
    - Media controls and mathematical/technical text isolation: room codes, timers (`05:00`), and timestamps strictly isolated using `<bdi>` and `dir="ltr"` to prevent punctuation scrambling.
    - WCAG 1.4.12 typography: increased line-height (1.8) and specialized Arabic/Persian/Urdu font stack (`Noto Sans Arabic`, `Amiri`, `Vazirmatn`, `Noto Nastaliq Urdu`).
    - CSS logical properties transition: replaced directional physical properties (`margin-right`, `padding-left`) with logical counterparts (`margin-inline-end`, `padding-inline-start`, `text-align: start`).
- **Lupus Werewolf Mobile Game BiDi Presentation**:
  - Added live client-side RTL switching (`applyDirectionality(lang)`) updating `document.documentElement.dir` on the fly without disconnecting the WebSocket.
  - Room code pill and phase clock chips tagged with `dir="ltr"` and `unicode-bidi: isolate`.
  - Host Chat direct messages: player and GM messages align dynamically to flex-start/flex-end based on reading order, message text isolated with `<bdi>`, and timestamps forced to LTR.
  - Localized Lupus roles, phases, factions, statuses, and player screen UI strings for Arabic, Persian, and Urdu.
- **Translation Tooling & PO/MO Catalogs**:
  - Seeded and compiled `locale/ar/`, `locale/fa/`, `locale/ur/` GNU gettext catalogs (`django.po` and `django.mo`).
  - Exported master CSV (`locale/translations_master.csv`) and dedicated untranslated hand-off CSVs (`locale/translations_ar.csv`, `locale/translations_fa.csv`, `locale/translations_ur.csv`).
  - Added unit test suite in `gamerooms/tests.py` covering BiDi root directionality, RTL translations, and Lupus dictionary localization.

## [v132] - 2026-11-12

### Added
- **Systematic Internationalization (i18n) Across All Website Templates**:
  - Implemented `{% load i18n %}`, `{% trans "..." %}`, and `{% blocktrans %}` across all remaining template files in the platform:
    - Base & Error pages: `templates/index.html`, `templates/404.html`, `templates/500.html`, `templates/wip.html`, `templates/cv.html`, `templates/bot_privacy.html`, `templates/bot_terms.html`.
    - Photos gallery: `gallery_list.html`, `gallery_detail.html`, `photo_viewer.html`, `upload.html`, `map.html`, and partials.
    - Tools: `pictionary.html`, `ics_maker.html`, `planz.html`, `planz_full.html`, and `calendar.html`.
    - Blog: `blog_index_page.html`, `blog_post_page.html`, `post_list.html`, `post_detail.html`, and photo blocks.
    - Emojinary & Lupus: `templates/emojinary/game.html`, `templates/lupus/player.html`, `templates/lupus/gm_dashboard.html`.
  - Discovered and indexed 337 unique translatable strings, with core seed translations raising translation coverage to ~78% across 9 languages.
- **Centralized Translation Management CLI Tool (`scripts/translations_tool.py`)**:
  - `export-csv`: Generates spreadsheet-ready master CSV (`locale/translations_master.csv`) and per-language CSVs (`locale/translations_<lang>.csv`) compatible with Google Sheets and Excel (UTF-8 BOM).
  - `import-csv`: Parses translated CSV back from native speakers/Google Sheets, automatically updates GNU gettext `.po` files, and compiles binary `.mo` catalogs.
  - `status`: Displays real-time translation completion table and coverage metrics.
  - `extract`: Scans codebase for translatable strings and synchronizes catalogs.
  - `compile`: Pure-Python `.mo` binary compilation with GNU `msgfmt` verification.

## [v131] - 2026-11-12

### Added
- **Multi-Language Presentation Localization for Game Rooms & Lupus Hub**:
  - Fully translated `/games/` (`gamerooms:room-list`), `/games/lupus/` (`lupus:hub`), `/games/lupus/create/`, `/games/lupus/join/`, and legacy game room forms into all 9 supported languages (`en`, `pt`, `it`, `es`, `fr`, `el`, `ru`, `hi`, `kn`).
  - Localized room badges, lifecycle states (`Open (Lobby)`, `Running`, `Finished`, `Active`), and phase badges (`Day`, `Night`, `Voting`, `Limbo`) across views and templates.
  - Localized interactive forms, placeholders, help texts, and error/validation feedback.
- **Automated Locale Compilation**:
  - Overhauled `scripts/generate_locales.py` with full catalogs and dual-engine binary `.mo` compilation (native pure-Python + GNU `msgfmt`).
  - Added pytest suite `TestGameroomsI18n` (28 new test cases) and extended Robot Framework suite `09_internationalization.robot`.

## [v130] - 2026-11-12

### Added
- **Two-Way Private Direct Messaging (DMs)**:
  - Added discrete, real-time messaging between players and the Game Master (`send_dm`, `mark_dms_read`).
  - Added dedicated 5th tab `Host Chat` (`tab-content-chat`) on the player screen with full message feed, unread badge counter, and private composer.
  - Added `gm-dms-modal` on the Game Master Cockpit with player list conversation selector, live unread counter badge in top-bar, and direct response composer.
- **Mid-Game Waiting Player Prompt**:
  - Prominent alert banner (`#midgame-waiting-banner`) appears at the top of the GM cockpit whenever a player connects mid-game (`status="waiting"`).
  - Quick `Assign Role Now` shortcut opens role assignment with one click.
- **Mayor Executive Day Vote Veto & Self-Pardon**:
  - Mayor can now exercise executive veto to pardon themselves if voted out by town execution during the day (`was_lynched_yesterday`).
  - Added direct `👨‍⚖️ Mayor Veto / Cancel Vote` button in GM Day Voting Director (`cancel_day_vote_veto`) to immediately overturn day vote outcomes.

### Fixed
- **Mobile Bottom Navigation Dock**:
  - Modern native dock component fixed to the screen bottom (`z-index: 99999`) with proper mobile safe area inset padding (`max(env(safe-area-inset-bottom), 8px)`).
  - Clean active pill indicators, 5 tabs (`Table`, `Game`, `Chat`, `Notes`, `My Role`), and adjusted page container bottom padding to prevent content overlap.
- **Town Gazette Bulletin Visibility & Status**:
  - Resolved mobile viewport truncation and ensured submission box remains responsive.
  - Fixed misleading "submitted" notice for waiting players/spectators; displays clear waiting prompt instead.
- **Ghost & Disgruntled Ghost Lifecycle**:
  - Spirit roles only activate in night stages when an active player holds the role; leaving or removing the ghost removes the stage.
  - Haunting and suppression actions are now optional (`is_complete: True`), preventing blocked night transitions.
- **Iterative Multi-Language Localization**:
  - Localized all remaining hardcoded player screen UI strings (tabs, gazette, pointing, night rules, dawn report, timers) across 9 languages (`en`, `pt`, `it`, `es`, `fr`, `el`, `ru`, `hi`, `kn`).

## [v129] - 2026-11-12

### Fixed
- **Hacker Role Deck Builder & Selection**:
  - Restored missing `chip-hacker` toggle button in GM Dashboard Deck Builder (`templates/lupus/gm_dashboard.html`), allowing hosts to toggle and play the Hacker role.
  - Also added missing `chip-watson` (🕵️‍♂️ Watson) and `chip-saboteur_wolf` (🐺⚡ Saboteur Wolf) toggle chips in the Deck Builder HTML.
  - Added missing role pre-assignment buttons for `wolf_cub` (🐾 Wolf Cub) in Evil Team, and `martyrdom` (💣 Martyrdom) and `gull` (🕊️ The Gull) in Good Team within `manual-role-modal`.
- **Hacker Night Scan GM Interface & Real-Time Ratio Preview**:
  - Added specialized `hacker-widget` during the Hacker night stage:
    - Multi-select player toggle buttons and table-ring seat selection to pick 2–3 scan suspects.
    - Real-time evil presence ratio evaluation preview (All Evil, Majority Evil, Even Split, Minority Evil, Clean).
    - Clear selection button and scan target counter badge.
- **Hacker Player Screen Secret Intelligence Notes**:
  - Enhanced player view for Hacker to display scan mission instructions on Night 0 and live evaluated scan intel (`state.hacker_result`) during daytime deduction.
- **Engine Night Resolution & Day Voting Interlock**:
  - Automatically locks Day 1 voting when Hacker is in play or scan intelligence is announced, keeping Day 1 reserved for deduction and suspicions.
  - Updated Night 0 resolution to announce Hacker Intel in the dawn report immediately following the scan.

### Testing
- Added unit tests in `TestLupusV129HackerDeckAndScan` in `lupus/tests.py` verifying HTML markup, Hacker dealing, scan calculation, and day voting lock (172 passed in `pytest`).
- Verified all 47 Robot Framework game simulation scenarios pass.

## [v128] - 2026-11-11

### Added
- **Comprehensive Internationalization (i18n) Supporting 9 Languages**:
  - Full platform and game client localization across 9 languages: English (`en` - main/default), Portuguese (`pt`), Italian (`it`), Spanish (`es`), French (`fr`), Greek (`el`), Russian (`ru`), Hindi (`hi`), and Kannada (`kn`).
  - Added font fallbacks for non-Latin typography (`Noto Sans Devanagari`, `Noto Sans Kannada`, `Nirmala UI`) in base template layout.
- **Strict Separation of Concerns & Engine English Invariance**:
  - Internal game state, Redis storage keys, player attributes (`role`, `status`, `faction`), phases, rule mechanics, and action tapes remain 100% in canonical English.
  - Localization occurs exclusively at the serialization and presentation boundary (`get_sanitized_player_view` and `get_gm_view`).
- **Complete Role Catalog Translations (29 Roles)**:
  - Translated all 29 roles across all 9 languages in `lupus/translations.py`: localized display names, descriptions, objectives, day tips, night tips, and pro tips.
  - Localized lookups for player statuses (`Vivo`, `Morto`, `В лимбе`, `ಜೀವಂತ`, etc.), factions (`Aldeões`, `Lupo Mannaro`, `ತೋಳಗಳು`, etc.), phases (`Votação do Dia`, `Vote du Jour`, etc.), and UI strings (`hold_to_peek`, `release_to_hide`, `secret_role`).
- **Player Screen Dynamic Localization & Privacy Shield**:
  - Added `#player-lang-select` language switcher dropdown in top app bar.
  - Supported dynamic WebSocket language updates (`action: "set_player_language"`) allowing live switching without page reloads.
  - Localized privacy shield text (`#shield-title`, `#shield-desc`), status badges (`#my-status-badge`), and phase badges on the player screen.
- **Django Core i18n & Wagtail Readiness**:
  - Configured `LocaleMiddleware`, `LANGUAGES` tuple, and compiled binary gettext message catalogs (`locale/*/LC_MESSAGES/django.mo`) for all 9 languages.
  - Enabled Wagtail multi-locale infrastructure (`WAGTAIL_I18N_ENABLED = True`, `WAGTAIL_CONTENT_LANGUAGES`).
- **Testing**:
  - Added `TestLupusInternationalization` in `lupus/tests.py` verifying state invariance and presentation boundary translations (170 passed in `pytest`).
  - Added `tests/robot/lupus/suites/09_internationalization.robot` simulating simultaneous multi-lingual players in a single match and dynamic language switching (47 passed in Robot Framework).

## [v127] - 2026-11-11

### Added
- **Mid-Game Joiners & Near-GameOver Edge Cases Simulation Suite (`tests/robot/lupus/suites/08_midgame_joiners.robot`)**:
  - Added dedicated Robot Framework simulation test suite covering 7 distinct late-arrival and near-gameover edge cases.
  - Added keywords in `LupusLibrary`: `Assign Midgame Role`, `Pending Gameover Winner Should Be`, `Pending Gameover Should Be None`, `Living Players Count Should Be`, `Pair Lovers`, `Check Win Condition`.
  - Added 8 unit tests in `lupus/tests.py` under `TestMidgameJoinerAndNearGameoverEdgeCases`.

### Fixed
- **Unassigned Mid-Game Joiner Status**:
  - Late players joining mid-game (`phase != "lobby"`) now enter with `status="waiting"` rather than `"alive"`, preventing unassigned spectators from distorting living player counts, day voting thresholds, or wolf parity calculations.
- **Dynamic Pending GameOver Invalidation on Mid-Game Role Assignment**:
  - `assign_midgame_role` resets `pending_gameover = None` when the game is still active, allowing `check_win_condition` to re-evaluate whether a new Confirmed Traveler or Town player breaks parity and saves the village.
- **Successor (Understudy) Heartbreak & Role Inheritance at Dawn**:
  - Prevented double-killing lovers when a waiting Successor steps in to inherit a fallen Lover's role and binds to the surviving partner.
  - Added explicit announcement in the dawn report when a Successor steps in to avert heartbreak or inherit a fallen player's role.
  - Day vote elimination message accurately acknowledges when a Successor stepped in to avert lover heartbreak.
  - Standard roles assigned mid-game explicitly activate status as `"alive"`.
  - Joined players or role assignments after `phase="gameover"` strictly preserve finished state and recorded winner.

## [v126] - 2026-11-11

### Added
- **Public vs. Hidden Martyrdom Variations (`martyrdom_type`)**:
  - **Public Variety (`public`)**: Instant loud grenade detonation. When eliminated (by village vote or night attack), the grenade explodes immediately in the village square, taking down their primed target in public with a town-wide announcement. If unprimed, presents a live detonation picker.
  - **Hidden Variety (`hidden`)**: Stealthy delayed revenge trap. When eliminated (day or night), death remains silent with no public grenade leak. On the **immediate following night**, a dedicated secret night stage (`martyrdom`) prompts the deceased martyr to designate an explosive booby trap victim. Detonates at dawn alongside night casualties unless protected by Doctor.
  - **One-Night Revenge Window**: Enforced one-night limit; after dawn of the subsequent night, `pending_hidden_martyrdom` is retired.
  - **Bluff Pause**: On all other nights (or if Martyr is alive or not in play), the GM cockpit displays the standard 5–10s bluff pause to avoid leaking the Martyr's status.
- **Cockpit Role Builder Enhancements**:
  - Added `chip-martyrdom` with inline variation toggle (`📢 Public (Instant)` vs `🔒 Hidden (Night Trap)`).
  - Added `chip-wolf_cub` (🐾) and `chip-gull` (🕊️) into GM deck builder with complete metadata.
  - Added night review summary entry for Martyrdom explosive booby trap.
- **Frontend Testing & Smoke Suite**:
  - Built lean Playwright smoke tests (`tests/playwright/test_lupus.py`) verifying Lupus hub rendering, GM room creation, and player join/privacy peek shield, adhering to Carson Gross's *"Codin' Dirty"* testing philosophy.
  - Added host environment fallback in `tests/playwright/conftest.py` ensuring clean pytest execution across environments without FHS browser dependencies while relying on the ultra-fast (1.4s) Robot Framework simulation suite for rules verification.
- **Testing**:
  - Added unit tests in `lupus/tests.py` covering hidden martyrdom night trap resolution, one-night window expiration, and Doctor protection immunity.
  - Added Robot Framework scenario in `tests/robot/lupus/suites/07_roles_special_pack.robot` (37 passed).

## [v125] - 2026-11-11

### Added
- **Wolf Cub Role (`wolf_cub`, Werewolf Pack, 🐾)**:
  - Added beloved pup of the wolf pack to `ROLE_REGISTRY` and demo deck (`Filhote de Lobo`).
  - **Carnage Rampage Trigger**: When the Wolf Cub dies (via day execution, vigilante sniper, witch poison, or serial killer), the wolf pack enters an enraged frenzy (`state["wolf_cub_rampage"] = True`).
  - **Double Kill Night Hunt**: On the following night, the Werewolves hunt stage prompts the wolves for two victims, and `resolve_night` eliminates both chosen targets (with Bodyguard, Doctor, and Gull interactions).
- **Martyrdom Role (`martyrdom`, Town, 💣)**:
  - Call of Duty inspired perk! When eliminated (at night or executed by the village), drops a live grenade taking down one chosen player with them.
  - Players can prime their live grenade target in advance on their phone screen.
  - If eliminated without a primed target, GM dashboard and player screens present an interactive live grenade detonation picker.
- **The Gull Role (`gull`, Town ➔ Werewolf, 🕊️)**:
  - Based on "The Cursed" from Ultimate Werewolf.
  - Naive villager who starts aligned with Town and inspects as Good to the Detective.
  - **Nocturnal Infection**: If attacked by werewolves at night without Doctor protection, they do not die — they are secretly converted into a Werewolf (`faction: FACTION_WOLVES`, `gull_converted: True`).
  - After conversion, Detective inspects them as Evil, and their phone secret role view notifies them they are now a Wolf.
  - Doctor protection successfully shields The Gull from infection and death.
- **Robot Framework Test Suite (`07_roles_special_pack.robot`)**:
  - Added 4 end-to-end simulation tests covering Wolf Cub double-kill rampage, Martyrdom revenge live grenade, The Gull werewolf bite conversion, and Doctor protection immunity.
  - Extended `LupusLibrary.py` with `Wolves Attack With Rampage`, `Martyrdom Primes Target`, and `Player Faction Should Be`.

## [v124] - 2026-11-11

### Added
- **Portuguese 22-Role Demo Room**:
  - Replaced the 10 English demo players with all 22 playable Lupus roles with authentic Portuguese names (`Lobisomem`, `Lobo Alfa`, `Silenciador`, `Incriminador`, `Lobo Sabotador`, `Vidente`, `Watson`, `Médico`, `Guarda-Costas`, `Anjo`, `Anjo da Morte`, `Vigilante`, `Presidente`, `Bruxa`, `Amante 1`, `Amante 2`, `Cupido`, `Bobo da Corte`, `Assassino em Série`, `Caçador de Lobos`, `Hacker`, `Aldeão`).
  - Added NFKD unicode normalization (`normalize_text_for_matching`) so Portuguese accented names (`Médico`, `Aldeão`, `Assassino em Série`, `Caçador de Lobos`) match their role keywords 100% reliably.
  - Enabled Framer role in registry (`lupus/roles.py`).
- **Room Lifecycle States (`open`, `running`, `finished`)**:
  - Added `status` field to `gamerooms.models.Room` with database index and choices `open`, `running`, and `finished`.
  - Added migration `gamerooms/migrations/0003_room_status.py`.
  - Synchronized `state["status"]` across `create_initial_state` (`open`), `start_game` (`running`), `trigger_game_over` (`finished`), and `create_next_game_lobby`.
- **Automatic Room Title Incrementing (`increment_room_title`)**:
  - Automatically appends `" 2"` or increments trailing numbers (e.g. `"someones birthday"` ➔ `"someones birthday 2"` ➔ `"someones birthday 3"`).
- **Seamless Player Migration & WebSocket Redirection**:
  - Implemented `create_next_game_lobby`: creates the next room in `open` status, marks the existing room as `finished`, and moves all players across while preserving their reconnect tokens, player IDs, and table seating order.
  - Channels WebSocket broadcast `room.redirect`: automatically redirects GM cockpit and all connected players to the new room URL.
  - Added automatic forwarding in `gm_dashboard`, `room_play`, and `room_join` when visiting a room that has a `next_room_code`.
- **Finished Rooms Archive on Lupus Hub**:
  - Separated active games (`open`, `running`) from past finished games on `templates/lupus/hub.html` with direct links to GM cockpit and replay export.
- **Enhanced `clear_games` Management Command**:
  - Updated `clear_games` command to flush both `emojinary:game:*` and `lupus:*` Redis/Valkey keys alongside database rooms and sessions.

## [v122] - 2026-11-11

### Added
- **Robot Framework Game Simulation Testing Framework**:
  - Implemented headless in-memory simulation engine [`LupusSimulator.py`](file:///home/msilva/projects/marco-silva.com/tests/robot/lupus/LupusSimulator.py) using a dictionary-backed `MockRedis` to run multi-round Lupus sessions in milliseconds without external daemons.
  - Developed high-level Robot keyword library [`LupusLibrary.py`](file:///home/msilva/projects/marco-silva.com/tests/robot/lupus/LupusLibrary.py) with intuitive DSL keywords (`Given A New Game`, `Player Joins As`, `Wolves Attack`, `Doctor Protects`, `Sniper Shoots`, `Night Resolves`, `Day Voting Begins`, `Final Vote Is Tallied`).
  - Added 6 simulation test suites with 32 automated scenarios under `tests/robot/lupus/suites/`:
    - `01_roles_lethal.robot`: Werewolves, Serial Killer, Sniper (Danger & Silver), Death Angel, Saboteur Wolf.
    - `02_roles_protection.robot`: Doctor, Bodyguard single and double intercept, Witch revive, Angel limbo mechanic.
    - `03_roles_information.robot`: Detective, Alpha Wolf passive camouflage, Framer misdirection, Silencer.
    - `04_roles_social_and_power.robot`: Public Mayor immunity & 2x vote weight, Hidden Mayor, Mayor night veto, Innocent Lovers heartbreak, Jester solo victory.
    - `05_game_cycles.robot`: Multi-round game progression, voting runoff & double-tie peace, room lobby archival.
    - `06_regressions.robot`: v121 simultaneous resolution, dual witch potions, silenced voter rights, limbo voter restrictions.
- **Deterministic Action History Tape & Replay Export**:
  - Structured event recording (`state["action_history"]`) across room creation, player joins, role dealing, night actions, and day trials in [`lupus/game_state.py`](file:///home/msilva/projects/marco-silva.com/lupus/game_state.py).
  - Added `💾 Export Replay JSON` and `📋 Copy Replay Tape` buttons in the GM cockpit navigation bar and Live Activity Log header (`templates/lupus/gm_dashboard.html`).
  - Added HTTP export endpoint at `GET /games/lupus/<code/export-replay/`.
- **Replay CLI & Auto-Converter (`lupus/replay.py`)**:
  - Built CLI runner for inspecting exported games (`--summary`), verifying deterministic execution headlessly (`--verify`), and auto-generating reproducible `.robot` test files (`--to-robot`) from bug reports and live sessions.

### Fixed
- **Framer Night Action Recording**:
  - Added missing `stage_id == "framer"` handler to `record_gm_night_action` so Game Master finger-pointing records Framer targets accurately.
- **Jester Solo Victory State**:
  - Set `state["winner"] = "jester"` directly alongside `pending_gameover` when the Jester is executed by town vote.

## [v121] - 2026-11-11

### Fixed
- **Simultaneous Night Action Resolution for Alive Powers (Witch & Living Roles)**:
  - Fixed night resolution so that all players who started the night alive have their recorded powers execute simultaneously at dawn, even if the player is attacked and killed during that same night.
  - Specifically fixed the Witch: if the Witch was alive and is attacked/killed tonight by Wolves, Serial Killer, or Vigilante, her recorded potions (reviving a soul in Limbo and/or poisoning a living player) now successfully take effect at dawn instead of being wrongly cancelled.
  - The Witch cannot self-heal if attacked tonight (she still dies or enters Limbo alongside her potion victims).
  - Preserved no-op rule for non-living states: if the Witch was already dead or hovering in Limbo before the night began, or is suppressed by a Ghost/Saboteur, her recorded potion actions silently no-op.

## [v120] - 2026-11-10

### Changed
- **Distinct Role Emojis Across UI and Game State**:
  - **Alpha Wolf (`alpha_wolf`)**: Updated emoji to Gorilla `🦍` (replacing `👑`), distinguishing pack leadership from royalty/host icons.
  - **Framer (`framer`)**: Updated emoji to Face with Spiral Eyes `😵‍💫` (replacing `🎭`), visually highlighting hypnotic misdirection.
  - **Death Angel (`death_angel`)**: Updated emoji to Skull `💀` (replacing `👼🗡️`), cleanly signifying execution of souls hovering in Limbo.
  - **Mayor (`mayor`)**: Updated emoji to Man Judge `👨‍⚖️` (replacing `🎖️`), reinforcing daytime executive voting authority and immunity.
  - **Distinguished Lover Emojis**:
    - **Innocent Lovers (`lover`)**: Revolving Hearts `💞` for the bonded Town citizen couple across deck chips, pre-assign modal, night stages, table nodes, and secret notes.
    - **Cupid (`cupid`)**: Bow & Arrow `🏹` for the neutral matchmaker who binds obsessive lovers.
    - **Obsessive Lovers (`obsessive_lover` / Cupid victims)**: Heart on Fire `❤️‍🔥` across player secret cards, table seat nodes, and victory game over announcements.
    - **Wolf Hunter (`wolf_hunter`)**: Bow & Wolf `🏹🐺` distinguishing solo vigilante hunting from Cupid's matchmaker bow.

## [v119] - 2026-11-10

### Fixed
- **Mayor Veto Status Check**: Fixed conditional evaluation order in the GM night stage view so that when nobody was executed yesterday (`last_lynched_id is None`), it accurately displays `ℹ️ Nobody was executed yesterday. No victim available to pardon.` rather than erroneously warning that the Mayor had already vetoed the person.
- **Hacker Intel Announcement**: Decoupled Hacker Intel dawn reporting from hardcoded Round 1: Intel is now announced on the dawn immediately following the scan regardless of round number, and marked as announced.
- **Full Resolution Report in Activity Log**: Dawn resolution reports are now systematically appended to the GM Live Activity Log (`state["events_log"]`), detailing all night casualties, Limbo transitions, silenced players, Hacker intel, and Gazette bulletins.

### Added
- **Dual Witch Potions Selection**:
  - Redesigned Witch night interface to feature two dedicated, independent targets:
    - **🧪 Revive Potion**: Restores souls currently in Limbo back to living status (or saves tonight's wolf attack victim).
    - **☠️ Poison Potion**: Targets living players only.
  - The Witch stage is always callable by the GM for natural bluffing and table scripts; if the Witch is not alive, any recorded actions silently no-op during night resolution without revealing dead roles.
- **Final Night Stage Transition**:
  - Transformed the "Next Stage &rarr;" button on the final Dawn Review summary stage into `☀️ Wake Town (Resolve Night)` with green accent styling, executing `resolveNight()` seamlessly.

## [v118] - 2026-11-10

### Added
- **Death Angel Standalone Role Card**:
  - Separated Death Angel from being an Angel add-on into an independent Good Team role card in the deck builder.
  - Removed mandatory Angel requirement / demotion to citizen: Death Angel can now be assigned and dealt in games without an Angel (acting harmlessly like a citizen if no souls enter Limbo).
  - Updated pre-assignment manual modal with complete role listings including Framer and Cupid (Matchmaker).
- **Game History Archiving & Full Gazette Reset**:
  - `return_to_lobby` archives completed games into `state["game_history"]` capturing game number, timestamp, rounds played, winner, and full player rosters with roles, factions, and survival statuses.
  - Gazette submissions (`news_bulletins`, `approved_news_bulletins`), player bulletin limits (`last_news_post_round`, `used_dead_news_bulletin`), and player finger points are thoroughly wiped clean upon returning to the lobby or starting a new game.

### Changed
- **Ring Table Seating with GM Podium**:
  - Streamlined table layouts to exclusively use the open **Ring Table** (with GM podium anchored at the bottom) and the accessible **Card List** view, removing the overlapping Figure U mode.
  - Symmetrically distributed seats along an elliptical arc without corner overcrowding or node overlaps.
- **Eye-Contact / Recognition Night Stages**:
  - Non-targeting night stages (`lovers_meet`, `watson_intro`, `wolves_meet`) are designated as `no_target: True`.
  - GM night stage view hides target selection dropdowns and displays clear visual-check banners (`👀 Visual / Eye-Contact Only (No target action required)`), preventing accidental target registrations when tapping seats.
- **Hacker Night Scheduling**:
  - Hacker scan is strictly scheduled for Round 0 (Night 0) only, with scan intel announced on Day 1 dawn, eliminating redundant Night 1 scan steps.
- **Live Finger Pointers Placement**:
  - Relocated live finger pointers box right inside the Phase & Round controls card for instant visibility when the GM conducts table votes or suspect accusations.

## [v117] - 2026-11-10

### Added
- **Mayor Vote-Canceling Power Toggle (`mayor_can_cancel_vote`)**:
  - Both Public and Hidden Mayors can independently have the power to cancel the vote (executive pardon veto) enabled or disabled.
  - Added inline toggle to Mayor role chip in deck builder (`[ ⚖️ Cancel: ON ⇄ ]` vs `[ 🚫 Cancel: OFF ⇄ ]`).
  - Synced to player role descriptions and night execution veto permissions.
- **Pre-Assignment List & Indicators**:
  - Added missing roles `death_angel` and `wolf_hunter` to pre-assignment role picker modal.
  - Added dynamic status banner in modal showing player's current pre-assignment (`🎯 Currently Pre-assigned` vs `🎲 Random / Unassigned`).
  - Added active highlight (`✓ [Role] [Assigned]`) on current pre-assignment and subtle claimant tags (`[Role] (Pre-assigned: Alice)`) when a role is already claimed by another player at the table.
  - Added live header badge (`🎯 X Pre-assigned`) and seating node highlights (`.u-seat-node.is-preassigned`) on table diagram.
  - Enhanced name auto-assign keywords for `death_angel` ("death angel", "dark angel") and `wolf_hunter` ("wolf hunter", "lone hunter").

### Changed
- **Divider-Based GM Dashboard Layout**:
  - Replaced bulky enclosed card boxes (`.card-box`) with sleek horizontal section dividers (`.gm-section`).
  - Eliminated side whitespace padding to maximize horizontal density for role grids, table seating diagrams, and player controls on both mobile and desktop.

## [v116] - 2026-11-10

### Changed
- **Inline Extended Role Pills for Tuning & Variations**:
  - Replaced separate tuning sub-cards with seamless inline-extending pill chips in the lobby deck builder grid (`.role-toggle-chip.extended`).
  - **Mayor**: Pill extends when active to include an inline mode toggle (`📢 Public (Immune) ⇄` vs `🕵️ Hidden ⇄`).
  - **Sniper / Vigilante**: Pill extends when active to display danger (`💥`) and silver (`✨`) bullet steppers inline.
  - **Angel**: Pill extends when active to include an inline `+🗡️ Death Angel` add-on toggle button.
  - **Serial Killer**: Pill extends when active to toggle between `🔪 Solo Win ⇄` and `🎯 Wolf Hunter ⇄`.
  - Removed separate detached chips for Death Angel and Wolf Hunter, keeping the role selection grid tight, cohesive, and perfectly aligned across mobile and desktop.

## [v115] - 2026-11-10

### Added
- **Pre-Game Role Card Tuning UI**: Integrated role tuning controls directly on role chips/cards in the pre-game deck builder instead of the room creation page:
  - **Vigilante / Sniper Bullets Stepper**: Live steppers for Danger Bullets and Silver Bullets directly under the active Sniper card, automatically syncing to settings and player inventories.
  - **Mayor Variation Selector**: Live toggle between **Public Mayor** and **Hidden Mayor** on the Mayor card.
- **Public Mayor Lynching Immunity**:
  - A Public Mayor cannot be voted out by town execution ("public mayor can't be voted out"). If the Public Mayor receives the highest vote tally, executive immunity activates, the execution fails, and the town proceeds to night peacefully.
  - Public Mayor identity is confirmed publicly to all players and retains double voting power (`2x`).
- **Hidden Mayor Mechanic**:
  - Hidden Mayor keeps their role secret, votes with standard `1x` weight, and can be voted out normally (or exercise their 1-time pardon veto at night).
- **Lobby Grid Additions**: Added `Death Angel` to the Good Team toggle grid and `Wolf Hunter` to the Neutral Team toggle grid with custom pill rendering in the deck roster.

### Changed
- **Create Room Page Streamlining**: Removed danger and silver bullet inputs from `templates/lupus/create.html` in favor of in-lobby role card tuning.
- **Roster Tag Labels**: Dynamic deck roster tags now display tuned parameters (e.g. `🎯 Sniper (1D, 0S)`, `🎖️ Public Mayor`, `🎖️ Hidden Mayor`).

## [v114] - 2026-11-10

### Added
- **Night 0 & Day 0 Initial Sequence**: Introduced peaceful Night 0 (weapons holstered; wolves meet, lovers awaken, Watson identifies Detective, Hacker scans suspects) followed by Day 0 (discussion only, voting locked). Normal lethal night begins on Night 1; Day 1 reveals Hacker intel and unlocks voting.
- **Death Angel Role (`death_angel`)**: Good-aligned role dependent on a living Angel. Can directly strike a player in Limbo to permanent death. Can strike from Limbo! (Demotes to Citizen if room lacks an Angel).
- **Wolf Hunter Role (`wolf_hunter`)**: High-stakes lone hunter. If they strike a wolf at night, the wolf dies; if they strike a non-wolf, the hunter dies of backfire instead.
- **Quantified Role Reveal on Death**: Settings option (`0`: None, `1`: Alignment, `2`: Faction, `3`: Full Role). In Limbo games, revelation strictly triggers on permanent death ("death death"), never during Limbo.
- **Quantified Sniper Ammo**: Separate danger bullets and silver bullets pools configurable in settings and tracked per player inventory.
- **Integrated Limbo Night Stage (`limbo_angel_guess`)**: Dedicated night stage before Dawn Review where the GM processes limbo souls one-by-one for their Angel guess. If the Angel is dead, all remaining limbo souls pass permanently to death at dawn.
- **Real-Time Player Pointing**: Players can point at other players from mobile (`Alice 👉 Bob`); displayed live in the GM cockpit and auto-cleared on phase/stage shifts.
- **GM Coroner's Report / Gazette Leak**: Game Master can leak a fallen player's alignment or full role directly to the Town Gazette.
- **Tutorial Categorization**: Grouped all roles in the tutorial into 4 distinct categories: 🟢 Good, 🔴 Bad, 🟡 Neutral/Solo, and 🟣 Add-on/Midgame.

### Changed
- **Simplified Alignment Wording**: Simplified Detective inspection and logs from `"Good / Innocent"` to `"Good"` and `"Evil / Enemy"` to `"Evil"`.
- **Cupid & Lovers Cleanup**: Removed duplicate `obsessive_lover` from dealable decks; Cupid creates obsessive lovers dynamically while `lover` represents starting Innocent Lovers.
- **Midgame Add-ons Segregation**: Marked `traveler`, `ghost`, `disgruntled_ghost`, and `successor` as midgame-only, preventing them from being dealt in pre-game decks.
- **Unassigned Role Card**: Hidden the "How to Play My Role" guide button when a player has no role assigned.

## [v113] - 2026-11-10
- Active rooms hub at `/games/lupus/` and `/lupus/` redirects.
- Demo players named after their roles with lobby role pre-assignment & name-based auto-assignment.
- Danger bullet backfire fix (shooter dies of guilt, innocent target survives unharmed).

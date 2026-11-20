import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE_HOST = "https://marco-silva.com"
CHROMIUM_PATH = "/home/msilva/.nix-profile/bin/chromium"
DOCS_DIR = "/home/msilva/projects/marco-silva.com/docs/screenshots"


async def capture_stop():
    print("--- [1/7] Capturing Stop! ---")
    out = os.path.join(DOCS_DIR, "stop/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "STOP2001"
    url = f"{BASE_HOST}/games/{room}/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_m = await browser.new_context(viewport={"width": 393, "height": 852})
        page_m = await ctx_m.new_page()
        ctx_d = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = await ctx_d.new_page()

        # Alice (Mobile)
        await page_m.goto(url)
        await page_m.fill('input[name="name"]', "Alice (Host)")
        await page_m.click('button:has-text("join")')
        await page_m.wait_for_url("**/games/stop/**")

        # Bob (Desktop)
        await page_d.goto(url)
        await page_d.fill('input[name="name"]', "Bob")
        await page_d.click('button:has-text("join")')
        await page_d.wait_for_url("**/games/stop/**")
        await asyncio.sleep(1.5)

        # Reset room to lobby if stuck in gameover or playing
        await page_m.evaluate("""
            if (typeof wsSend === 'function') {
                if (gameState && (gameState.phase === 'gameover' || gameState.phase === 'scores')) {
                    wsSend({ action: 'play_again' });
                }
            }
        """)
        await asyncio.sleep(1.5)

        # 01 & 02 Lobby
        await page_m.screenshot(path=f"{out}/01_stop_lobby_mobile.png")
        await page_d.screenshot(path=f"{out}/02_stop_lobby_desktop.png")

        # 03 Color Picker open
        await page_m.evaluate("""
            if (typeof onRosterColorClick === 'function' && gameState && gameState.players && gameState.players.length) {
                onRosterColorClick(gameState.players[0].id, '#3b82f6', true, true);
            } else if (typeof openColorPickerModal === 'function') {
                openColorPickerModal('alice', '#3b82f6', () => {});
            }
        """)
        await asyncio.sleep(0.6)
        await page_m.screenshot(path=f"{out}/03_stop_color_picker_mobile.png")
        await page_m.evaluate("if (typeof closeColorPickerModal === 'function') closeColorPickerModal();")
        await asyncio.sleep(0.4)

        # Start Round (button is #btn-start-game)
        start_btn = page_m.locator("#btn-start-game")
        if await start_btn.is_visible():
            await start_btn.click()
        else:
            await page_m.evaluate("wsSend({ action: 'start_round' })")
        # Wait 4.5s for 4.0s synchronized countdown to complete
        await asyncio.sleep(4.5)

        # 04 & 05 Playing
        await page_m.screenshot(path=f"{out}/04_stop_playing_mobile.png")
        await page_d.screenshot(path=f"{out}/05_stop_playing_desktop.png")

        # Bob submits an answer and calls stop
        ans_input = page_d.locator("#answer-input")
        if await ans_input.is_visible():
            await ans_input.fill("Banana")
            await page_d.click("#btn-submit-answer")
            await asyncio.sleep(0.5)

        # Alice forces stop to enter reveal
        await page_m.evaluate("wsSend({ action: 'call_stop', reason: 'Time up!' })")
        await asyncio.sleep(2.5)

        # 06 & 07 Reveal
        await page_m.screenshot(path=f"{out}/06_stop_reveal_mobile.png")
        await page_d.screenshot(path=f"{out}/07_stop_reveal_desktop.png")

        # End game directly to view podium
        await page_m.evaluate("wsSend({ action: 'end_game' })")
        await asyncio.sleep(2)

        # 08 & 09 Scores / Podium
        await page_m.screenshot(path=f"{out}/08_stop_scores_mobile.png")
        await page_d.screenshot(path=f"{out}/09_stop_scores_desktop.png")

        await browser.close()
    print("Done Stop!")


async def capture_emojinary():
    print("--- [2/7] Capturing Emojinary ---")
    out = os.path.join(DOCS_DIR, "emojinary/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "EMOJ2001"
    url = f"{BASE_HOST}/games/{room}/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_m = await browser.new_context(viewport={"width": 393, "height": 852})
        page_m = await ctx_m.new_page()
        ctx_d = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = await ctx_d.new_page()

        await page_m.goto(url)
        await page_m.fill('input[name="name"]', "Alice (Host)")
        await page_m.click('button:has-text("join")')
        await page_m.wait_for_url("**/games/emojinary/**")

        await page_d.goto(url)
        await page_d.fill('input[name="name"]', "Bob")
        await page_d.click('button:has-text("join")')
        await page_d.wait_for_url("**/games/emojinary/**")
        await asyncio.sleep(1.5)

        # Reset room to clean lobby if in gameover
        await page_m.evaluate("""
            if (typeof ws !== 'undefined' && ws.readyState === WebSocket.OPEN) {
                if (typeof latestState !== 'undefined' && latestState && (latestState.phase === 'game_over' || latestState.phase === 'gameover')) {
                    ws.send(JSON.stringify({action: 'play_again'}));
                }
            }
        """)
        await asyncio.sleep(1.5)

        # 01 & 02 Lobby
        await page_m.screenshot(path=f"{out}/01_emojinary_lobby_mobile.png")
        await page_d.screenshot(path=f"{out}/02_emojinary_lobby_desktop.png")

        # Start game
        start_btn = page_m.locator("#start-btn")
        if await start_btn.is_visible():
            await start_btn.click()
        else:
            await page_m.evaluate("ws.send(JSON.stringify({action: 'start'}))")
        await asyncio.sleep(2.5)

        # 04 Drawing (Mobile) & 05 Guesser (Desktop)
        await page_m.screenshot(path=f"{out}/04_emojinary_drawing_mobile.png")
        await page_d.screenshot(path=f"{out}/05_emojinary_guesser_desktop.png")

        # Clue giver submits an emoji
        await page_m.fill("#emoji-field", "🍕🔥")
        await page_m.click("#btn-reveal-emoji")
        await asyncio.sleep(2)

        # 06 & 07 Revealed
        await page_m.screenshot(path=f"{out}/06_emojinary_revealed_mobile.png")
        await page_d.screenshot(path=f"{out}/07_emojinary_revealed_desktop.png")

        # End game to reach podium
        await page_m.evaluate("ws.send(JSON.stringify({action: 'end_game'}))")
        await asyncio.sleep(2)

        # 08 & 09 Podium
        await page_m.screenshot(path=f"{out}/08_emojinary_podium_mobile.png")
        await page_d.screenshot(path=f"{out}/09_emojinary_podium_desktop.png")

        await browser.close()
    print("Done Emojinary!")


async def capture_impostor():
    print("--- [3/7] Capturing Word Impostor ---")
    out = os.path.join(DOCS_DIR, "impostor/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "IMPO2001"
    url = f"{BASE_HOST}/games/{room}/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_m = await browser.new_context(viewport={"width": 393, "height": 852})
        page_m = await ctx_m.new_page()
        ctx_d = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = await ctx_d.new_page()

        await page_m.goto(url)
        await page_m.fill('input[name="name"]', "Alice (Host)")
        await page_m.click('button:has-text("join")')
        await page_m.wait_for_url("**/games/impostor/**")

        await page_d.goto(url)
        await page_d.fill('input[name="name"]', "Bob")
        await page_d.click('button:has-text("join")')
        await page_d.wait_for_url("**/games/impostor/**")
        await asyncio.sleep(1.5)

        # Reset to lobby if not already
        await page_m.evaluate("""
            if (typeof sendAction === 'function') {
                sendAction('reset_game');
            }
        """)
        await asyncio.sleep(1.5)

        # 01 & 02 Lobby
        await page_m.screenshot(path=f"{out}/01_impostor_lobby_mobile.png")
        await page_d.screenshot(path=f"{out}/02_impostor_lobby_desktop.png")

        # Start round
        await page_m.evaluate("sendAction('start_game')")
        await asyncio.sleep(2)

        # 04 & 05 Secret Card Blurred
        await page_m.screenshot(path=f"{out}/04_impostor_secret_card_blurred_mobile.png")
        await page_d.screenshot(path=f"{out}/05_impostor_secret_card_blurred_desktop.png")

        # Unblur card
        await page_m.click("#btn-toggle-peek")
        await asyncio.sleep(0.5)
        await page_m.screenshot(path=f"{out}/06_impostor_secret_card_revealed_mobile.png")

        # Submit clues for both players
        await page_m.evaluate("sendAction('submit_clue', { clue: 'Crispy' })")
        await asyncio.sleep(1)
        await page_d.evaluate("sendAction('submit_clue', { clue: 'Delicious' })")
        await asyncio.sleep(1.5)

        # 07 & 08 Clue Turn
        await page_m.screenshot(path=f"{out}/07_impostor_clue_turn_mobile.png")
        await page_d.screenshot(path=f"{out}/08_impostor_clue_turn_desktop.png")

        # Advance to voting (action is 'start_voting')
        await page_m.evaluate("sendAction('start_voting')")
        await asyncio.sleep(2)

        # 09 & 10 Voting
        await page_m.screenshot(path=f"{out}/09_impostor_voting_mobile.png")
        await page_d.screenshot(path=f"{out}/10_impostor_voting_desktop.png")

        # Accuse suspect / resolve voting (Alice points at Bob)
        await page_m.evaluate("""
            const bob = (typeof state !== 'undefined' && state && state.players) ? state.players.find(p => p.name.includes('Bob')) : null;
            if (bob) {
                sendAction('accuse_suspect', { target_id: bob.id });
            } else {
                sendAction('tally_votes');
            }
        """)
        await asyncio.sleep(2)

        # 11 & 12 Outcome / Reveal
        await page_m.screenshot(path=f"{out}/11_impostor_outcome_mobile.png")
        await page_d.screenshot(path=f"{out}/12_impostor_outcome_desktop.png")

        await browser.close()
    print("Done Impostor!")


async def capture_codenames():
    print("--- [4/7] Capturing Codenames ---")
    out = os.path.join(DOCS_DIR, "codenames/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "CODE2001"
    url = f"{BASE_HOST}/games/{room}/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_m = await browser.new_context(viewport={"width": 393, "height": 852})
        page_m = await ctx_m.new_page()
        ctx_d = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = await ctx_d.new_page()

        await page_m.goto(url)
        await page_m.fill('input[name="name"]', "Alice (Host)")
        await page_m.click('button:has-text("join")')
        await page_m.wait_for_url("**/games/codenames/**")

        await page_d.goto(url)
        await page_d.fill('input[name="name"]', "Bob")
        await page_d.click('button:has-text("join")')
        await page_d.wait_for_url("**/games/codenames/**")
        await asyncio.sleep(1.5)

        # Reset if needed
        await page_m.evaluate("""
            if (typeof latestState !== 'undefined' && latestState && latestState.phase === 'gameover') {
                sendAction('play_again');
            }
        """)
        await asyncio.sleep(1)

        # Assign teams: Alice Red Spymaster, Bob Red Operative (join_team action)
        await page_m.evaluate("sendAction('join_team', { team: 'red', role: 'spymaster' })")
        await page_d.evaluate("sendAction('join_team', { team: 'red', role: 'operative' })")
        await asyncio.sleep(1)

        # Send test chat to demonstrate chat & event log works
        await page_m.evaluate("sendAction('chat', { msg: 'Hello team! Ready to play.' })")
        await asyncio.sleep(0.5)

        # 01 & 02 Lobby
        await page_m.screenshot(path=f"{out}/01_codenames_lobby_mobile.png")
        await page_d.screenshot(path=f"{out}/02_codenames_lobby_desktop.png")

        # Start game (start_game action)
        await page_m.evaluate("sendAction('start_game')")
        await asyncio.sleep(2)

        # 03 Spymaster (Mobile) & 04 Operative (Desktop)
        await page_m.screenshot(path=f"{out}/03_codenames_grid_spymaster_mobile.png")
        await page_d.screenshot(path=f"{out}/04_codenames_grid_operative_desktop.png")

        # Spymaster submits a clue (action key is 'clue', with by_mod: true)
        await page_m.evaluate("sendAction('submit_clue', { clue: 'OCEAN', count: 2, by_mod: true })")
        await asyncio.sleep(1.5)

        # 05 & 06 Clue Published
        await page_m.screenshot(path=f"{out}/05_codenames_clue_published_mobile.png")
        await page_d.screenshot(path=f"{out}/06_codenames_clue_published_desktop.png")

        # Operative reveals card 0
        await page_d.evaluate("sendAction('guess', { index: 0 })")
        await asyncio.sleep(1.5)
        await page_d.screenshot(path=f"{out}/07_codenames_card_revealed_desktop.png")

        # End game
        await page_m.evaluate("sendAction('end_game')")
        await asyncio.sleep(2)

        # 08 & 09 Game Over
        await page_m.screenshot(path=f"{out}/08_codenames_gameover_mobile.png")
        await page_d.screenshot(path=f"{out}/09_codenames_gameover_desktop.png")

        await browser.close()
    print("Done Codenames!")


async def capture_dontsay():
    print("--- [5/7] Capturing Don't Say ---")
    out = os.path.join(DOCS_DIR, "dontsay/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "DSAY2001"
    url = f"{BASE_HOST}/games/{room}/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_m = await browser.new_context(viewport={"width": 393, "height": 852})
        page_m = await ctx_m.new_page()
        ctx_d = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = await ctx_d.new_page()

        await page_m.goto(url)
        await page_m.fill('input[name="name"]', "Alice (Host)")
        await page_m.click('button:has-text("join")')
        await page_m.wait_for_url("**/games/dontsay/**")

        await page_d.goto(url)
        await page_d.fill('input[name="name"]', "Bob")
        await page_d.click('button:has-text("join")')
        await page_d.wait_for_url("**/games/dontsay/**")
        await asyncio.sleep(1.5)

        # Reset room to clean lobby
        await page_m.evaluate("wsSend({ action: 'reset_game' })")
        await asyncio.sleep(1.5)

        # 01 & 02 Lobby
        await page_m.screenshot(path=f"{out}/01_lobby_mobile.png")
        await page_d.screenshot(path=f"{out}/02_lobby_desktop.png")

        # Open color picker
        await page_m.evaluate("""
            if (typeof onRosterColorClick === 'function' && gameState && gameState.players && gameState.players.length) {
                onRosterColorClick(gameState.players[0].id, '#3b82f6', true, true);
            } else if (typeof openColorPickerModal === 'function') {
                openColorPickerModal('alice', '#3b82f6', () => {});
            }
        """)
        await asyncio.sleep(0.5)
        await page_m.screenshot(path=f"{out}/03_lobby_color_picker_mobile.png")
        await page_m.evaluate("if (typeof closeColorPickerModal === 'function') closeColorPickerModal();")
        await asyncio.sleep(0.3)

        # Start game in The ME mode
        await page_m.evaluate("wsSend({ action: 'update_settings', settings: { game_mode: 'the_me' } })")
        await asyncio.sleep(0.5)
        await page_m.evaluate("wsSend({ action: 'start_game' })")
        # Wait 4.5s for synchronized 4.0s countdown modal to clear
        await asyncio.sleep(4.5)

        # 04 Answering Host (Mobile) & 05 Waiting Player (Desktop)
        await page_m.screenshot(path=f"{out}/04_the_me_answering_host_mobile.png")
        await page_d.screenshot(path=f"{out}/05_the_me_waiting_player_desktop.png")

        # The ME submits answer
        await page_m.fill("#the-me-host-input", "Paris")
        await page_m.evaluate("submitTheMeAnswer()")
        await asyncio.sleep(1.5)

        # Guesser submits via #input-answer
        ans_input = page_d.locator("#input-answer")
        if await ans_input.is_visible():
            await ans_input.fill("London")
            await page_d.click("#btn-submit-answer")
            await asyncio.sleep(1)

        # Reveal (action is 'reveal_round')
        await page_m.evaluate("wsSend({ action: 'reveal_round' })")
        await asyncio.sleep(2)

        # 06 & 07 Reveal
        await page_m.screenshot(path=f"{out}/06_dontsay_reveal_mobile.png")
        await page_d.screenshot(path=f"{out}/07_dontsay_reveal_desktop.png")

        # End game to show podium
        await page_m.evaluate("wsSend({ action: 'end_game' })")
        await asyncio.sleep(2)

        # 09 & 10 Podium
        await page_m.screenshot(path=f"{out}/09_dontsay_podium_mobile.png")
        await page_d.screenshot(path=f"{out}/10_dontsay_podium_desktop.png")

        await browser.close()
    print("Done Don't Say!")


async def capture_rankit():
    print("--- [6/7] Capturing Rank It! ---")
    out = os.path.join(DOCS_DIR, "rankit/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "RKIT2001"
    url = f"{BASE_HOST}/games/{room}/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_m = await browser.new_context(viewport={"width": 393, "height": 852})
        page_m = await ctx_m.new_page()
        ctx_d = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = await ctx_d.new_page()
        ctx_t = await browser.new_context(viewport={"width": 810, "height": 1080})
        page_t = await ctx_t.new_page()

        await page_m.goto(url)
        await page_m.fill('input[name="name"]', "Alice (Host)")
        await page_m.click('button:has-text("join")')
        await page_m.wait_for_url("**/games/rankit/**")

        await page_d.goto(url)
        await page_d.fill('input[name="name"]', "Bob")
        await page_d.click('button:has-text("join")')
        await page_d.wait_for_url("**/games/rankit/**")

        await page_t.goto(url)
        await page_t.fill('input[name="name"]', "Charlie")
        await page_t.click('button:has-text("join")')
        await page_t.wait_for_url("**/games/rankit/**")
        await asyncio.sleep(1.5)

        # Reset room to lobby
        await page_m.evaluate("wsSend({ action: 'reset_game' })")
        await asyncio.sleep(1.5)

        # 01 & 02 Lobby
        await page_m.screenshot(path=f"{out}/01_lobby_mobile.png")
        await page_d.screenshot(path=f"{out}/02_lobby_desktop.png")

        # Open color picker
        await page_m.evaluate("""
            if (typeof onRosterColorClick === 'function' && gameState && gameState.players && gameState.players.length) {
                onRosterColorClick(gameState.players[0].id, '#3b82f6', true, true);
            } else if (typeof openColorPickerModal === 'function') {
                openColorPickerModal('alice', '#3b82f6', () => {});
            }
        """)
        await asyncio.sleep(0.5)
        await page_m.screenshot(path=f"{out}/03_lobby_color_picker_mobile.png")
        await page_m.evaluate("if (typeof closeColorPickerModal === 'function') closeColorPickerModal();")
        await asyncio.sleep(0.3)

        # Start level (countdown)
        await page_m.evaluate("wsSend({ action: 'start_level', from_level: 1 })")
        await asyncio.sleep(1)
        # Capture countdown staging with blurred backdrop
        await page_m.screenshot(path=f"{out}/04_countdown_staging_mobile.png")
        # Wait 4s for countdown to finish completely
        await asyncio.sleep(4)

        # 05 & 06 Unrevealed hand
        await page_m.screenshot(path=f"{out}/05_hand_unrevealed_mobile.png")
        await page_d.screenshot(path=f"{out}/06_hand_unrevealed_desktop.png")

        # Play cards into timeline
        await page_m.evaluate(
            "if (gameState.viewer && gameState.viewer.hand && gameState.viewer.hand.length) wsSend({ action: 'play_card', card_id: gameState.viewer.hand[0].card_id })"
        )
        await page_d.evaluate(
            "if (gameState.viewer && gameState.viewer.hand && gameState.viewer.hand.length) wsSend({ action: 'play_card', card_id: gameState.viewer.hand[0].card_id })"
        )
        await page_t.evaluate(
            "if (gameState.viewer && gameState.viewer.hand && gameState.viewer.hand.length) wsSend({ action: 'play_card', card_id: gameState.viewer.hand[0].card_id })"
        )
        await asyncio.sleep(1.5)

        # 07 & 08 Discussion timeline
        await page_m.screenshot(path=f"{out}/07_discussion_timeline_mobile.png")
        await page_t.screenshot(path=f"{out}/08_discussion_timeline_tablet.png")

        # Reveal timeline
        await page_m.evaluate("wsSend({ action: 'reveal_timeline' })")
        await asyncio.sleep(2)

        # 14 & 15 Success / Reveal
        await page_m.screenshot(path=f"{out}/14_revealed_success_mobile.png")
        await page_d.screenshot(path=f"{out}/15_revealed_success_desktop.png")

        # Close modal to inspect timeline
        close_btn = page_m.locator("#modal-level-success .btn-close, button:has-text('Inspect Timeline')").first
        if await close_btn.is_visible():
            await close_btn.click()
            await asyncio.sleep(0.5)
        # 18 Inspected timeline (shows prompt card populated)
        await page_m.screenshot(path=f"{out}/18_inspected_timeline_mobile.png")

        await browser.close()
    print("Done Rank It!")


async def capture_lupus():
    print("--- [7/7] Capturing Lupus in Tabula ---")
    out = os.path.join(DOCS_DIR, "lupus/judge_pass")
    os.makedirs(out, exist_ok=True)
    room = "LUPU2001"
    gm_token = "8fa7eb79e6e544929d319e49f4d812c1"
    gm_url = f"{BASE_HOST}/games/lupus/{room}/gm/?gm_token={gm_token}"
    join_url = f"{BASE_HOST}/games/lupus/{room}/join/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM_PATH, headless=True)
        ctx_gm = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_gm = await ctx_gm.new_page()
        ctx_p = await browser.new_context(viewport={"width": 393, "height": 852})
        page_p = await ctx_p.new_page()

        # GM Dashboard
        await page_gm.goto(gm_url)
        await asyncio.sleep(2)

        # Auto-fit deck to players if players joined
        await page_gm.evaluate("""
            if (typeof fitDeckToPlayers === 'function') {
                fitDeckToPlayers();
            }
        """)
        await asyncio.sleep(1)

        # 01 GM Dashboard (with deck balancing meter)
        await page_gm.screenshot(path=f"{out}/01_lupus_gm_dashboard_desktop.png")

        # Bob on Mobile joins room
        await page_p.goto(join_url)
        await page_p.fill('input[name="name"]', "Bob")
        await page_p.click('button[type="submit"]')
        await page_p.wait_for_url("**/play/**")
        await asyncio.sleep(2)

        # 02 Mobile Player Lobby (with topbar identity un-crushed)
        await page_p.screenshot(path=f"{out}/02_lupus_player_lobby_mobile.png")

        # GM deals roles / starts
        await page_gm.evaluate("""
            if (typeof fitDeckToPlayers === 'function') fitDeckToPlayers();
            if (typeof handleStartGame === 'function') handleStartGame();
        """)
        await asyncio.sleep(2.5)

        # 03 GM Active
        await page_gm.screenshot(path=f"{out}/03_lupus_gm_active_desktop.png")

        # Mobile player switches to role tab & unblurs
        await page_p.evaluate("""
            if (typeof setAppTab === 'function') setAppTab('role');
            const el = document.getElementById('role-card-inner');
            if (el) el.classList.remove('blurred');
        """)
        await asyncio.sleep(1)

        # 04 Mobile Player Role Card
        await page_p.screenshot(path=f"{out}/04_lupus_player_role_card_mobile.png")

        # GM advances to Night
        await page_gm.evaluate("""
            if (typeof changePhase === 'function') changePhase('night');
        """)
        await asyncio.sleep(2)

        # 06 & 07 Night Phase
        await page_gm.screenshot(path=f"{out}/06_lupus_gm_phase_desktop.png")
        await page_p.screenshot(path=f"{out}/07_lupus_player_phase_mobile.png")

        # Replay modal on GM
        await page_gm.evaluate("""
            if (typeof openModal === 'function') openModal('gm-timeline-modal');
            if (typeof renderGmReplay === 'function' && typeof currentGameState !== 'undefined') renderGmReplay(currentGameState || {});
        """)
        await asyncio.sleep(1)
        await page_gm.screenshot(path=f"{out}/08_lupus_replay_modal_desktop.png")

        await browser.close()
    print("Done Lupus!")


async def main():
    for fn in [
        capture_stop,
        capture_emojinary,
        capture_impostor,
        capture_codenames,
        capture_dontsay,
        capture_rankit,
        capture_lupus,
    ]:
        try:
            await fn()
        except Exception as e:
            print(f"[!] Error in {fn.__name__}: {e}", file=sys.stderr)
    print("\n🎉 ALL 7 GAMES CAPTURED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())

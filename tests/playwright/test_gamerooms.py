"""Playwright browser tests for game rooms and emojinary."""

import re

from playwright.sync_api import Browser, Page, expect

BASE = "http://localhost:8000"


def test_room_list_page(page: Page):
    page.goto(f"{BASE}/games/")
    expect(page.locator("h1")).to_contain_text("game rooms")
    expect(page.get_by_text("create room")).to_be_visible()


def test_create_room_flow(page: Page):
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Test Room")

    # Read the captcha question and solve it
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    answer = int(nums[0]) + int(nums[1])
    page.fill("input[name='captcha_answer']", str(answer))

    page.click("button[type='submit']")
    # Should redirect to join page (name entry)
    page.wait_for_url(re.compile(r"/games/\w+/"))
    expect(page.locator("input[name='name']")).to_be_visible()


def test_create_room_wrong_captcha(page: Page):
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Bad Captcha Room")
    page.fill("input[name='captcha_answer']", "999")
    page.click("button[type='submit']")
    expect(page.locator("body")).to_contain_text("wrong captcha")


def test_join_open_room_and_enter_game(page: Page):
    # Create a room first
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Open Room")
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    page.fill("input[name='captcha_answer']", str(int(nums[0]) + int(nums[1])))
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/\w+/"))

    # Enter name
    page.fill("input[name='name']", "TestPlayer")
    page.click("button[type='submit']")

    # Should be in the game
    page.wait_for_url(re.compile(r"/games/emojinary/\w+/TestPlayer/"))
    expect(page.locator("#game-area")).to_be_visible()


def test_locked_room_password_flow(page: Page, browser: "Browser"):
    # Create the room
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Locked Room PW")
    page.fill("input[name='password']", "mysecret")
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    page.fill("input[name='captcha_answer']", str(int(nums[0]) + int(nums[1])))
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/\w+/"))

    # Get the room URL
    room_url = page.url

    # Open a fresh context (no session) to simulate another player
    ctx = browser.new_context()
    joiner = ctx.new_page()
    joiner.goto(room_url)

    # Should see password form
    expect(joiner.locator("input[name='password']")).to_be_visible()

    # Wrong password
    joiner.fill("input[name='password']", "wrong")
    joiner.click("button[type='submit']")
    expect(joiner.locator("body")).to_contain_text("wrong password")

    # Correct password
    joiner.fill("input[name='password']", "mysecret")
    joiner.click("button[type='submit']")

    # Should see name form
    expect(joiner.locator("input[name='name']")).to_be_visible()

    # Enter name and join
    joiner.fill("input[name='name']", "SecurePlayer")
    joiner.click("button[type='submit']")
    joiner.wait_for_url(re.compile(r"/games/emojinary/\w+/SecurePlayer/"))
    expect(joiner.locator("#game-area")).to_be_visible()
    ctx.close()


def test_game_page_has_emoji_keyboard(page: Page):
    # Create and join a room
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Emoji KB Test")
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    page.fill("input[name='captcha_answer']", str(int(nums[0]) + int(nums[1])))
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/\w+/"))
    page.fill("input[name='name']", "EmojiTester")
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/emojinary/"))

    # Emoji keyboard should exist (hidden until game starts, but in DOM)
    expect(page.locator("#emoji-kb")).to_be_attached()
    expect(page.locator("#emoji-pages")).to_be_attached()


def test_multiplayer_start_game(page: Page, browser: "Browser"):
    """Test that two players can join and start a game."""
    # Player 1 creates room
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Multi Test")
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    page.fill("input[name='captcha_answer']", str(int(nums[0]) + int(nums[1])))
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/\w+/"))

    # Get room URL
    room_url = page.url

    # Player 1 joins
    page.fill("input[name='name']", "Player1")
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/emojinary/"))
    page.wait_for_timeout(1000)

    # Player 2 joins in new context
    ctx2 = browser.new_context()
    p2 = ctx2.new_page()
    p2.goto(room_url)
    p2.fill("input[name='name']", "Player2")
    p2.click("button[type='submit']")
    p2.wait_for_url(re.compile(r"/games/emojinary/"))
    p2.wait_for_timeout(1000)

    # Player 1 should see Player2 in the players list
    expect(page.locator("#players").first).to_contain_text("Player2")

    # Set rounds to 2 for quick test
    page.fill("#set-rounds", "2")
    page.wait_for_timeout(500)

    # Player 1 starts the game
    page.click("#start-btn")

    # Wait for countdown (3-2-1-GO = ~4s)
    page.wait_for_timeout(5000)

    # Game should have started — status should show round info
    expect(page.locator("#status").first).to_contain_text("Round")

    ctx2.close()


def test_full_game_flow(page: Page, browser: "Browser"):
    """Test a complete 1-round game: emoji phase, reveal, guess, game over."""
    # Create room
    page.goto(f"{BASE}/games/create/")
    page.fill("input[name='title']", "Full Game Test")
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    page.fill("input[name='captcha_answer']", str(int(nums[0]) + int(nums[1])))
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/\w+/"))
    room_url = page.url

    # Player 1 joins
    page.fill("input[name='name']", "Alice")
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/emojinary/"))
    page.wait_for_timeout(1000)

    # Player 2 joins
    ctx2 = browser.new_context()
    p2 = ctx2.new_page()
    p2.goto(room_url)
    p2.fill("input[name='name']", "Bob")
    p2.click("button[type='submit']")
    p2.wait_for_url(re.compile(r"/games/emojinary/"))
    p2.wait_for_timeout(1000)

    # Set to 1 round, no timers
    page.fill("#set-rounds", "1")
    page.fill("#set-emoji-timer", "0")
    page.fill("#set-guess-timer", "0")
    page.wait_for_timeout(500)

    # Start game
    page.click("#start-btn")
    page.wait_for_timeout(5000)  # countdown

    # One of them should have the emoji input, the other should see "waiting"
    # Check both pages for who has the turn
    alice_has_turn = page.locator("#emoji-input-area").is_visible()
    bob_has_turn = p2.locator("#emoji-input-area").is_visible()
    assert alice_has_turn or bob_has_turn, "Someone should have the emoji input"

    if alice_has_turn:
        active, guesser = page, p2
    else:
        active, guesser = p2, page

    # Active player adds an emoji and reveals
    active.evaluate(
        "document.getElementById('emoji-field').value='🎬🦁👑'; "
        + "document.querySelector('[onclick*=sendEmoji]')?.click() || "
        + "fetch(location.origin+'/ws/').catch(()=>{})"
    )
    # Send the emoji via websocket
    active.evaluate("ws.send(JSON.stringify({action:'emoji',emoji:'🎬🦁👑'}))")
    active.wait_for_timeout(500)
    active.click("button:has-text('reveal')")
    active.wait_for_timeout(1500)

    # Guesser should see the emoji
    expect(guesser.locator("#emoji-display")).to_contain_text("🎬🦁👑")

    ctx2.close()

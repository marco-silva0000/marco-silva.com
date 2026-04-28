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
    expect(page.locator("#start-btn")).to_be_visible()


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
    expect(joiner.locator("#start-btn")).to_be_visible()
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

"""Playwright dirty browser smoke tests for Lupus in Tabula.

Follows Carson Gross's 'Codin' Dirty' philosophy:
A few lean end-to-end smoke tests verifying real browser rendering,
form submission, and dynamic DOM interaction without brittle test suites.
"""

import os
import re

from playwright.sync_api import Browser, Page, expect

BASE = os.environ.get("PLAYWRIGHT_BASE_URL", "https://marco-silva.com")


def test_lupus_hub_renders(page: Page):
    """Verify Lupus hub page renders title, room creator and quick join."""
    page.goto(f"{BASE}/games/lupus/")
    expect(page.locator("body")).to_contain_text("Lupus in Tabula")
    expect(page.locator("a[href*='/create/']").first).to_be_visible()


def test_lupus_room_creation_and_cockpit_elements(page: Page):
    """Verify GM room creation navigates to Cockpit and displays role builder chips."""
    page.goto(f"{BASE}/games/lupus/create/")
    page.fill("input[name='title']", "Smoke Room")

    # Solve arithmetic captcha
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    answer = int(nums[0]) + int(nums[1])
    page.fill("input[name='captcha_answer']", str(answer))

    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/lupus/\w+/gm/"))

    # Verify GM dashboard cockpit rendered
    expect(page.locator("#chip-detective")).to_be_visible()
    expect(page.locator("#chip-doctor")).to_be_visible()


def test_lupus_player_join_flow(page: Page, browser: Browser):
    """Verify a player can join an active room and view their role card."""
    # 1. Create a room as GM
    page.goto(f"{BASE}/games/lupus/create/")
    page.fill("input[name='title']", "Player Smoke Test")
    label_text = page.locator("label", has_text="+").text_content()
    nums = re.findall(r"\d+", label_text)
    page.fill("input[name='captcha_answer']", str(int(nums[0]) + int(nums[1])))
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/games/lupus/(\w+)/gm/"))
    m = re.search(r"/games/lupus/(\w+)/gm/", page.url)
    assert m is not None
    room_code = m.group(1)

    # 2. Join as player in a fresh context
    ctx = browser.new_context()
    player_page = ctx.new_page()
    player_page.goto(f"{BASE}/games/lupus/{room_code}/")

    # Fill name
    player_page.fill("input[name='name']", "DirtyTester")
    player_page.click("button[type='submit']")
    player_page.wait_for_url(re.compile(rf"/games/lupus/{room_code}/player/"))

    # Verify player view
    expect(player_page.locator("body")).to_contain_text("DirtyTester")
    expect(player_page.locator("#btn-peek-role")).to_be_visible()
    ctx.close()

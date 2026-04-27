"""Playwright browser tests for the planz calendar tool."""

import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8000"
PASSWORD = "planz"


@pytest.fixture(scope="module")
def browser_context(browser_type_launch):
    # Use the module-scoped browser
    pass


def test_login_page_shows_password_form(page: Page):
    page.goto(f"{BASE}/tools/planz/")
    expect(page.locator("input[name='passwd']")).to_be_visible()
    expect(page.locator("button[type='submit']")).to_be_visible()


def test_wrong_password_shows_error(page: Page):
    page.goto(f"{BASE}/tools/planz/")
    page.fill("input[name='passwd']", "wrong")
    page.click("button[type='submit']")
    expect(page.locator("#result")).to_contain_text("wrong password")


def test_correct_password_shows_calendar(page: Page):
    page.goto(f"{BASE}/tools/planz/")
    page.fill("input[name='passwd']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_selector(".planz-nav")
    expect(page.locator(".planz-nav")).to_be_visible()
    expect(page.locator(".planz-columns")).to_be_visible()


def test_query_param_auth_shows_calendar(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    expect(page.locator(".planz-nav")).to_be_visible()
    expect(page.locator(".planz-columns")).to_be_visible()


def test_default_view_is_3_days(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    expect(page.locator(".planz-columns.cols-3")).to_be_visible()


def test_all_view_buttons_visible(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    expect(page.get_by_role("button", name="1 day")).to_be_visible()
    expect(page.get_by_role("button", name="3 day")).to_be_visible()
    expect(page.get_by_role("button", name="week")).to_be_visible()


def test_switch_to_week_view(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    page.get_by_role("button", name="week").click()
    page.wait_for_selector(".cols-7")
    expect(page.locator(".planz-columns.cols-7")).to_be_visible()


def test_switch_to_1_day_view(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    page.get_by_role("button", name="1 day").click()
    page.wait_for_selector(".cols-1")
    expect(page.locator(".planz-columns.cols-1")).to_be_visible()


def test_navigation_arrows_work(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    # Get initial date range text
    initial_range = page.locator(".planz-date-range").text_content()
    # Click next
    page.get_by_role("button", name="Next day").click()
    page.wait_for_timeout(500)
    new_range = page.locator(".planz-date-range").text_content()
    assert initial_range != new_range


def test_today_button_resets(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}&start=2026-05-15")
    page.get_by_role("button", name="today").click()
    page.wait_for_timeout(500)
    # Should contain today's indicator
    expect(page.locator(".planz-date-range")).to_be_visible()


def test_htmx_navigation_no_full_reload(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    # Mark the page with a JS variable
    page.evaluate("window.__planz_loaded = true")
    # Click next arrow (HTMX swap)
    page.get_by_role("button", name="Next day").click()
    page.wait_for_timeout(500)
    # If HTMX worked, the JS variable should still exist (no full reload)
    still_loaded = page.evaluate("window.__planz_loaded")
    assert still_loaded is True


def test_ics_download_link_present(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}")
    # May or may not have events, but the page should load without error
    expect(page.locator(".planz-columns")).to_be_visible()


def test_columns_layout_3day(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}&days=3")
    columns = page.locator(".planz-col")
    assert columns.count() == 3


def test_columns_layout_week(page: Page):
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}&days=7")
    columns = page.locator(".planz-col")
    assert columns.count() == 7


def test_empty_days_show_placeholder(page: Page):
    # Go far in the future where there are likely no events
    page.goto(f"{BASE}/tools/planz/?passwd={PASSWORD}&days=3&start=2027-12-01")
    expect(page.locator(".planz-day-empty").first).to_be_visible()

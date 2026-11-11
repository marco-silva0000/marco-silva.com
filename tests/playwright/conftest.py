import pytest


def can_launch_playwright():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
            return True
    except Exception:
        return False


HAS_PLAYWRIGHT_BROWSER = can_launch_playwright()


def pytest_runtest_setup(item):
    if "playwright" in str(item.fspath) and not HAS_PLAYWRIGHT_BROWSER:
        pytest.skip(
            "Playwright browser cannot launch on host (e.g. NixOS missing FHS shared libraries). "
            "Use Robot Framework simulation suite for rules & state machine testing."
        )

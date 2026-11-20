#!/usr/bin/env python3
"""Screenshot generation tool for Marco Silva party games suite across diverse devices.

Supported Viewports:
- Latest iPhone (16 / 15 Pro, 393x852 @3x)
- iPhone Max (16 / 15 Pro Max, 430x932 @3x)
- iPhone XR (414x896 @2x)
- Latest Pixel (Pixel 9 / 8, 412x915 @2.625x)
- Pixel Max (Pixel 9 Pro XL / 8 Pro, 448x998 @2.8x)
- iPad (Air / 11-inch, 820x1180 @2x)
- Basic Laptop Fullscreen (1366x768 @1x)
- Laptop Split Screen (720x900 @1x)
- Big External HD Screen (1920x1080 @1x)

Usage:
    python scripts/generate_game_screenshots.py --help
    python scripts/generate_game_screenshots.py --games portal,stop --devices iphone_latest,laptop_fullscreen
    python scripts/generate_game_screenshots.py --all
"""

import argparse
import glob
import os
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DEVICE_CONFIGS = {
    "iphone_latest": {
        "name": "Latest iPhone (16/15 Pro)",
        "slug": "iphone_latest",
        "viewport": {"width": 393, "height": 852},
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    },
    "iphone_max": {
        "name": "iPhone Max (16/15 Pro Max)",
        "slug": "iphone_max",
        "viewport": {"width": 430, "height": 932},
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    },
    "iphone_xr": {
        "name": "iPhone XR",
        "slug": "iphone_xr",
        "viewport": {"width": 414, "height": 896},
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    },
    "pixel_latest": {
        "name": "Latest Pixel (Pixel 9/8)",
        "slug": "pixel_latest",
        "viewport": {"width": 412, "height": 915},
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    },
    "pixel_max": {
        "name": "Pixel Max (Pixel 9 Pro XL / 8 Pro)",
        "slug": "pixel_max",
        "viewport": {"width": 448, "height": 998},
        "device_scale_factor": 2.8,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    },
    "ipad": {
        "name": "iPad (Air / 11-inch)",
        "slug": "ipad",
        "viewport": {"width": 820, "height": 1180},
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    },
    "laptop_fullscreen": {
        "name": "Basic Laptop Fullscreen (1366x768)",
        "slug": "laptop_fullscreen",
        "viewport": {"width": 1366, "height": 768},
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    },
    "laptop_splitscreen": {
        "name": "Laptop Split Screen (720x900)",
        "slug": "laptop_splitscreen",
        "viewport": {"width": 720, "height": 900},
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    },
    "external_hd": {
        "name": "Big External HD Screen (1920x1080)",
        "slug": "external_hd",
        "viewport": {"width": 1920, "height": 1080},
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    },
}


def find_chromium_path():
    """Resolve chromium binary from system PATH or Nix store."""
    which_path = shutil.which("chromium") or shutil.which("google-chrome")
    if which_path:
        return which_path

    nix_matches = glob.glob("/nix/store/*-chromium-[0-9]*/bin/chromium")
    if nix_matches:
        return nix_matches[0]

    return None


def solve_captcha(page):
    """Solve math captcha on game creation forms."""
    try:
        exp_input = page.locator('input[name="captcha_expected"]')
        if exp_input.count() > 0:
            val = exp_input.first.input_value()
            page.fill('input[name="captcha_answer"]', val)
            return True
    except Exception:
        pass
    return False


def setup_browser_context(browser, dev_key):
    """Create a Playwright browser context configured for a specific device."""
    dev = DEVICE_CONFIGS[dev_key]
    return browser.new_context(
        viewport=dev["viewport"],
        device_scale_factor=dev["device_scale_factor"],
        is_mobile=dev["is_mobile"],
        has_touch=dev["has_touch"],
        user_agent=dev["user_agent"],
    )


def capture_portal(browser, base_url, out_dir, devices):
    """Capture the Games Portal hub across all requested viewports."""
    portal_dir = out_dir / "portal"
    portal_dir.mkdir(parents=True, exist_ok=True)
    dev_dir = out_dir / "devices"
    dev_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Capturing Games Portal ({len(devices)} devices)...")
    for d_key in devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        page.on("console", lambda msg: print(f"    [console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [pageerror] {err}"))
        try:
            page.goto(f"{base_url}/games/", wait_until="networkidle")
            time.sleep(0.5)

            # Save to portal dir and devices comparison dir
            path1 = portal_dir / f"portal_{d_key}.png"
            path2 = dev_dir / f"portal_{d_key}.png"
            page.screenshot(path=str(path1), full_page=False)
            shutil.copyfile(path1, path2)
            print(f"    -> Saved {path1.name}")
        except Exception as e:
            print(f"    [!] Error capturing portal on {d_key}: {e}")
        finally:
            ctx.close()


def capture_stop(browser, base_url, out_dir, devices):
    """Capture Stop! party game screens (Creation, Lobby, Playing with unified card)."""
    stop_dir = out_dir / "stop"
    stop_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Capturing Stop! Party Game ({len(devices)} devices)...")

    for d_key in devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        page.on("console", lambda msg: print(f"    [console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [pageerror] {err}"))
        try:
            # 1. Creation Form
            page.goto(f"{base_url}/games/create/?game=stop", wait_until="networkidle")
            time.sleep(0.4)
            c_path = stop_dir / f"stop_create_{d_key}.png"
            page.screenshot(path=str(c_path))
            print(f"    -> Saved {c_path.name}")

            # 2. Create room and land on Lobby
            page.fill('input[name="title"]', f"Stop! Tutorial ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Host")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/stop/**")
            page.wait_for_selector("#players-list", state="attached")
            time.sleep(1.0)

            lobby_path = stop_dir / f"stop_lobby_{d_key}.png"
            page.screenshot(path=str(lobby_path))
            print(f"    -> Saved {lobby_path.name}")

            # 3. Start Match -> Playing stage with unified question card
            started = False
            for _ in range(3):
                try:
                    page.click("#btn-start-game")
                    page.wait_for_selector("#answer-input", state="visible", timeout=4000)
                    started = True
                    break
                except Exception:
                    time.sleep(1)

            if started:
                time.sleep(1.0)
                cur_letter = page.locator("#hero-letter").text_content() or "A"
                page.fill("#answer-input", f"{cur_letter}pple")
                time.sleep(0.3)

                play_path = stop_dir / f"stop_playing_{d_key}.png"
                page.screenshot(path=str(play_path))
                print(f"    -> Saved {play_path.name}")
        except Exception as e:
            print(f"    [!] Error capturing stop on {d_key}: {e}")
        finally:
            ctx.close()


def capture_dontsay(browser, base_url, out_dir, devices):
    """Capture Don't Say the Same Thing as Me game screens."""
    ds_dir = out_dir / "dontsay"
    ds_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Capturing Don't Say the Same Thing as Me ({len(devices)} devices)...")

    for d_key in devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        page.on("console", lambda msg: print(f"    [console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [pageerror] {err}"))
        try:
            # 1. Create room form
            page.goto(f"{base_url}/games/create/?game=dontsay", wait_until="networkidle")
            time.sleep(0.4)
            c_path = ds_dir / f"dontsay_create_{d_key}.png"
            page.screenshot(path=str(c_path))
            print(f"    -> Saved {c_path.name}")

            page.fill('input[name="title"]', f"Don't Say! Demo ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Host")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/dontsay/**")
            page.wait_for_selector("#players-roster", state="attached")
            time.sleep(1.0)

            lobby_path = ds_dir / f"dontsay_lobby_{d_key}.png"
            page.screenshot(path=str(lobby_path))
            print(f"    -> Saved {lobby_path.name}")

            # Start game round
            try:
                start_btn = page.locator("#btn-start-game")
                start_btn.scroll_into_view_if_needed()
                start_btn.click()
                page.wait_for_selector("#stage-answering", state="visible", timeout=6000)
                time.sleep(1.0)
            except Exception as ex:
                print(f"    [!] Error clicking start game: {ex}")

            play_path = ds_dir / f"dontsay_playing_{d_key}.png"
            page.screenshot(path=str(play_path))
            print(f"    -> Saved {play_path.name}")

        except Exception as e:
            print(f"    [!] Error capturing dontsay on {d_key}: {e}")
        finally:
            ctx.close()


def capture_rankit(browser, base_url, out_dir, devices):
    """Capture Rank It! (ito) game screens (Creation, Lobby with Color Picker, Playing with Spectrum and Timeline)."""
    rk_dir = out_dir / "rankit"
    rk_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Capturing Rank It! (ito) ({len(devices)} devices)...")

    for d_key in devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        page.on("console", lambda msg: print(f"    [console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [pageerror] {err}"))
        try:
            # 1. Create Room Form
            page.goto(f"{base_url}/games/create/?game=rankit", wait_until="networkidle")
            time.sleep(0.4)
            c_path = rk_dir / f"rankit_create_{d_key}.png"
            page.screenshot(path=str(c_path))
            print(f"    -> Saved {c_path.name}")

            # 2. Fill room name & enter Lobby
            page.fill('input[name="title"]', f"Rank It! Demo ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Host")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/rankit/**")
            page.wait_for_selector("#roster-list", state="attached")
            try:
                page.wait_for_selector(".player-color-trigger", state="visible", timeout=6000)
            except Exception as e_wait:
                print(f"    [!] Timeout waiting for .player-color-trigger: {e_wait}")
            time.sleep(0.5)

            lobby_path = rk_dir / f"rankit_lobby_{d_key}.png"
            page.screenshot(path=str(lobby_path))
            print(f"    -> Saved {lobby_path.name}")

            # 3. Open Color Picker
            try:
                page.wait_for_selector(".player-color-trigger", timeout=3000)
                page.click(".player-color-trigger")
                page.wait_for_selector("#modal-player-color-picker", state="visible", timeout=2000)
                time.sleep(0.4)
                color_path = rk_dir / f"rankit_color_picker_{d_key}.png"
                page.screenshot(path=str(color_path))
                print(f"    -> Saved {color_path.name}")
                # Pick a color and close
                page.click(".player-swatch-btn:nth-child(4)")
                time.sleep(0.3)
            except Exception as e_color:
                print(f"    [!] Note on color picker capture: {e_color}")

            # 4. Start Level 1 -> Playing with Spectrum & Timeline
            try:
                start_btn = page.locator("#btn-start-level")
                start_btn.scroll_into_view_if_needed()
                start_btn.click()
                # Wait past the 4-second synchronized countdown
                time.sleep(5.0)

                page.wait_for_selector("#section-prompt-card", state="visible", timeout=6000)

                # Type a clue in hand card if available
                clue_input = page.locator(".rk-hand-clue-input").first
                if clue_input.count() > 0:
                    clue_input.fill("A grumpy badger with armor")
                    time.sleep(0.3)

                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(0.4)

                play_path = rk_dir / f"rankit_playing_{d_key}.png"
                page.screenshot(path=str(play_path))
                print(f"    -> Saved {play_path.name}")
            except Exception as e_play:
                print(f"    [!] Note on start level capture: {e_play}")

        except Exception as e:
            print(f"    [!] Error capturing rankit on {d_key}: {e}")
        finally:
            ctx.close()


def capture_smartn(browser, base_url, out_dir, devices):
    """Capture SmartN (Smart 10 Trivia) screens (Creation, Lobby, Playing with Smartbox & Capsules, Single Device Mode)."""
    sn_dir = out_dir / "smartn"
    sn_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Capturing SmartN ({len(devices)} devices)...")

    for d_key in devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        page.on("console", lambda msg: print(f"    [console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [pageerror] {err}"))
        try:
            # 1. Create Room Form
            page.goto(f"{base_url}/games/create/?game=smartn", wait_until="networkidle")
            time.sleep(0.4)
            c_path = sn_dir / f"smartn_create_{d_key}.png"
            page.screenshot(path=str(c_path))
            print(f"    -> Saved {c_path.name}")

            # 2. Enter Lobby
            page.fill('input[name="title"]', f"SmartN Trivia ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Host")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/smartn/**")
            page.wait_for_selector("#roster-grid-lobby", state="attached")
            try:
                page.wait_for_function("() => window.ws && window.ws.readyState === 1", timeout=8000)
            except Exception:
                pass
            time.sleep(0.5)

            lobby_path = sn_dir / f"smartn_lobby_{d_key}.png"
            page.screenshot(path=str(lobby_path))
            print(f"    -> Saved {lobby_path.name}")

            # 3. Start Match -> The Smartbox with 10 Capsules
            try:
                page.click('button:has-text("Start SmartN Match")')
                page.wait_for_selector("#view-playing", state="visible", timeout=8000)
                time.sleep(0.5)

                play_path = sn_dir / f"smartn_playing_{d_key}.png"
                page.screenshot(path=str(play_path))
                print(f"    -> Saved {play_path.name}")

                # 4. Open a capsule
                unrev = page.locator(".capsule-item.unrevealed").first
                if unrev.count() > 0:
                    unrev.click()
                    time.sleep(0.5)
                    opened_path = sn_dir / f"smartn_capsule_opened_{d_key}.png"
                    page.screenshot(path=str(opened_path))
                    print(f"    -> Saved {opened_path.name}")

                # 5. Switch to Single Device Pass & Play mode
                page.click("#lbl-toggle-mode")
                time.sleep(0.5)
                single_path = sn_dir / f"smartn_single_device_{d_key}.png"
                page.screenshot(path=str(single_path))
                print(f"    -> Saved {single_path.name}")

            except Exception as e_play:
                print(f"    [!] Note on SmartN playing capture: {e_play}")

        except Exception as e:
            print(f"    [!] Error capturing SmartN on {d_key}: {e}")
        finally:
            ctx.close()


def capture_lupus(browser, base_url, out_dir, devices):
    """Capture Lupus / Werewolf Hub, Creation, and Cockpit with populated demo table."""
    lupus_dir = out_dir / "lupus"
    lupus_dir.mkdir(parents=True, exist_ok=True)
    print("[*] Capturing Lupus in Tabula / Werewolf...")

    rep_devices = [d for d in ["iphone_latest", "ipad", "laptop_fullscreen", "external_hd"] if d in devices] or [
        devices[0]
    ]

    for d_key in rep_devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        try:
            # 1. Lupus Hub
            page.goto(f"{base_url}/games/lupus/", wait_until="networkidle")
            time.sleep(0.5)
            hub_path = lupus_dir / f"lupus_hub_{d_key}.png"
            page.screenshot(path=str(hub_path))
            print(f"    -> Saved {hub_path.name}")

            # 2. Lupus Create Form
            page.goto(f"{base_url}/games/lupus/create/", wait_until="networkidle")
            time.sleep(0.4)
            create_path = lupus_dir / f"lupus_create_{d_key}.png"
            page.screenshot(path=str(create_path))
            print(f"    -> Saved {create_path.name}")

            # 3. Create Lupus Room with demo trigger (password 'test' & narrator 'Marco')
            page.fill('input[name="title"]', f"Village of Tabula ({d_key})")
            page.fill('input[name="password"]', "test")
            page.fill('input[name="gm_name"]', "Marco (Narrator)")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/lupus/**/gm/**")
            time.sleep(2.0)

            cockpit_path = lupus_dir / f"lupus_gm_cockpit_{d_key}.png"
            page.screenshot(path=str(cockpit_path))
            print(f"    -> Saved {cockpit_path.name}")

        except Exception as e:
            print(f"    [!] Error capturing lupus on {d_key}: {e}")
        finally:
            ctx.close()


def capture_codenames(browser, base_url, out_dir, devices):
    """Capture Codenames 5x5 board and team roster."""
    cn_dir = out_dir / "codenames"
    cn_dir.mkdir(parents=True, exist_ok=True)
    print("[*] Capturing Codenames...")

    rep_devices = [d for d in ["iphone_latest", "ipad", "laptop_fullscreen"] if d in devices] or [devices[0]]

    for d_key in rep_devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        p2_ctx = None
        try:
            page.goto(f"{base_url}/games/create/?game=codenames", wait_until="networkidle")
            page.fill('input[name="title"]', f"Codenames Demo ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Spymaster Blue")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/codenames/**")
            page.wait_for_selector("#players-list", state="attached")
            time.sleep(1.0)

            board_path = cn_dir / f"codenames_lobby_{d_key}.png"
            page.screenshot(path=str(board_path))
            print(f"    -> Saved {board_path.name}")

            # Extract code to join second player so board can be dealt
            url_parts = page.url.split("/games/codenames/")
            if len(url_parts) > 1:
                code = url_parts[1].split("/")[0]
                p2_ctx = setup_browser_context(browser, d_key)
                p2_page = p2_ctx.new_page()
                p2_page.goto(f"{base_url}/games/{code}/", wait_until="networkidle")
                p2_page.wait_for_selector('input[name="name"]')
                p2_page.fill('input[name="name"]', "Operative Red")
                p2_page.click('button[type="submit"]')
                p2_page.wait_for_url(f"**/games/codenames/{code}/**")
                time.sleep(1.0)

                # Now start game on page
                start_btn = page.locator('button:has-text("Start Codenames")')
                if start_btn.is_visible():
                    start_btn.click()
                    page.wait_for_selector("#board-wrap", state="visible", timeout=6000)
                    time.sleep(1.0)
                    play_path = cn_dir / f"codenames_board_{d_key}.png"
                    page.screenshot(path=str(play_path))
                    print(f"    -> Saved {play_path.name}")

        except Exception as e:
            print(f"    [!] Error capturing codenames on {d_key}: {e}")
        finally:
            if p2_ctx:
                p2_ctx.close()
            ctx.close()


def capture_impostor(browser, base_url, out_dir, devices):
    """Capture Word Impostor game screens."""
    imp_dir = out_dir / "impostor"
    imp_dir.mkdir(parents=True, exist_ok=True)
    print("[*] Capturing Word Impostor...")

    rep_devices = [d for d in ["iphone_latest", "ipad", "laptop_fullscreen"] if d in devices] or [devices[0]]

    for d_key in rep_devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        p2_ctx = None
        try:
            page.goto(f"{base_url}/games/create/?game=impostor", wait_until="networkidle")
            page.fill('input[name="title"]', f"Impostor Demo ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Detective 1")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/impostor/**")
            page.wait_for_selector("#players-list", state="attached")
            time.sleep(1.0)

            lobby_path = imp_dir / f"impostor_lobby_{d_key}.png"
            page.screenshot(path=str(lobby_path))
            print(f"    -> Saved {lobby_path.name}")

            # Join 2nd player to start round
            url_parts = page.url.split("/games/impostor/")
            if len(url_parts) > 1:
                code = url_parts[1].split("/")[0]
                p2_ctx = setup_browser_context(browser, d_key)
                p2_page = p2_ctx.new_page()
                p2_page.goto(f"{base_url}/games/{code}/", wait_until="networkidle")
                p2_page.wait_for_selector('input[name="name"]')
                p2_page.fill('input[name="name"]', "Detective 2")
                p2_page.click('button[type="submit"]')
                p2_page.wait_for_url(f"**/games/impostor/{code}/**")
                time.sleep(1.0)

                start_btn = page.locator("#btn-start-game")
                if start_btn.is_visible():
                    start_btn.click()
                    page.wait_for_selector("#secret-card-box", state="visible", timeout=6000)
                    time.sleep(0.5)
                    page.click("#secret-card-box")
                    time.sleep(0.5)
                    play_path = imp_dir / f"impostor_playing_{d_key}.png"
                    page.screenshot(path=str(play_path))
                    print(f"    -> Saved {play_path.name}")

        except Exception as e:
            print(f"    [!] Error capturing impostor on {d_key}: {e}")
        finally:
            if p2_ctx:
                p2_ctx.close()
            ctx.close()


def capture_emojinary(browser, base_url, out_dir, devices):
    """Capture Emojinary game screens (Create, Lobby, Playing)."""
    ej_dir = out_dir / "emojinary"
    ej_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Capturing Emojinary ({len(devices)} devices)...")

    for d_key in devices:
        ctx = setup_browser_context(browser, d_key)
        page = ctx.new_page()
        page.on("console", lambda msg: print(f"    [console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [pageerror] {err}"))
        try:
            page.goto(f"{base_url}/games/create/?game=emojinary", wait_until="networkidle")
            page.fill('input[name="title"]', f"Emojinary Demo ({d_key})")
            solve_captcha(page)
            page.click('button[type="submit"]')

            page.wait_for_selector('input[name="name"]')
            page.fill('input[name="name"]', "Artist")
            page.click('button[type="submit"]')

            page.wait_for_url("**/games/emojinary/**")
            page.wait_for_selector("#players", state="attached")
            time.sleep(1.0)

            lobby_path = ej_dir / f"emojinary_lobby_{d_key}.png"
            page.screenshot(path=str(lobby_path))
            print(f"    -> Saved {lobby_path.name}")

            start_btn = page.locator("#start-btn")
            if start_btn.is_visible():
                start_btn.click()
                time.sleep(1.2)
                play_path = ej_dir / f"emojinary_playing_{d_key}.png"
                page.screenshot(path=str(play_path))
                print(f"    -> Saved {play_path.name}")
        except Exception as e:
            print(f"    [!] Error capturing emojinary on {d_key}: {e}")
        finally:
            ctx.close()


def main():
    parser = argparse.ArgumentParser(description="Multi-Device Screenshot Generator for Party Games")
    parser.add_argument(
        "--url", default="https://marco-silva.com", help="Base production/dev URL (default: https://marco-silva.com)"
    )
    parser.add_argument("--outdir", default="docs/screenshots", help="Output directory (default: docs/screenshots)")
    parser.add_argument("--devices", default="all", help="Comma-separated device keys or 'all'")
    parser.add_argument(
        "--games",
        default="all",
        help="Comma-separated games: portal,stop,dontsay,lupus,codenames,impostor,emojinary or 'all'",
    )
    parser.add_argument("--all", action="store_true", help="Generate all devices and all games")

    args = parser.parse_args()

    # Resolve devices
    if args.all or args.devices == "all":
        devices = list(DEVICE_CONFIGS.keys())
    else:
        devices = [d.strip() for d in args.devices.split(",") if d.strip() in DEVICE_CONFIGS]
        if not devices:
            devices = list(DEVICE_CONFIGS.keys())

    # Resolve games
    valid_games = ["portal", "stop", "dontsay", "rankit", "smartn", "lupus", "codenames", "impostor", "emojinary"]
    if args.all or args.games == "all":
        games = valid_games
    else:
        games = [g.strip() for g in args.games.split(",") if g.strip() in valid_games]
        if not games:
            games = valid_games

    out_dir = Path(args.outdir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    chromium_path = find_chromium_path()
    if not chromium_path:
        print(
            "[!] Error: Chromium binary not found. Run 'playwright install chromium' or install chromium package.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=== Multi-Device Game Screenshot Generator ===")
    print(f"Base URL    : {args.url}")
    print(f"Output Dir  : {out_dir}")
    print(f"Chromium    : {chromium_path}")
    print(f"Devices ({len(devices)}): {', '.join(devices)}")
    print(f"Games   ({len(games)}): {', '.join(games)}")
    print("=" * 48)

    # Ensure fontconfig path for emoji rendering
    env = dict(os.environ)
    fc_conf = Path("/home/msilva/.config/fontconfig/fonts.conf")
    if fc_conf.exists():
        env["FONTCONFIG_FILE"] = str(fc_conf)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chromium_path,
            headless=True,
            env=env,
        )

        start_time = time.time()

        if "portal" in games:
            capture_portal(browser, args.url, out_dir, devices)

        if "stop" in games:
            capture_stop(browser, args.url, out_dir, devices)

        if "dontsay" in games:
            capture_dontsay(browser, args.url, out_dir, devices)

        if "rankit" in games:
            capture_rankit(browser, args.url, out_dir, devices)

        if "smartn" in games:
            capture_smartn(browser, args.url, out_dir, devices)

        if "lupus" in games:
            capture_lupus(browser, args.url, out_dir, devices)

        if "codenames" in games:
            capture_codenames(browser, args.url, out_dir, devices)

        if "impostor" in games:
            capture_impostor(browser, args.url, out_dir, devices)

        if "emojinary" in games:
            capture_emojinary(browser, args.url, out_dir, devices)

        browser.close()
        elapsed = time.time() - start_time
        print(f"\n[✓] Completed in {elapsed:.1f}s. Assets generated in {out_dir}/")


if __name__ == "__main__":
    main()

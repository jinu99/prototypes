"""Playwright test: capture dashboard screenshots and verify basic functionality."""

import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8400"
SCREENSHOT_DIR = "screenshots"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Load dashboard
        page.goto(BASE)
        page.wait_for_timeout(2000)  # Wait for API data to load

        # Screenshot: main dashboard
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_dashboard_main.png")
        print("Screenshot: 01_dashboard_main.png")

        # Verify header exists
        header = page.text_content("header h1")
        assert "Agent Stabilizer" in header, f"Expected header, got: {header}"
        print(f"Header: {header.strip()}")

        # Verify stats loaded
        sessions_stat = page.text_content("#stat-sessions")
        print(f"Sessions stat: {sessions_stat}")
        assert sessions_stat != "-", "Stats should have loaded"

        blocked_stat = page.text_content("#stat-blocked")
        print(f"Blocked stat: {blocked_stat}")

        # Click first session if available
        session_items = page.query_selector_all(".session-item")
        if session_items:
            session_items[0].click()
            page.wait_for_timeout(1000)
            page.screenshot(path=f"{SCREENSHOT_DIR}/02_session_selected.png")
            print("Screenshot: 02_session_selected.png")

        # Switch to blocked tab
        blocked_tab = page.query_selector('[data-tab="blocked"]')
        if blocked_tab:
            blocked_tab.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=f"{SCREENSHOT_DIR}/03_blocked_view.png")
            print("Screenshot: 03_blocked_view.png")

        browser.close()
        print("\nAll dashboard tests passed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

"""Playwright test script for dashboard screenshots and verification."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
BASE_URL = "http://localhost:8088"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # 1. Empty state
        page.goto(BASE_URL)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_empty_state.png"))
        print("[OK] Screenshot: empty state")

        # 2. Load demo data
        page.click("text=Load Demo")
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_demo_overview.png"))
        print("[OK] Screenshot: demo overview")

        # 3. Click on call #4 (the one with warning)
        items = page.query_selector_all(".call-item")
        if len(items) >= 3:
            items[-1].click()  # Last item should have the warning
            page.wait_for_timeout(1000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_warning_call.png"))
            print("[OK] Screenshot: warning call")

        # 4. Messages tab
        page.click("text=Messages")
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_messages_tab.png"))
        print("[OK] Screenshot: messages tab")

        # 5. Diff tab - select call #2 overview first
        items = page.query_selector_all(".call-item")
        if len(items) >= 2:
            items[1].click()  # Second call
            page.wait_for_timeout(1000)

        page.click("text=Diff")
        page.wait_for_timeout(500)
        page.click("text=Compare")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_diff_view.png"))
        print("[OK] Screenshot: diff view")

        # 6. Verify key elements exist
        page.click("text=Overview")
        page.wait_for_timeout(500)
        checks = {
            "bar_chart": page.query_selector(".token-chart") is not None,
            "treemap": page.query_selector(".treemap-container") is not None,
            "call_list": len(page.query_selector_all(".call-item")) > 0,
            "legend": page.query_selector(".legend") is not None,
        }

        print("\n--- Verification ---")
        for name, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name}")

        browser.close()
        print("\nAll screenshots saved to screenshots/")


if __name__ == "__main__":
    main()

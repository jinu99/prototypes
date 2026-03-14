"""Playwright browser test — screenshots and basic interaction."""

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
SHOTS = "screenshots"


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1024, "height": 768})

        # 1. Initial empty state
        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.screenshot(path=f"{SHOTS}/01_initial.png")
        print("[OK] 01_initial.png — empty state")

        # 2. Click "Collect Now"
        page.click("text=Collect Now")
        page.wait_for_timeout(3000)
        page.screenshot(path=f"{SHOTS}/02_after_collect.png")
        print("[OK] 02_after_collect.png — timeline with data")

        # 3. Filter by Reddit
        page.click("button.tab >> text=Reddit")
        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/03_reddit_filter.png")
        print("[OK] 03_reddit_filter.png — Reddit only")

        # 4. Filter by RSS
        page.click("button.tab >> text=RSS")
        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/04_rss_filter.png")
        print("[OK] 04_rss_filter.png — RSS only")

        # 5. Noise filter — set min score to 100
        page.click("button.tab >> text=All")
        page.fill("#minScore", "100")
        page.press("#minScore", "Enter")
        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/05_noise_filter.png")
        print("[OK] 05_noise_filter.png — min score 100")

        # 6. Open Settings panel
        page.fill("#minScore", "0")
        page.press("#minScore", "Enter")
        page.click("text=Settings")
        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/06_settings.png")
        print("[OK] 06_settings.png — config panel open")

        # 7. Add a keyword
        page.fill("#newKeyword", "rust")
        page.click("#configPanel .config-section:first-child button.sm")
        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/07_keyword_added.png")
        print("[OK] 07_keyword_added.png — 'rust' keyword added")

        browser.close()
        print("\nAll screenshots saved to screenshots/")


if __name__ == "__main__":
    run()

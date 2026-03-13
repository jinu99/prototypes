"""Take screenshots of the dashboard for review."""

from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


def take_screenshots():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Full page screenshot
        page.screenshot(path=str(SCREENSHOTS_DIR / "dashboard_full.png"), full_page=True)
        print(f"Saved: {SCREENSHOTS_DIR / 'dashboard_full.png'}")

        # Timeline area
        page.screenshot(path=str(SCREENSHOTS_DIR / "dashboard_top.png"),
                       clip={"x": 0, "y": 0, "width": 1400, "height": 350})
        print(f"Saved: {SCREENSHOTS_DIR / 'dashboard_top.png'}")

        browser.close()


if __name__ == "__main__":
    take_screenshots()

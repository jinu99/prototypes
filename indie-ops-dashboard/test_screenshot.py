"""Take screenshots of the dashboard for visual inspection."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)
URL = "http://localhost:8099"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        await page.goto(URL)
        # Wait for charts and data to load
        await page.wait_for_function("document.getElementById('stat-cpu').textContent !== '—'", timeout=15000)
        await asyncio.sleep(2)  # let Chart.js animations finish

        # Full page screenshot
        await page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-full.png"), full_page=True)
        print("Saved: dashboard-full.png")

        # Main panel only (viewport crop)
        await page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-viewport.png"))
        print("Saved: dashboard-viewport.png")

        # Click refresh and capture
        await page.click("text=Refresh")
        await asyncio.sleep(2)
        await page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-after-refresh.png"))
        print("Saved: dashboard-after-refresh.png")

        # Test uptime check button
        await page.click("text=Check Now")
        await asyncio.sleep(3)
        await page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-after-uptime-check.png"))
        print("Saved: dashboard-after-uptime-check.png")

        # Test heartbeat button
        await page.click("text=Send Test Beat")
        await asyncio.sleep(1)
        await page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-after-heartbeat.png"))
        print("Saved: dashboard-after-heartbeat.png")

        await browser.close()
        print("\nAll screenshots saved to screenshots/")


if __name__ == "__main__":
    asyncio.run(main())

"""Take screenshots of the dashboard for visual verification."""
import subprocess
import sys

def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Load dashboard
        page.goto("http://localhost:8787/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Wait for Chart.js to render

        # Full page screenshot
        page.screenshot(path="screenshots/dashboard-full.png", full_page=True)
        print("Saved: screenshots/dashboard-full.png")

        # Top section (summary + charts)
        page.screenshot(path="screenshots/dashboard-top.png", clip={"x": 0, "y": 0, "width": 1400, "height": 600})
        print("Saved: screenshots/dashboard-top.png")

        # Click Run Attribution and screenshot again
        page.click("text=Run Attribution")
        page.wait_for_timeout(1500)
        page.screenshot(path="screenshots/dashboard-after-match.png", full_page=True)
        print("Saved: screenshots/dashboard-after-match.png")

        browser.close()


if __name__ == "__main__":
    main()

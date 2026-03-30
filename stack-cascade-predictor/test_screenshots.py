"""Playwright screenshot tests for the dashboard."""

import time
import requests
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8099"
SHOTS = "screenshots"


def main():
    # Reset first
    requests.post(f"{BASE}/api/reset")
    time.sleep(0.5)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # 1. Initial state — all operational
        page.goto(BASE)
        page.wait_for_timeout(2000)  # Wait for SSE + graph layout
        page.screenshot(path=f"{SHOTS}/01_initial_state.png")
        print("[OK] Screenshot: initial state")

        # 2. Simulate AWS outage
        requests.post(f"{BASE}/api/simulate", json={
            "service_id": "aws-us-east-1", "status": "outage"
        })
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{SHOTS}/02_aws_outage_cascade.png")
        print("[OK] Screenshot: AWS outage cascade")

        # 3. Reset + simulate Stripe degraded
        requests.post(f"{BASE}/api/reset")
        page.wait_for_timeout(1000)
        requests.post(f"{BASE}/api/simulate", json={
            "service_id": "stripe", "status": "degraded"
        })
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{SHOTS}/03_stripe_degraded.png")
        print("[OK] Screenshot: Stripe degraded")

        # 4. Reset + poll mock feeds
        requests.post(f"{BASE}/api/reset")
        page.wait_for_timeout(1000)
        requests.post(f"{BASE}/api/poll-now")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{SHOTS}/04_feed_poll_result.png")
        print("[OK] Screenshot: feed poll result")

        browser.close()
    print("\nAll screenshots saved to screenshots/")


if __name__ == "__main__":
    main()

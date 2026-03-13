"""Playwright browser tests — captures screenshots and validates UI behavior."""

import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8765"
SCREENSHOTS = "screenshots"


def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # 1. Landing page — Single Model tab
        page.goto(BASE_URL)
        page.wait_for_selector("#single-model option")
        page.screenshot(path=f"{SCREENSHOTS}/01_landing.png")
        print("[OK] Landing page loaded")

        # 2. Single model estimate
        page.select_option("#single-model", "llama-7b-q4km")
        page.select_option("#single-ctx", "4096")
        page.click("button:text('Estimate')")
        page.wait_for_selector(".stat-grid")
        time.sleep(0.5)
        page.screenshot(path=f"{SCREENSHOTS}/02_single_estimate.png")
        print("[OK] Single model estimate rendered")

        # 3. MoE model (Mixtral)
        page.select_option("#single-model", "mixtral-8x7b-q4km")
        page.click("button:text('Estimate')")
        page.wait_for_selector(".moe-table")
        time.sleep(0.5)
        page.screenshot(path=f"{SCREENSHOTS}/03_moe_estimate.png")
        print("[OK] MoE model with offloading table")

        # 4. Multi-Model tab
        page.click(".tab:text('Multi-Model')")
        page.check("#multi-llama-7b-q4km")
        page.check("#multi-phi-2-q8")
        page.fill("#multi-budget", "24576")
        page.click("button:text('Plan Multi-Model')")
        page.wait_for_selector(".stat-grid")
        time.sleep(0.5)
        page.screenshot(path=f"{SCREENSHOTS}/04_multi_model.png")
        print("[OK] Multi-model planning")

        # 5. Grid Search tab
        page.click(".tab:text('Grid Search')")
        page.fill("#grid-budget", "8192")
        page.click("button:text('Search Feasible Combos')")
        page.wait_for_selector(".grid-results")
        time.sleep(0.5)
        page.screenshot(path=f"{SCREENSHOTS}/05_grid_search.png")
        print("[OK] Grid search results")

        # 6. Validation tab
        page.click(".tab:text('llama.cpp Validation')")
        page.click("button:text('Run Validation')")
        page.wait_for_selector(".badge-ok")
        time.sleep(0.5)
        page.screenshot(path=f"{SCREENSHOTS}/06_validation.png")
        print("[OK] llama.cpp validation")

        # 7. GGUF Upload tab
        page.click(".tab:text('GGUF Upload')")
        page.screenshot(path=f"{SCREENSHOTS}/07_upload_tab.png")
        print("[OK] Upload tab")

        browser.close()
        print("\nAll browser tests passed!")


if __name__ == "__main__":
    run_tests()

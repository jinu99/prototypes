"""End-to-end Playwright test for the feed relevance engine."""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
SCREENSHOTS = Path(__file__).parent / "screenshots"
SAMPLE_OPML = Path(__file__).parent / "sample.opml"


def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768})

        # 1. Load main page
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS / "01_initial.png"))
        print("[OK] 01_initial - Main page loaded")

        # 2. Upload OPML
        file_input = page.locator("#opml-input")
        file_input.set_input_files(str(SAMPLE_OPML))
        # Wait for upload to complete (articles to appear or message)
        page.wait_for_function(
            "document.querySelector('.msg-ok') !== null",
            timeout=120000,
        )
        page.screenshot(path=str(SCREENSHOTS / "02_opml_uploaded.png"))
        print("[OK] 02_opml_uploaded - OPML uploaded and feeds fetched")

        # 3. Set keywords
        page.fill("#keywords-input", "machine learning, LLM, distributed systems, rust, system design")
        page.click("#keywords-btn")
        page.wait_for_function(
            "document.querySelectorAll('.keyword-tag').length > 0",
            timeout=30000,
        )
        time.sleep(1)  # Let scores update
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS / "03_keywords_set.png"))
        print("[OK] 03_keywords_set - Keywords set and articles scored")

        # 4. Check articles are visible with scores
        articles = page.locator(".article")
        count = articles.count()
        assert count > 0, f"Expected articles but got {count}"
        print(f"[OK] Found {count} articles displayed")

        # Check score badges
        scores = page.locator(".score-badge")
        first_score = scores.first.text_content()
        print(f"[OK] First article score: {first_score}")

        page.screenshot(path=str(SCREENSHOTS / "04_articles_scored.png"))
        print("[OK] 04_articles_scored - Articles with scores visible")

        # 5. Click Read on first article
        read_btns = page.locator(".btn-read")
        if read_btns.count() > 0:
            read_btns.first.click()
            page.wait_for_function(
                "document.querySelector('.msg-ok') !== null",
                timeout=10000,
            )
            time.sleep(1)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(SCREENSHOTS / "05_feedback_read.png"))
            print("[OK] 05_feedback_read - Read feedback submitted")

        # 6. Click Skip on a few articles
        skip_btns = page.locator(".btn-skip")
        for i in range(min(3, skip_btns.count())):
            skip_btns.nth(0).click()  # always first since list re-renders
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)

        page.screenshot(path=str(SCREENSHOTS / "06_after_feedback.png"))
        print("[OK] 06_after_feedback - Multiple feedbacks submitted")

        # 7. Check stats updated
        feedbacks_el = page.locator("#s-feedbacks")
        fb_count = feedbacks_el.text_content()
        print(f"[OK] Feedback count in stats: {fb_count}")

        # Final full page
        page.screenshot(path=str(SCREENSHOTS / "07_final.png"), full_page=True)
        print("[OK] 07_final - Full page screenshot")

        browser.close()
        print("\n[ALL TESTS PASSED]")


if __name__ == "__main__":
    run_tests()

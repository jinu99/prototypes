"""Take screenshots of the generated report for visual verification."""

from playwright.sync_api import sync_playwright
from pathlib import Path

REPORT = Path(__file__).parent / "demo_report.html"
SCREENSHOTS = Path(__file__).parent / "screenshots"


def main():
    SCREENSHOTS.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1024, "height": 768})

        page.goto(f"file://{REPORT.resolve()}")
        page.wait_for_load_state("networkidle")

        # Full page screenshot
        page.screenshot(path=str(SCREENSHOTS / "full_report.png"), full_page=True)
        print("Saved: full_report.png")

        # Header/summary area
        page.screenshot(path=str(SCREENSHOTS / "header_summary.png"),
                        clip={"x": 0, "y": 0, "width": 1024, "height": 300})
        print("Saved: header_summary.png")

        # Click first segment with file changes to expand it
        segments = page.query_selector_all(".segment")
        for seg in segments:
            badge = seg.query_selector(".badge-files")
            if badge:
                header = seg.query_selector(".segment-header")
                header.click()
                page.wait_for_timeout(300)
                seg.screenshot(path=str(SCREENSHOTS / "expanded_segment.png"))
                print("Saved: expanded_segment.png")
                break

        # Find a segment with mismatches
        for seg in segments:
            badge = seg.query_selector(".badge-warn")
            if badge:
                header = seg.query_selector(".segment-header")
                # Make sure it's open
                if "open" not in (seg.get_attribute("class") or ""):
                    header.click()
                    page.wait_for_timeout(300)
                seg.screenshot(path=str(SCREENSHOTS / "mismatch_segment.png"))
                print("Saved: mismatch_segment.png")
                break

        browser.close()
        print("Done!")


if __name__ == "__main__":
    main()

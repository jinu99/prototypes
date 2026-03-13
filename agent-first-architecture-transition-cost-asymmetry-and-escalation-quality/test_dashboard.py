"""
Playwright로 대시보드 스크린샷을 찍고 기본 동작을 확인하는 스크립트.
"""

import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
PORT = 8000


def main():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    # 서버 시작
    server = subprocess.Popen(
        [sys.executable, "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1400, "height": 900})

            page.goto(f"http://localhost:{PORT}/dashboard.html")
            page.wait_for_selector(".metric-card", timeout=5000)
            time.sleep(1)  # wait for transitions

            # 1. 전체 대시보드 스크린샷
            page.screenshot(
                path=str(SCREENSHOTS_DIR / "01_dashboard_overview.png"),
                full_page=False,
            )
            print("1. 대시보드 개요 스크린샷 완료")

            # 2. 시나리오 카드 하나 펼치기 (E01: 엣지 케이스)
            cards = page.query_selector_all(".scenario-card")
            if len(cards) >= 9:
                cards[8].query_selector(".scenario-header").click()
                time.sleep(0.5)
                cards[8].scroll_into_view_if_needed()
                page.screenshot(
                    path=str(SCREENSHOTS_DIR / "02_edge_case_detail.png"),
                    full_page=False,
                )
                print("2. 엣지 케이스 상세 스크린샷 완료")

            # 3. 전체 페이지 풀 스크린샷
            page.screenshot(
                path=str(SCREENSHOTS_DIR / "03_full_page.png"),
                full_page=True,
            )
            print("3. 전체 페이지 스크린샷 완료")

            # 4. 기본 검증
            metric_values = page.query_selector_all(".metric-card .value")
            values = [el.text_content() for el in metric_values]
            print(f"메트릭 값: {values}")

            scenario_count = len(cards)
            print(f"시나리오 카드 수: {scenario_count}")

            assert scenario_count == 10, f"시나리오 10개 기대, {scenario_count}개 발견"
            assert "100%" in values[1], f"Agent 정확도 100% 기대, {values[1]} 발견"

            print("\n모든 검증 통과!")
            browser.close()

    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()

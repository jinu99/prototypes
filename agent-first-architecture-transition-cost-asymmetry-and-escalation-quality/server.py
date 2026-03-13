"""
대시보드용 간단한 HTTP 서버.
output/results.json을 제공하고 dashboard.html을 서빙한다.
"""

import http.server
import json
from pathlib import Path

PORT = 8000
BASE_DIR = Path(__file__).parent


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def main():
    # 결과 파일이 없으면 시뮬레이션 먼저 실행
    results_path = BASE_DIR / "output" / "results.json"
    if not results_path.exists():
        print("결과 파일이 없습니다. 먼저 시뮬레이션을 실행합니다...")
        from main import run_simulation
        run_simulation()

    print(f"\n대시보드 서버 시작: http://localhost:{PORT}/dashboard.html")
    print("종료: Ctrl+C\n")

    server = http.server.HTTPServer(("", PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")
        server.shutdown()


if __name__ == "__main__":
    main()

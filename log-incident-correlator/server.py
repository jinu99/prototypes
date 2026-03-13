"""Simple HTTP server for the dashboard."""

import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from db import get_connection, init_db, get_all_templates, get_all_deploys, get_all_correlations

_db_path = None


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self.path = "/dashboard.html"
            return super().do_GET()
        elif self.path == "/api/data":
            return self._serve_api_data()
        else:
            return super().do_GET()

    def _serve_api_data(self):
        conn = get_connection(_db_path)
        init_db(conn)
        data = {
            "templates": get_all_templates(conn),
            "deploys": get_all_deploys(conn),
            "correlations": get_all_correlations(conn),
        }
        conn.close()

        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress default logging


def run_server(db_path: Path = None, port: int = 8080):
    global _db_path
    _db_path = db_path or Path("correlator.db")

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"Dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()

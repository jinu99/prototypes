"""Simple echo server that receives webhooks and tracks requests.

Useful as a local test target for chaos scenarios.
Supports configurable failure modes for testing.
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict


class EchoState:
    """Shared state for the echo server."""

    def __init__(self):
        self.requests: list[dict] = []
        self.seen_ids: set[str] = set()
        self.lock = threading.Lock()
        # Config: if True, return 409 on duplicate idempotency keys
        self.reject_duplicates = False

    def reset(self):
        with self.lock:
            self.requests.clear()
            self.seen_ids.clear()


_state = EchoState()


class EchoHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body.decode("utf-8", errors="replace")}

        idempotency_key = self.headers.get("Idempotency-Key", "")

        with _state.lock:
            record = {
                "method": "POST",
                "path": self.path,
                "headers": dict(self.headers),
                "body": payload,
                "idempotency_key": idempotency_key,
                "seq": len(_state.requests),
            }
            _state.requests.append(record)

            if _state.reject_duplicates and idempotency_key:
                if idempotency_key in _state.seen_ids:
                    self.send_response(409)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "duplicate",
                        "idempotency_key": idempotency_key,
                    }).encode())
                    return
                _state.seen_ids.add(idempotency_key)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "received", "seq": record["seq"]}).encode())

    def do_GET(self):
        if self.path == "/_requests":
            with _state.lock:
                data = list(_state.requests)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())
            return

        if self.path == "/_reset":
            _state.reset()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"reset"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Webhook Echo Server")

    def log_message(self, format, *args):
        pass  # suppress request logs


def get_state() -> EchoState:
    return _state


def run_server(port: int = 9876, reject_duplicates: bool = False) -> HTTPServer:
    _state.reset()
    _state.reject_duplicates = reject_duplicates
    server = HTTPServer(("127.0.0.1", port), EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

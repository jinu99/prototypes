"""Minimal HTTP forward proxy for capturing outbound HTTP traffic."""

import asyncio
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
import threading
import json
import time
import sqlite3

logger = logging.getLogger(__name__)


class ProxyHandler(BaseHTTPRequestHandler):
    """Simple HTTP forward proxy handler.

    Captures request/response and stores in SQLite via the shared state
    set on the server instance.
    """

    def do_GET(self):
        self._proxy_request("GET")

    def do_POST(self):
        self._proxy_request("POST")

    def do_PUT(self):
        self._proxy_request("PUT")

    def do_DELETE(self):
        self._proxy_request("DELETE")

    def do_PATCH(self):
        self._proxy_request("PATCH")

    def do_HEAD(self):
        self._proxy_request("HEAD")

    def _proxy_request(self, method: str):
        url = self.path
        # Read request body if present
        content_length = int(self.headers.get("Content-Length", 0))
        req_body = self.rfile.read(content_length) if content_length > 0 else b""

        # Build forwarding headers (skip hop-by-hop)
        skip = {"host", "proxy-connection", "connection", "keep-alive",
                "transfer-encoding", "te", "trailer", "upgrade",
                "proxy-authorization", "proxy-authenticate"}
        fwd_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in skip
        }

        req_headers_dict = dict(self.headers.items())
        status_code = 502
        resp_headers_dict: dict = {}
        resp_body = b""

        try:
            req = Request(url, data=req_body if req_body else None,
                          headers=fwd_headers, method=method)
            with urlopen(req, timeout=30) as resp:
                status_code = resp.status
                resp_headers_dict = dict(resp.headers.items())
                resp_body = resp.read()
        except URLError as e:
            status_code = 502
            resp_body = str(e).encode()
        except Exception as e:
            status_code = 502
            resp_body = f"Proxy error: {e}".encode()

        # Store in SQLite
        try:
            store_fn = self.server.store_http  # type: ignore
            store_fn(
                method=method,
                url=url,
                req_headers=req_headers_dict,
                req_body=req_body.decode("utf-8", errors="replace")[:4096],
                status_code=status_code,
                resp_headers=resp_headers_dict,
                resp_body=resp_body.decode("utf-8", errors="replace")[:4096],
            )
        except Exception:
            logger.exception("Failed to store HTTP traffic")

        # Send response back
        self.send_response(status_code)
        for k, v in resp_headers_dict.items():
            if k.lower() not in ("transfer-encoding", "connection"):
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, format, *args):
        logger.debug("PROXY: %s", format % args)


def start_proxy(port: int, store_fn) -> tuple[HTTPServer, threading.Thread]:
    """Start the HTTP proxy on a background thread. Returns (server, thread)."""
    server = HTTPServer(("127.0.0.1", port), ProxyHandler)
    server.store_http = store_fn  # type: ignore
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("HTTP proxy listening on 127.0.0.1:%d", port)
    return server, thread


def find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

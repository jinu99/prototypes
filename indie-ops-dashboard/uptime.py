"""Uptime checker with HTTP ping + retry."""

import asyncio
import time
from urllib.request import urlopen, Request
from urllib.error import URLError

from database import insert_uptime_check

MAX_RETRIES = 2
TIMEOUT_SEC = 5

# Default targets for demo
DEFAULT_TARGETS = [
    "https://httpbin.org/status/200",
    "https://example.com",
]


async def check_url(url: str) -> dict:
    """Check a single URL with retry logic. Returns result dict."""
    for attempt in range(1 + MAX_RETRIES):
        start = time.time()
        try:
            req = Request(url, method="GET")
            resp = await asyncio.get_event_loop().run_in_executor(
                None, lambda: urlopen(req, timeout=TIMEOUT_SEC)
            )
            elapsed_ms = (time.time() - start) * 1000
            result = {
                "url": url,
                "status": "up",
                "response_ms": round(elapsed_ms, 1),
                "error": None,
            }
            await insert_uptime_check(time.time(), url, "up", result["response_ms"], None)
            return result
        except (URLError, OSError, TimeoutError) as e:
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1)
                continue
            elapsed_ms = (time.time() - start) * 1000
            error_msg = str(e)[:200]
            result = {
                "url": url,
                "status": "down",
                "response_ms": round(elapsed_ms, 1),
                "error": error_msg,
            }
            await insert_uptime_check(time.time(), url, "down", result["response_ms"], error_msg)
            return result


async def run_uptime_checks(targets: list[str] | None = None) -> list[dict]:
    """Run uptime checks for all targets."""
    urls = targets or DEFAULT_TARGETS
    results = await asyncio.gather(*[check_url(u) for u in urls])
    return list(results)

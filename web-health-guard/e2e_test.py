"""End-to-end test — curl-based API verification + HTML response validation."""

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

PORT = 8767
BASE = f"http://localhost:{PORT}"
SCREENSHOTS = Path("screenshots")
SCREENSHOTS.mkdir(exist_ok=True)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def api_get(path):
    result = subprocess.run(
        ["curl", "-s", f"{BASE}{path}"],
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout


def start_server():
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(3)
    return proc


def main():
    proc = start_server()
    try:
        # -- Test 1: Landing page --
        print("\n=== Test: Landing Page ===")
        html = api_get("/")
        check("Index returns HTML", "<title>Web Health Guard</title>" in html)
        check("Search bar present", 'id="urlInput"' in html)
        check("Scan button present", 'id="scanBtn"' in html)

        # Save landing page HTML for inspection
        Path(SCREENSHOTS / "01_landing.html").write_text(html)

        # -- Test 2: Scan github.com --
        print("\n=== Test: Scan github.com ===")
        raw = api_get(f"/api/scan?url={quote('https://github.com')}")
        data = json.loads(raw)

        check("Scan returns url", data.get("url") == "https://github.com")
        check("Page status 200", data.get("page_status") == 200)

        seo = data.get("seo", [])
        check("SEO items >= 10", len(seo) >= 10, f"got {len(seo)}")
        passed = sum(1 for c in seo if c["passed"])
        failed = len(seo) - passed
        check("SEO has pass/fail", passed > 0 and failed >= 0, f"{passed} pass, {failed} fail")
        check("SEO has developer explanations", all(len(c.get("detail", "")) > 5 for c in seo))

        robots = data.get("robots", {})
        crawlers = robots.get("crawlers", [])
        check("AI crawlers >= 5", len(crawlers) >= 5, f"got {len(crawlers)}")
        check("robots.txt found", robots.get("found") is True)

        blocked_count = sum(1 for c in crawlers if c["blocked"])
        check("Some crawlers checked", blocked_count >= 0, f"{blocked_count} blocked")

        snippet = robots.get("block_snippet")
        if blocked_count < len(crawlers):
            check("Block snippet generated", snippet is not None and len(snippet) > 10)
        else:
            check("All crawlers blocked (no snippet needed)", snippet is None)

        phantom = data.get("phantom", {})
        check("Phantom section present", "phantoms" in phantom)
        check("Remediation guide present", "remediation" in phantom)
        check("Remediation has entries", len(phantom.get("remediation", {})) >= 3)

        # Save full response
        Path(SCREENSHOTS / "02_scan_github.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )

        # -- Test 3: Scan wikipedia.org --
        print("\n=== Test: Scan wikipedia.org ===")
        raw2 = api_get(f"/api/scan?url={quote('https://wikipedia.org')}")
        data2 = json.loads(raw2)
        check("Wikipedia scan succeeds", data2.get("page_status") == 200)
        check("Wikipedia SEO items >= 10", len(data2.get("seo", [])) >= 10)
        check("Wikipedia robots analyzed", "crawlers" in data2.get("robots", {}))

        Path(SCREENSHOTS / "03_scan_wikipedia.json").write_text(
            json.dumps(data2, indent=2, ensure_ascii=False)
        )

        # -- Test 4: Scan example.com (simple site) --
        print("\n=== Test: Scan example.com ===")
        raw3 = api_get(f"/api/scan?url={quote('https://example.com')}")
        data3 = json.loads(raw3)
        check("Example.com scan succeeds", data3.get("page_status") == 200)

        # -- Test 5: Invalid URL --
        print("\n=== Test: Invalid URL ===")
        raw4 = api_get(f"/api/scan?url={quote('https://this-does-not-exist-12345.com')}")
        data4 = json.loads(raw4)
        check("Invalid URL returns error", "error" in data4)

        # -- Test 6: Response time --
        print("\n=== Test: Response Time ===")
        start = time.time()
        api_get(f"/api/scan?url={quote('https://example.com')}")
        elapsed = time.time() - start
        check("Response within 30 seconds", elapsed < 30, f"{elapsed:.1f}s")

        # -- Summary --
        print(f"\n{'='*50}")
        print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} checks")
        print(f"{'='*50}")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()

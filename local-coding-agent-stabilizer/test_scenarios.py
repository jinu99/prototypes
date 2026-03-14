"""Test scenarios: simulate destructive edit patterns against the proxy in mock mode."""

import httpx
import json
import sys
import time

BASE = "http://localhost:8400"
HEADERS = {"Content-Type": "application/json"}


def chat(messages, session_id="test", stream=False):
    """Send a chat completion request."""
    resp = httpx.post(
        f"{BASE}/v1/chat/completions",
        json={"model": "mock-model", "messages": messages, "stream": stream},
        headers={**HEADERS, "x-session-id": session_id},
        timeout=30,
    )
    return resp.json()


def test_normal():
    """Normal tool call — should pass through."""
    print("=== Test 1: Normal tool call ===")
    result = chat([{"role": "user", "content": "write a hello world"}], session_id="normal-1")
    content = result["choices"][0]["message"]["content"]
    blocked = result.get("stabilizer", {}).get("blocked", False)
    print(f"  Content: {content[:80]}")
    print(f"  Blocked: {blocked}")
    assert not blocked, "Normal call should NOT be blocked"
    print("  PASS\n")


def test_file_deletion():
    """File deletion — should be blocked."""
    print("=== Test 2: File deletion ===")
    result = chat([{"role": "user", "content": "delete the main file"}], session_id="delete-1")
    content = result["choices"][0]["message"]["content"]
    blocked = result.get("stabilizer", {}).get("blocked", False)
    print(f"  Content: {content[:80]}")
    print(f"  Blocked: {blocked}")
    assert blocked, "File deletion should be blocked"
    assert "BLOCKED" in content
    print("  PASS\n")


def test_empty_write():
    """Empty file write — should be blocked."""
    print("=== Test 3: Empty file write ===")
    result = chat([{"role": "user", "content": "clear the utils file"}], session_id="empty-1")
    content = result["choices"][0]["message"]["content"]
    blocked = result.get("stabilizer", {}).get("blocked", False)
    print(f"  Content: {content[:80]}")
    print(f"  Blocked: {blocked}")
    assert blocked, "Empty write should be blocked"
    print("  PASS\n")


def test_massive_deletion():
    """Massive content deletion — should be blocked."""
    print("=== Test 4: Massive deletion (>80%) ===")
    result = chat([{"role": "user", "content": "rewrite all of app.py"}], session_id="mass-1")
    content = result["choices"][0]["message"]["content"]
    blocked = result.get("stabilizer", {}).get("blocked", False)
    print(f"  Content: {content[:80]}")
    print(f"  Blocked: {blocked}")
    assert blocked, "Massive deletion should be blocked"
    print("  PASS\n")


def test_loop_detection():
    """Repeated identical tool calls — should be blocked on 3rd."""
    print("=== Test 5: Loop detection ===")
    sid = "loop-1"
    # The mock mode sends 3 identical tool calls in one request
    result = chat([{"role": "user", "content": "loop this edit"}], session_id=sid)
    content = result["choices"][0]["message"]["content"]
    blocked = result.get("stabilizer", {}).get("blocked", False)
    print(f"  Content: {content[:80]}")
    print(f"  Blocked: {blocked}")
    assert blocked, "Loop should be detected and blocked"
    assert "Loop" in content or "loop" in content.lower()
    print("  PASS\n")


def test_dashboard_api():
    """Verify dashboard API endpoints return data."""
    print("=== Test 6: Dashboard APIs ===")
    stats = httpx.get(f"{BASE}/api/stats", timeout=10).json()
    print(f"  Stats: {stats}")
    assert stats["total_sessions"] > 0, "Should have sessions"
    assert stats["total_blocked"] > 0, "Should have blocked events"

    sessions = httpx.get(f"{BASE}/api/sessions", timeout=10).json()
    print(f"  Sessions: {len(sessions)} found")
    assert len(sessions) > 0

    blocked = httpx.get(f"{BASE}/api/blocked", timeout=10).json()
    print(f"  Blocked events: {len(blocked)} found")
    assert len(blocked) > 0

    # Dashboard HTML should load
    dash = httpx.get(f"{BASE}/", timeout=10)
    assert dash.status_code == 200
    assert "Agent Stabilizer" in dash.text
    print("  Dashboard HTML: OK")
    print("  PASS\n")


def main():
    print("\n🧪 Running Stabilizer Test Scenarios\n")
    print(f"Target: {BASE}\n")

    # Check server is up
    try:
        httpx.get(f"{BASE}/api/stats", timeout=5)
    except httpx.ConnectError:
        print("ERROR: Server not running. Start with: uv run python proxy.py --mock")
        sys.exit(1)

    tests = [test_normal, test_file_deletion, test_empty_write,
             test_massive_deletion, test_loop_detection, test_dashboard_api]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}\n")
            failed += 1

    print(f"{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

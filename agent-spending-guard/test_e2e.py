"""End-to-end test: starts mock server + proxy, runs agent scenarios, checks audit log."""

import json
import os
import signal
import subprocess
import sys
import time
import requests

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_PORT = 9000
PROXY_PORT = 8080
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}"
MOCK_URL = f"http://127.0.0.1:{MOCK_PORT}"

processes = []


def start_process(cmd, name, env=None):
    full_env = {**os.environ, **(env or {})}
    proc = subprocess.Popen(
        cmd, cwd=PROJECT_DIR, env=full_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    processes.append((name, proc))
    print(f"  Started {name} (PID {proc.pid})")
    return proc


def cleanup():
    for name, proc in processes:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"  Stopped {name}")


def wait_for_port(port, timeout=15):
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.3)
    return False


def make_proxied_request(method, path, data=None, json_data=None):
    url = f"{MOCK_URL}{path}"
    proxies = {"http": PROXY_URL}
    try:
        resp = requests.request(
            method, url, data=data, json=json_data,
            proxies=proxies, timeout=10,
        )
        return resp.status_code, resp.json()
    except Exception as e:
        return None, {"error": str(e)}


def test_pass_through():
    """Non-payment request should pass through."""
    print("\n[TEST] Pass-through (health check)")
    status, body = make_proxied_request("GET", "/health")
    assert status == 200, f"Expected 200, got {status}"
    assert body.get("status") == "ok"
    print("  ✅ PASS")


def test_normal_charge():
    """Small charge within limits should be approved."""
    print("\n[TEST] Normal Stripe charge ($25.00)")
    status, body = make_proxied_request("POST", "/v1/charges", data={
        "amount": "2500",
        "currency": "usd",
        "description": "Widget purchase",
    })
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert "id" in body, f"Expected charge ID in response: {body}"
    print("  ✅ PASS")


def test_over_limit_blocked():
    """Charge over per-transaction limit should be blocked (auto-denied)."""
    print("\n[TEST] Over-limit charge ($75.00) — should be blocked")
    status, body = make_proxied_request("POST", "/v1/charges", data={
        "amount": "7500",
        "currency": "usd",
        "description": "Expensive purchase",
    })
    assert status == 403, f"Expected 403, got {status}: {body}"
    assert "spending_guard_blocked" in json.dumps(body)
    print("  ✅ PASS")


def test_paypal_normal():
    """PayPal order within limits."""
    print("\n[TEST] PayPal order ($30.00)")
    status, body = make_proxied_request("POST", "/v2/checkout/orders", json_data={
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": "30.00"}
        }],
    })
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert "id" in body
    print("  ✅ PASS")


def test_pii_detection():
    """Request with PII should trigger warning (action=warn allows it through)."""
    print("\n[TEST] PII detection (email + phone)")
    status, body = make_proxied_request("POST", "/v1/payment_intents", data={
        "amount": "1500",
        "currency": "usd",
        "description": "Order for john@example.com, call 555-123-4567",
    })
    # With action=warn, it should still pass through
    assert status == 200, f"Expected 200, got {status}: {body}"
    print("  ✅ PASS (PII warning logged)")


def test_audit_log():
    """Check that transactions were logged."""
    print("\n[TEST] Audit log entries")
    sys.path.insert(0, PROJECT_DIR)
    import db
    rows = db.get_recent_transactions(50)
    assert len(rows) >= 4, f"Expected at least 4 audit entries, got {len(rows)}"

    # Check there's at least one blocked entry
    blocked = [r for r in rows if r["decision"] == "blocked"]
    assert len(blocked) >= 1, "Expected at least 1 blocked transaction"

    # Check PII was detected
    pii_rows = [r for r in rows if r.get("pii_detected")]
    assert len(pii_rows) >= 1, "Expected at least 1 PII detection"

    print(f"  ✅ PASS ({len(rows)} entries, {len(blocked)} blocked, {len(pii_rows)} with PII)")


def main():
    # Clean previous audit DB
    db_path = os.path.join(PROJECT_DIR, "audit.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    print("=" * 50)
    print("E2E Test Suite — Agent Spending Guard")
    print("=" * 50)

    # Start mock server
    print("\nStarting services...")
    start_process(
        [sys.executable, "mock_server.py"],
        "mock-server",
    )

    # Start mitmdump (non-interactive proxy) with addon
    mitmdump_path = os.path.join(PROJECT_DIR, ".venv", "bin", "mitmdump")
    start_process(
        [
            mitmdump_path,
            "--mode", "regular",
            "--listen-port", str(PROXY_PORT),
            "-s", "proxy_addon.py",
            "--quiet",
        ],
        "mitmdump",
        env={"SPENDING_GUARD_NON_INTERACTIVE": "1"},
    )

    # Wait for both services
    print("\nWaiting for services...")
    if not wait_for_port(MOCK_PORT):
        print("  ❌ Mock server failed to start")
        cleanup()
        return 1

    if not wait_for_port(PROXY_PORT):
        print("  ❌ Proxy failed to start")
        cleanup()
        return 1

    print("  Both services ready.\n")

    # Run tests
    passed = 0
    failed = 0
    tests = [
        test_pass_through,
        test_normal_charge,
        test_over_limit_blocked,
        test_paypal_normal,
        test_pii_detection,
        test_audit_log,
    ]

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    cleanup()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

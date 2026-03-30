"""Simulated AI agent that makes payment API calls through the proxy."""

import argparse
import json
import requests
import time
import sys


PROXY = "http://127.0.0.1:8080"
BASE_URL = "http://127.0.0.1:9000"


def make_request(method, path, data=None, json_data=None, use_proxy=True):
    url = f"{BASE_URL}{path}"
    proxies = {"http": PROXY} if use_proxy else None
    try:
        resp = requests.request(
            method, url, data=data, json=json_data,
            proxies=proxies, timeout=10,
        )
        return resp.status_code, resp.json()
    except requests.exceptions.ConnectionError as e:
        return None, {"error": f"Connection failed: {e}"}
    except Exception as e:
        return None, {"error": str(e)}


def scenario_normal():
    """Small Stripe charge — should pass."""
    print("\n--- Scenario 1: Normal Stripe charge ($25.00) ---")
    status, body = make_request("POST", "/v1/charges", data={
        "amount": "2500",
        "currency": "usd",
        "description": "Widget purchase",
    })
    print(f"  Status: {status}")
    print(f"  Response: {json.dumps(body, indent=2)[:300]}")


def scenario_over_limit():
    """Large Stripe charge — exceeds per-transaction limit."""
    print("\n--- Scenario 2: Over-limit charge ($75.00) ---")
    status, body = make_request("POST", "/v1/charges", data={
        "amount": "7500",
        "currency": "usd",
        "description": "Expensive purchase",
    })
    print(f"  Status: {status}")
    print(f"  Response: {json.dumps(body, indent=2)[:300]}")


def scenario_paypal():
    """PayPal order — moderate amount."""
    print("\n--- Scenario 3: PayPal order ($30.00) ---")
    status, body = make_request("POST", "/v2/checkout/orders", json_data={
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                "value": "30.00",
            }
        }],
    })
    print(f"  Status: {status}")
    print(f"  Response: {json.dumps(body, indent=2)[:300]}")


def scenario_pii():
    """Stripe charge with PII in request body."""
    print("\n--- Scenario 4: Charge with PII (email + phone) ---")
    status, body = make_request("POST", "/v1/payment_intents", data={
        "amount": "1500",
        "currency": "usd",
        "description": "Order for john@example.com, call 555-123-4567",
    })
    print(f"  Status: {status}")
    print(f"  Response: {json.dumps(body, indent=2)[:300]}")


def scenario_health():
    """Non-payment endpoint — should pass through unmodified."""
    print("\n--- Scenario 5: Health check (non-payment) ---")
    status, body = make_request("GET", "/health")
    print(f"  Status: {status}")
    print(f"  Response: {json.dumps(body, indent=2)[:300]}")


SCENARIOS = {
    "normal": scenario_normal,
    "over_limit": scenario_over_limit,
    "paypal": scenario_paypal,
    "pii": scenario_pii,
    "health": scenario_health,
}


def main():
    parser = argparse.ArgumentParser(description="Agent spending simulator")
    parser.add_argument(
        "scenarios", nargs="*", default=list(SCENARIOS.keys()),
        help=f"Scenarios to run: {', '.join(SCENARIOS.keys())} (default: all)",
    )
    parser.add_argument("--no-proxy", action="store_true", help="Bypass proxy")
    args = parser.parse_args()

    if args.no_proxy:
        global PROXY
        PROXY = None

    print("=" * 50)
    print("Agent Spending Simulator")
    print(f"Target: {BASE_URL}")
    print(f"Proxy:  {PROXY or 'DISABLED'}")
    print("=" * 50)

    for name in args.scenarios:
        if name in SCENARIOS:
            SCENARIOS[name]()
        else:
            print(f"\nUnknown scenario: {name}")

    print("\n" + "=" * 50)
    print("All scenarios completed.")


if __name__ == "__main__":
    main()

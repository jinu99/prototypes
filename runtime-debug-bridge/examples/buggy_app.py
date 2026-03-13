"""Example buggy app for testing rdb — simulates a realistic debugging scenario."""

import sys
import urllib.request
import json


def fetch_data(endpoint):
    """Fetch data from an API (will go through rdb proxy)."""
    url = f"http://httpbin.org/{endpoint}"
    print(f"[app] Fetching {url}...")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        print(f"[app] Got {resp.status} from {endpoint}")
        return data


def process():
    print("[app] Step 1: fetch valid endpoint")
    data = fetch_data("get?step=1")

    print("[app] Step 2: fetch another endpoint")
    data2 = fetch_data("get?step=2")

    print("[app] Step 3: process data")
    # Simulate a bug: accessing a key that doesn't exist
    try:
        result = data["args"]["missing_key"]
    except KeyError as e:
        print(f"[app] KeyError: {e} — data['args'] keys: {list(data['args'].keys())}", file=sys.stderr)
        print("[app] FATAL: cannot proceed without required field", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    print("[app] Starting...")
    process()
    print("[app] Done.")

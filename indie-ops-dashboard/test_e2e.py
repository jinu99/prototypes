"""End-to-end verification of all dashboard features via API and HTML checks."""

import asyncio
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError


BASE = "http://localhost:8099"


def get(path):
    return json.loads(urlopen(f"{BASE}{path}", timeout=10).read())


def post(path):
    req = Request(f"{BASE}{path}", method="POST", data=b"")
    return json.loads(urlopen(req, timeout=10).read())


def get_html(path):
    return urlopen(f"{BASE}{path}", timeout=10).read().decode()


def main():
    results = []

    # 1. HTML page loads
    print("=" * 60)
    print("Indie Ops Dashboard — E2E Verification")
    print("=" * 60)

    html = get_html("/")
    ok = "Indie Ops Dashboard" in html and "metricsChart" in html and "cost-grid" in html
    results.append(("HTML dashboard loads", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] HTML dashboard loads")
    print(f"  - Contains title: {'Indie Ops Dashboard' in html}")
    print(f"  - Contains chart canvas: {'metricsChart' in html}")
    print(f"  - Contains cost grid: {'cost-grid' in html}")
    print(f"  - Contains segment bar: {'segment-bar' in html}")
    print(f"  - Contains uptime list: {'uptime-list' in html}")
    print(f"  - Contains heartbeat list: {'heartbeat-list' in html}")

    # 2. Metrics API
    data = get("/api/metrics?hours=24")
    ok = data["count"] > 2000
    results.append(("Metrics API returns 24h data", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] Metrics API: {data['count']} rows")
    if data["metrics"]:
        m = data["metrics"][0]
        print(f"  - Sample: CPU={m['cpu_percent']}%, Mem={m['memory_percent']}%, Net sent={m['net_sent_bytes']}")

    # 3. Analysis API — pattern classification
    analysis = get("/api/analysis?hours=24")
    cls = analysis["classification"]
    ok = cls["total_active_pct"] > 0 and len(cls["daily_hours"]) > 0 and len(cls["segments"]) > 0
    results.append(("Pattern analysis works", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] Pattern analysis:")
    print(f"  - Active %: {cls['total_active_pct']}%")
    print(f"  - Daily hours: {cls['daily_hours']}")
    print(f"  - Segments: {len(cls['segments'])}")

    # 4. Analysis API — cost comparison
    cost = analysis["cost_comparison"]
    ok = cost["ec2"]["monthly_cost"] > 0 and "recommendation" in cost["savings"]
    results.append(("Cost comparison works", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] Cost comparison:")
    print(f"  - EC2 monthly: ${cost['ec2']['monthly_cost']}")
    print(f"  - Lambda monthly: ${cost['lambda']['monthly_cost']}")
    print(f"  - Savings: {cost['savings']['percent']}% (${cost['savings']['monthly']})")
    print(f"  - Recommendation: {cost['savings']['recommendation'][:100]}...")

    # 5. Uptime checks
    uptime = get("/api/uptime")
    ok = len(uptime["checks"]) > 0
    results.append(("Uptime checks available", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] Uptime checks: {len(uptime['checks'])} records")
    if uptime["checks"]:
        c = uptime["checks"][0]
        print(f"  - Latest: {c['url']} → {c['status']}")

    # 6. Live uptime check
    live = post("/api/uptime/check")
    ok = len(live["results"]) > 0 and any(r["status"] == "up" for r in live["results"])
    results.append(("Live uptime check works", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] Live uptime check:")
    for r in live["results"]:
        print(f"  - {r['url']}: {r['status']} ({r.get('response_ms', 'N/A')}ms)")

    # 7. Heartbeats
    beats = get("/api/heartbeats")
    ok = len(beats["heartbeats"]) > 0
    results.append(("Heartbeat data available", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] Heartbeats: {len(beats['heartbeats'])} jobs")
    for h in beats["heartbeats"]:
        print(f"  - {h['job_name']}: {h['total_beats']}x")

    # 8. Post new heartbeat
    hb = post("/api/heartbeat/e2e-test-job")
    ok = hb["status"] == "ok" and hb["job"] == "e2e-test-job"
    results.append(("POST heartbeat works", ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] POST heartbeat: {hb}")

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

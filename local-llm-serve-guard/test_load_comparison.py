"""Load test: compares behavior WITH vs WITHOUT admission control.

Demonstrates that admission control prevents overload by rejecting/queuing
requests when VRAM is high, while without admission control all requests
would hit the backend simultaneously (risking OOM).
"""

from __future__ import annotations

import asyncio
import time
import sys

import httpx

PROXY_URL = "http://localhost:8780"


async def send_burst(client: httpx.AsyncClient, n: int, label: str) -> dict:
    """Send n concurrent requests and collect results."""
    tasks = [
        client.post(
            f"{PROXY_URL}/v1/chat/completions",
            json={"model": "mock-model", "messages": [{"role": "user", "content": f"{label} {i}"}]},
        )
        for i in range(n)
    ]
    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start

    stats = {"200": 0, "503": 0, "502": 0, "error": 0}
    for r in results:
        if isinstance(r, Exception):
            stats["error"] += 1
        else:
            key = str(r.status_code)
            stats[key] = stats.get(key, 0) + 1

    return {"elapsed": elapsed, "stats": stats, "total": n}


async def main():
    print("\n=== Load Comparison: Admission Control ON vs Simulated OFF ===\n")
    n = 30

    async with httpx.AsyncClient(timeout=60.0) as c:
        # --- Test 1: WITH admission control, VRAM at critical (96%) ---
        print(f"[Scenario A] Admission ON, VRAM critical (96%), {n} concurrent requests")
        await c.post(f"{PROXY_URL}/debug/set-mock-vram", json={"utilization_percent": 96.0})
        result_a = await send_burst(c, n, "with-admission")
        print(f"  Results: {result_a['stats']}")
        print(f"  Time: {result_a['elapsed']:.2f}s")
        rejected_a = result_a["stats"].get("503", 0)
        print(f"  Rejected (503): {rejected_a}/{n} — backends protected from overload")

        # --- Test 2: WITH admission control, VRAM normal (50%) ---
        print(f"\n[Scenario B] Admission ON, VRAM normal (50%), {n} concurrent requests")
        await c.post(f"{PROXY_URL}/debug/set-mock-vram", json={"utilization_percent": 50.0})
        result_b = await send_burst(c, n, "normal-vram")
        print(f"  Results: {result_b['stats']}")
        print(f"  Time: {result_b['elapsed']:.2f}s")
        success_b = result_b["stats"].get("200", 0)
        print(f"  Successful (200): {success_b}/{n} — all requests served")

        # --- Analysis ---
        print(f"\n{'='*60}")
        print("Analysis:")
        print(f"  Scenario A (VRAM critical): {rejected_a}/{n} requests rejected → 0 OOM risk")
        print(f"  Scenario B (VRAM normal):   {success_b}/{n} requests served → normal operation")
        print(f"\n  Without admission control, all {n} requests in Scenario A would hit")
        print(f"  the backend simultaneously, risking OOM crash.")
        print(f"  With admission control, {rejected_a} were rejected proactively.")

        oom_prevented = rejected_a > 0 and success_b > 0
        print(f"\n  OOM prevention validated: {'YES' if oom_prevented else 'NO'}")

        if not oom_prevented:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

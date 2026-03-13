"""Test VRAM admission control — simulates high VRAM to trigger queuing/rejection."""

from __future__ import annotations

import asyncio
import sys

import httpx

PROXY_URL = "http://localhost:8780"
RESULTS = []


def report(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


async def main():
    print("\n=== Admission Control Tests ===\n")

    async with httpx.AsyncClient(timeout=15.0) as c:
        # 1. Normal — VRAM at 50% (below threshold 85%)
        await c.post(f"{PROXY_URL}/debug/set-mock-vram", json={"utilization_percent": 50.0})
        r = await c.post(
            f"{PROXY_URL}/v1/chat/completions",
            json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
        )
        report("Normal VRAM (50%) — request admitted", r.status_code == 200, f"status={r.status_code}")

        # 2. Critical — VRAM at 96% (above critical 95%)
        await c.post(f"{PROXY_URL}/debug/set-mock-vram", json={"utilization_percent": 96.0})
        r = await c.post(
            f"{PROXY_URL}/v1/chat/completions",
            json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
        )
        report("Critical VRAM (96%) — request rejected", r.status_code == 503, f"status={r.status_code}")
        if r.status_code == 503:
            body = r.json()
            report(
                "Rejection message includes reason",
                "vram_critical" in body.get("error", {}).get("message", ""),
                body.get("error", {}).get("message", ""),
            )

        # 3. Between threshold and critical (90%) — should queue, then release when VRAM drops
        await c.post(f"{PROXY_URL}/debug/set-mock-vram", json={"utilization_percent": 90.0})

        async def delayed_release():
            await asyncio.sleep(1)
            await c.post(f"{PROXY_URL}/debug/set-mock-vram", json={"utilization_percent": 50.0})

        release_task = asyncio.create_task(delayed_release())
        r = await c.post(
            f"{PROXY_URL}/v1/chat/completions",
            json={"model": "mock-model", "messages": [{"role": "user", "content": "queued request"}]},
        )
        await release_task
        report(
            "Queued VRAM (90% → 50%) — request released",
            r.status_code == 200,
            f"status={r.status_code}",
        )

        # 4. Check final admission stats
        r = await c.get(f"{PROXY_URL}/health")
        data = r.json()
        stats = data["admission"]
        print(f"\n  Final stats: {stats}")
        report("Admitted count > 0", stats["admitted"] > 0)
        report("Rejected count > 0", stats["rejected"] > 0)
        report("Queued count > 0", stats["queued"] > 0)

    passed = sum(1 for _, p in RESULTS if p)
    total = len(RESULTS)
    print(f"\n{'='*50}")
    print(f"Admission tests: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""Chaos scenario execution engine.

Runs scenarios against a target URL and collects results.
"""

import time
import uuid
import httpx
from dataclasses import dataclass, field


@dataclass
class RequestResult:
    seq: int
    status_code: int
    elapsed_ms: float
    idempotency_key: str = ""
    error: str = ""


@dataclass
class ScenarioResult:
    name: str
    description: str
    type: str = ""
    verdict: str = ""  # PASS or FAIL
    reason: str = ""
    requests: list[RequestResult] = field(default_factory=list)
    total_ms: float = 0.0


def _send(
    client: httpx.Client,
    target: str,
    payload: dict,
    headers: dict | None = None,
) -> RequestResult:
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    try:
        start = time.monotonic()
        resp = client.post(target, json=payload, headers=hdrs, timeout=30.0)
        elapsed = (time.monotonic() - start) * 1000
        return RequestResult(
            seq=0,
            status_code=resp.status_code,
            elapsed_ms=round(elapsed, 1),
            idempotency_key=hdrs.get("Idempotency-Key", ""),
        )
    except Exception as e:
        return RequestResult(seq=0, status_code=0, elapsed_ms=0, error=str(e))


def run_duplicate(
    target: str,
    payload: dict,
    count: int = 3,
    headers: dict | None = None,
) -> ScenarioResult:
    """Send the same request N times. PASS if all return 2xx."""
    result = ScenarioResult(
        name="duplicate",
        description=f"Send identical payload {count} times to test idempotency",
        type="duplicate",
    )
    idem_key = str(uuid.uuid4())
    hdrs = {"Idempotency-Key": idem_key}
    if headers:
        hdrs.update(headers)

    start = time.monotonic()
    with httpx.Client() as client:
        for i in range(count):
            rr = _send(client, target, payload, hdrs)
            rr.seq = i
            rr.idempotency_key = idem_key
            result.requests.append(rr)
    result.total_ms = round((time.monotonic() - start) * 1000, 1)

    all_ok = all(200 <= r.status_code < 300 for r in result.requests)
    result.verdict = "PASS" if all_ok else "FAIL"
    if not all_ok:
        fails = [r for r in result.requests if not (200 <= r.status_code < 300)]
        result.reason = f"{len(fails)}/{count} requests returned non-2xx"
    else:
        result.reason = f"All {count} duplicate requests returned 2xx"
    return result


def run_delay(
    target: str,
    payload: dict,
    delay_seconds: float = 2.0,
    headers: dict | None = None,
) -> ScenarioResult:
    """Send request after a delay. PASS if response is 2xx."""
    result = ScenarioResult(
        name="delay",
        description=f"Send payload after {delay_seconds}s delay",
        type="delay",
    )
    hdrs = dict(headers) if headers else {}

    start = time.monotonic()
    time.sleep(delay_seconds)
    with httpx.Client() as client:
        rr = _send(client, target, payload, hdrs)
        rr.seq = 0
        result.requests.append(rr)
    result.total_ms = round((time.monotonic() - start) * 1000, 1)

    ok = 200 <= rr.status_code < 300
    result.verdict = "PASS" if ok else "FAIL"
    result.reason = (
        f"Response {rr.status_code} after {delay_seconds}s delay"
        if ok
        else f"Non-2xx ({rr.status_code}) after delay"
    )
    return result


def run_reorder(
    target: str,
    payloads: list[dict],
    headers: dict | None = None,
) -> ScenarioResult:
    """Send payloads in reverse order. PASS if all return 2xx."""
    result = ScenarioResult(
        name="reorder",
        description=f"Send {len(payloads)} payloads in reverse order",
        type="reorder",
    )
    hdrs = dict(headers) if headers else {}
    reversed_payloads = list(reversed(payloads))

    start = time.monotonic()
    with httpx.Client() as client:
        for i, p in enumerate(reversed_payloads):
            rr = _send(client, target, p, hdrs)
            rr.seq = i
            result.requests.append(rr)
    result.total_ms = round((time.monotonic() - start) * 1000, 1)

    all_ok = all(200 <= r.status_code < 300 for r in result.requests)
    result.verdict = "PASS" if all_ok else "FAIL"
    if all_ok:
        result.reason = "All reversed-order requests returned 2xx"
    else:
        fails = [r for r in result.requests if not (200 <= r.status_code < 300)]
        result.reason = f"{len(fails)}/{len(payloads)} requests returned non-2xx"
    return result


RUNNERS = {
    "duplicate": run_duplicate,
    "delay": run_delay,
    "reorder": run_reorder,
}

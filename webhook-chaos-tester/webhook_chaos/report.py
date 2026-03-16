"""Generate Markdown and JSON reports from scenario results."""

import json
from datetime import datetime
from webhook_chaos.engine import ScenarioResult

SCENARIO_TYPES = {"duplicate", "delay", "reorder"}


def to_markdown(results: list[ScenarioResult], target: str) -> str:
    lines = [
        "# Webhook Chaos Test Report",
        "",
        f"**Target:** `{target}`",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Scenarios:** {len(results)}",
        "",
    ]

    passed = sum(1 for r in results if r.verdict == "PASS")
    failed = len(results) - passed
    lines.append(f"## Summary: {passed} PASS / {failed} FAIL")
    lines.append("")

    for r in results:
        icon = "✅" if r.verdict == "PASS" else "❌"
        lines.append(f"### {icon} {r.name}")
        lines.append("")
        lines.append(f"- **Type:** {r.type or r.name}")
        lines.append(f"- **Description:** {r.description}")
        lines.append(f"- **Verdict:** **{r.verdict}**")
        lines.append(f"- **Reason:** {r.reason}")
        lines.append(f"- **Duration:** {r.total_ms}ms")
        lines.append(f"- **Requests:** {len(r.requests)}")
        lines.append("")

        lines.append("| # | Status | Time (ms) | Error |")
        lines.append("|---|--------|-----------|-------|")
        for req in r.requests:
            err = req.error if req.error else "-"
            lines.append(f"| {req.seq} | {req.status_code} | {req.elapsed_ms} | {err} |")
        lines.append("")

    return "\n".join(lines)


def to_json(results: list[ScenarioResult], target: str) -> str:
    data = {
        "target": target,
        "date": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.verdict == "PASS"),
            "failed": sum(1 for r in results if r.verdict == "FAIL"),
        },
        "scenarios": [
            {
                "name": r.name,
                "description": r.description,
                "verdict": r.verdict,
                "reason": r.reason,
                "total_ms": r.total_ms,
                "requests": [
                    {
                        "seq": req.seq,
                        "status_code": req.status_code,
                        "elapsed_ms": req.elapsed_ms,
                        "error": req.error,
                    }
                    for req in r.requests
                ],
            }
            for r in results
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)

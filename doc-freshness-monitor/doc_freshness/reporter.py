"""Generate JSON and Markdown reports."""

import json
from datetime import datetime


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def to_json(records: list[dict]) -> str:
    """Generate JSON report."""
    return json.dumps(records, indent=2, default=_serialize)


def to_markdown(records: list[dict]) -> str:
    """Generate Markdown report."""
    if not records:
        return "# Doc Freshness Report\n\nNo stale documentation found.\n"

    lines = [
        "# Doc Freshness Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Total doc-symbol pairs analyzed: {len(records)}",
        "",
        "## Results",
        "",
        "| Score | Doc File | Symbol | Kind | Code Last Changed | Commit # |",
        "|------:|:---------|:-------|:-----|:------------------|:---------|",
    ]

    for rec in records:
        score = rec.get("staleness_score", 0)
        doc = rec["doc_path"]
        symbol = rec["symbol"]
        kind = rec["kind"]
        code_mod = rec.get("code_modified")
        code_date = code_mod.strftime("%Y-%m-%d") if code_mod else "N/A"
        commits = rec.get("commit_count", 0)

        # Score indicator
        if score >= 70:
            indicator = f"**{score}** \u26a0\ufe0f"
        elif score >= 40:
            indicator = f"**{score}**"
        else:
            indicator = str(score)

        lines.append(
            f"| {indicator} | {doc} | `{symbol}` | {kind} | {code_date} | {commits} |"
        )

    # Summary
    stale = [r for r in records if r.get("staleness_score", 0) > 0]
    high = [r for r in records if r.get("staleness_score", 0) >= 70]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- **Total pairs**: {len(records)}",
        f"- **Stale (score > 0)**: {len(stale)}",
        f"- **High staleness (score >= 70)**: {len(high)}",
    ])

    return "\n".join(lines) + "\n"


def format_scan_table(doc_symbols: dict[str, list[dict]]) -> str:
    """Format symbol scan results as a readable table."""
    lines = [
        "# Symbol Scan Results",
        "",
        "| Doc File | Symbol | Kind | Line |",
        "|:---------|:-------|:-----|-----:|",
    ]
    total = 0
    for doc_path, symbols in sorted(doc_symbols.items()):
        for sym in symbols:
            lines.append(
                f"| {doc_path} | `{sym['symbol']}` | {sym['kind']} | {sym['line']} |"
            )
            total += 1

    lines.extend(["", f"Total: {total} symbol references found across {len(doc_symbols)} doc files."])
    return "\n".join(lines) + "\n"

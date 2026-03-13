"""Terminal and JSON report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


STATUS_COLORS = {"PASS": "green", "WARN": "yellow", "FAIL": "red"}


def print_terminal_report(results: list[dict[str, Any]], model: str, console: Console | None = None):
    console = console or Console()

    console.print()
    console.print(Panel(f"[bold]LLM Quality Probe Report[/bold]\nModel: {model}", style="blue"))
    console.print()

    # Summary table
    table = Table(title="Probe Results", show_header=True, header_style="bold")
    table.add_column("Probe", style="cyan", min_width=22)
    table.add_column("Status", justify="center", min_width=8)
    table.add_column("Key Metric", min_width=30)

    for r in results:
        probe = r["probe"]
        status = r["status"]
        color = STATUS_COLORS.get(status, "white")
        status_str = f"[{color}]{status}[/{color}]"

        if probe == "structured_output":
            s = r["summary"]
            metric = f"Parse: {s['parse_rate']}% | Schema: {s['schema_rate']}%"
        elif probe == "multiturn_stability":
            s = r["summary"]
            metric = f"Stability: {s['stability_rate']}% ({s['stable_turns']}/{s['total_turns']} turns)"
        elif probe == "output_efficiency":
            s = r["summary"]
            metric = f"Thinking overhead: {s['thinking_overhead_pct']}%"
        else:
            metric = ""

        table.add_row(probe, status_str, metric)

    console.print(table)
    console.print()

    # Detailed sections
    for r in results:
        _print_probe_details(r, console)

    # Overall status
    statuses = [r["status"] for r in results]
    if all(s == "PASS" for s in statuses):
        overall = "PASS"
    elif any(s == "FAIL" for s in statuses):
        overall = "FAIL"
    else:
        overall = "WARN"

    color = STATUS_COLORS[overall]
    console.print(Panel(f"[bold {color}]Overall: {overall}[/bold {color}]", style=color))
    console.print()


def _print_probe_details(result: dict, console: Console):
    probe = result["probe"]

    if probe == "structured_output":
        s = result["summary"]
        console.print(f"[bold cyan]Structured Output Details[/bold cyan]")
        console.print(f"  Tests: {s['total_tests']} | Parse OK: {s['parse_success']} | Schema OK: {s['schema_compliant']}")
        console.print(f"  Extra fields (not in schema): {s['hallucinated_fields_total']}")
        if result.get("details"):
            for d in result["details"]:
                icon = "[green]OK[/green]" if d["parse_success"] else "[red]FAIL[/red]"
                console.print(f"    {d['format'].upper()} {icon} — schema: {'OK' if d['schema_compliant'] else 'FAIL'}", highlight=False)
                if d["type_errors"]:
                    console.print(f"      Type errors: {d['type_errors']}")
                if d["missing_fields"]:
                    console.print(f"      Missing: {d['missing_fields']}")
        console.print()

    elif probe == "multiturn_stability":
        s = result["summary"]
        console.print(f"[bold cyan]Multi-turn Stability Details[/bold cyan]")
        if s["collapse_points"]:
            console.print(f"  Collapse detected at:")
            for cp in s["collapse_points"]:
                console.print(f"    Topic: {cp['topic']}, Turn {cp['turn']}: {', '.join(cp['issues'])}")
        else:
            console.print(f"  No collapse detected across {s['total_turns']} turns")
        console.print()

    elif probe == "output_efficiency":
        s = result["summary"]
        console.print(f"[bold cyan]Output Efficiency Details[/bold cyan]")
        console.print(f"  Thinking ON tokens: {s['thinking_on_tokens']}")
        console.print(f"  Thinking OFF tokens: {s['thinking_off_tokens']}")
        console.print(f"  Overhead: {s['thinking_overhead_pct']}%")
        console.print(f"  Most efficient config: {s['most_efficient']}")
        console.print(f"  Least efficient config: {s['least_efficient']}")
        console.print()


def save_json_report(results: list[dict], model: str, output_path: Path):
    report = {
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "probes": results,
        "overall": _compute_overall(results),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return output_path


def _compute_overall(results: list[dict]) -> str:
    statuses = [r["status"] for r in results]
    if all(s == "PASS" for s in statuses):
        return "PASS"
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    return "WARN"

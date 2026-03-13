"""CLI entry point for llm-qual-probe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from llm_qual_probe.client import LLMClient
from llm_qual_probe.probes import structured, multiturn, efficiency
from llm_qual_probe.reporter import print_terminal_report, save_json_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="llm-qual-probe",
        description="Probe local LLM quality: structured output, multi-turn stability, token efficiency",
    )
    parser.add_argument(
        "endpoint",
        help="OpenAI-compatible API endpoint (e.g., http://localhost:11434)",
    )
    parser.add_argument(
        "--model", "-m",
        default="",
        help="Model name (auto-detected if omitted)",
    )
    parser.add_argument(
        "--output", "-o",
        default="report.json",
        help="JSON report output path (default: report.json)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock responses instead of real LLM (for testing)",
    )
    parser.add_argument(
        "--probes", "-p",
        default="all",
        help="Comma-separated probe list: structured,multiturn,efficiency (default: all)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    console = Console()

    # Initialize client
    client = LLMClient(base_url=args.endpoint, model=args.model, mock=args.mock)

    # Detect model
    if not client.model:
        console.print("[dim]Detecting model...[/dim]")
        try:
            model = client.detect_model()
            if model:
                console.print(f"[green]Detected model: {model}[/green]")
            else:
                console.print("[yellow]No model detected, using default[/yellow]")
                client.model = "unknown"
        except Exception as e:
            if args.mock:
                client.model = "mock-model"
            else:
                console.print(f"[red]Failed to connect to {args.endpoint}: {e}[/red]")
                console.print("[dim]Tip: Use --mock to test without a running LLM server[/dim]")
                sys.exit(1)

    console.print(f"\n[bold]Running LLM Quality Probe against {client.model}[/bold]\n")

    # Select probes
    probe_names = args.probes.split(",") if args.probes != "all" else ["structured", "multiturn", "efficiency"]

    results = []
    probe_map = {
        "structured": ("Structured Output", structured.run),
        "multiturn": ("Multi-turn Stability", multiturn.run),
        "efficiency": ("Output Efficiency", efficiency.run),
    }

    for name in probe_names:
        name = name.strip()
        if name not in probe_map:
            console.print(f"[yellow]Unknown probe: {name}, skipping[/yellow]")
            continue
        label, fn = probe_map[name]
        console.print(f"[cyan]Running {label} probe...[/cyan]")
        try:
            result = fn(client)
            results.append(result)
            color = {"PASS": "green", "WARN": "yellow", "FAIL": "red"}.get(result["status"], "white")
            console.print(f"  [{color}]{result['status']}[/{color}]\n")
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]\n")
            results.append({"probe": name, "status": "FAIL", "summary": {"error": str(e)}, "details": []})

    # Output
    print_terminal_report(results, client.model, console)

    output_path = Path(args.output)
    saved = save_json_report(results, client.model, output_path)
    console.print(f"[dim]JSON report saved to: {saved}[/dim]")


if __name__ == "__main__":
    main()

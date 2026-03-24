"""CLI entry point for SQL Query Performance Advisor."""

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel

from sql_perf_advisor.fingerprint import detect_n_plus_1
from sql_perf_advisor.explain_parser import analyze_explain
from sql_perf_advisor.reporter import (
    rank_queries,
    print_top_n_report,
    print_n_plus_1_report,
    print_explain_report,
)

console = Console()


@click.group()
def cli():
    """SQL Query Performance Advisor — Offline pg_stat_statements analyzer."""
    pass


@cli.command()
@click.option("--input", "-i", "input_file", required=True, help="Path to snapshot JSON file")
@click.option("--top-n", "-n", default=10, help="Number of top costly queries to show")
@click.option("--call-threshold", default=1000, help="Min calls to flag as N+1 candidate")
def analyze(input_file: str, top_n: int, call_threshold: int):
    """Analyze a pg_stat_statements snapshot for performance issues."""
    try:
        with open(input_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON: {e}[/red]")
        sys.exit(1)

    statements = data.get("pg_stat_statements", [])
    explain_plans = data.get("explain_plans", [])
    snapshot_time = data.get("snapshot_time", "unknown")

    if not statements:
        console.print("[red]Error: No pg_stat_statements data found in input[/red]")
        sys.exit(1)

    console.print(Panel(
        f"[bold]SQL Query Performance Advisor[/bold]\n"
        f"Snapshot: {snapshot_time} | Queries: {len(statements)} | "
        f"EXPLAIN plans: {len(explain_plans)}",
        style="blue",
    ))

    # 1. Top-N costly queries
    console.print("\n[bold cyan]═══ Top-N Costly Queries ═══[/bold cyan]\n")
    ranked = rank_queries(statements, top_n)
    print_top_n_report(ranked)

    # 2. N+1 pattern detection
    console.print("\n[bold cyan]═══ N+1 Pattern Detection ═══[/bold cyan]\n")
    n_plus_1 = detect_n_plus_1(statements, call_threshold)
    print_n_plus_1_report(n_plus_1)

    # 3. EXPLAIN plan analysis
    if explain_plans:
        console.print("\n[bold cyan]═══ EXPLAIN Plan Analysis ═══[/bold cyan]\n")
        total_findings = 0
        for entry in explain_plans:
            plan = entry.get("plan", {})
            query = entry.get("query", "")
            findings = analyze_explain(plan, query)
            total_findings += len(findings)
            print_explain_report(findings, entry)

        console.print(f"\n  [bold]Total anti-patterns found: {total_findings}[/bold]")
    else:
        console.print("\n[dim]No EXPLAIN plans provided — skipping plan analysis.[/dim]")

    # Summary
    console.print("\n" + "═" * 60)
    issues = len(n_plus_1) + (total_findings if explain_plans else 0)
    if issues > 0:
        console.print(f"[bold red]⚠ {issues} performance issue(s) detected.[/bold red]")
    else:
        console.print("[bold green]✓ No performance issues detected.[/bold green]")


def main():
    cli()


if __name__ == "__main__":
    main()

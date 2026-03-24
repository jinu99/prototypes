"""Top-N cost query reporting and result formatting."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


console = Console()


def rank_queries(statements: list[dict], top_n: int = 10) -> list[dict]:
    """Rank queries by total_exec_time * calls (total cost impact)."""
    ranked = []
    for stmt in statements:
        calls = stmt.get("calls", 0)
        total_time = stmt.get("total_exec_time", 0)
        cost_score = total_time * calls
        ranked.append({
            **stmt,
            "cost_score": cost_score,
            "cache_hit_ratio": _cache_ratio(stmt),
        })
    return sorted(ranked, key=lambda x: x["cost_score"], reverse=True)[:top_n]


def print_top_n_report(ranked: list[dict]):
    """Print the Top-N cost queries as a rich table."""
    table = Table(title="Top-N Costly Queries (by total_exec_time × calls)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Query", max_width=60)
    table.add_column("Calls", justify="right")
    table.add_column("Total Time (ms)", justify="right")
    table.add_column("Mean (ms)", justify="right")
    table.add_column("Cost Score", justify="right", style="bold red")
    table.add_column("Cache Hit %", justify="right")

    for i, q in enumerate(ranked, 1):
        query_display = q["query"][:57] + "..." if len(q["query"]) > 60 else q["query"]
        table.add_row(
            str(i),
            query_display,
            f"{q['calls']:,}",
            f"{q['total_exec_time']:,.1f}",
            f"{q['mean_exec_time']:,.2f}",
            f"{q['cost_score']:,.0f}",
            f"{q['cache_hit_ratio']:.1f}%",
        )
    console.print(table)


def print_n_plus_1_report(patterns: list[dict]):
    """Print N+1 detection results."""
    if not patterns:
        console.print(Panel("[green]No N+1 patterns detected.[/green]", title="N+1 Detection"))
        return

    console.print(Panel(
        f"[bold red]Found {len(patterns)} N+1 pattern(s)[/bold red]",
        title="N+1 Detection",
    ))

    for i, p in enumerate(patterns, 1):
        severity_color = "red" if p["severity"] == "HIGH" else "yellow"
        console.print(f"\n[{severity_color}]#{i} [{p['severity']}] {p['type']}[/{severity_color}]")
        console.print(f"  Total calls: {p['total_calls']:,} | Total time: {p['total_time_ms']:,.1f} ms")

        if "parent" in p:
            console.print(f"  Parent: [dim]{p['parent']['query']}[/dim]")
            console.print(f"    calls={p['parent']['calls']:,}, time={p['parent']['total_exec_time']:,.1f}ms")
            console.print(f"  Child:  [dim]{p['child']['query']}[/dim]")
            console.print(f"    calls={p['child']['calls']:,}, time={p['child']['total_exec_time']:,.1f}ms")
        elif "query" in p:
            console.print(f"  Query: [dim]{p['query']['query']}[/dim]")
            console.print(f"    calls={p['query']['calls']:,}, time={p['query']['total_exec_time']:,.1f}ms")

        console.print(f"  [green]Suggestion:[/green] {p['suggestion']}")


def print_explain_report(findings: list, explain_entry: dict):
    """Print EXPLAIN analysis findings for a single query."""
    query = explain_entry.get("query", "unknown")
    queryid = explain_entry.get("queryid", "?")

    if not findings:
        console.print(f"  [green]✓[/green] Query {queryid}: No anti-patterns found")
        return

    console.print(f"\n  [bold]Query {queryid}:[/bold] [dim]{query[:80]}[/dim]")
    for f in findings:
        severity_color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "blue"}.get(f.severity, "white")
        console.print(f"    [{severity_color}][{f.severity}] {f.rule}[/{severity_color}]")
        console.print(f"      {f.detail}")
        console.print(f"      [green]→ {f.suggestion}[/green]")


def _cache_ratio(stmt: dict) -> float:
    hit = stmt.get("shared_blks_hit", 0)
    read = stmt.get("shared_blks_read", 0)
    total = hit + read
    return (hit / total * 100) if total > 0 else 100.0

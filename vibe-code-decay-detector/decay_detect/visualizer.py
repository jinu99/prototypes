"""Rich-based terminal visualization for architecture metrics trends."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from .storage import CommitMetrics, RevertPattern


console = Console()

# Block characters for bar charts
BLOCKS = " ▏▎▍▌▋▊▉█"


def _bar(value: float, max_val: float, width: int = 30) -> str:
    """Create a bar chart string."""
    if max_val <= 0:
        return ""
    ratio = min(value / max_val, 1.0)
    full_blocks = int(ratio * width)
    remainder = (ratio * width) - full_blocks
    partial_idx = int(remainder * 8)
    bar = "█" * full_blocks
    if partial_idx > 0 and full_blocks < width:
        bar += BLOCKS[partial_idx]
    return bar


def _trend_arrow(values: list[float], window: int = 5) -> str:
    """Show trend arrow based on recent values."""
    if len(values) < 2:
        return ""
    recent = values[-window:]
    if len(recent) < 2:
        return ""
    diff = recent[-1] - recent[0]
    if diff > 0:
        return " [red]↑[/red]"
    elif diff < 0:
        return " [green]↓[/green]"
    return " [dim]→[/dim]"


def display_coupling_trend(metrics: list[CommitMetrics]):
    """Display edge count (coupling) trend as a bar chart."""
    if not metrics:
        console.print("[dim]No metrics data to display.[/dim]")
        return

    max_edges = max(m.edge_count for m in metrics) if metrics else 1
    edge_values = [m.edge_count for m in metrics]
    trend = _trend_arrow(edge_values)

    console.print()
    console.print(
        Panel(f"[bold]Module Coupling (Edge Count){trend}[/bold]",
              style="blue", expand=False)
    )

    # Show last 30 commits max for readability
    display = metrics[-30:]
    for m in display:
        bar = _bar(m.edge_count, max_edges)
        label = f"[dim]{m.commit_hash[:7]}[/dim]"
        console.print(f"  {label} [blue]{bar}[/blue] {m.edge_count}")


def display_cyclic_deps_trend(metrics: list[CommitMetrics]):
    """Display cyclic dependency count trend."""
    if not metrics:
        return

    max_cycles = max(m.cyclic_dep_count for m in metrics) if metrics else 1
    if max_cycles == 0:
        console.print()
        console.print("[green]  No cyclic dependencies detected.[/green]")
        return

    cycle_values = [m.cyclic_dep_count for m in metrics]
    trend = _trend_arrow(cycle_values)

    console.print()
    console.print(
        Panel(f"[bold]Cyclic Dependencies{trend}[/bold]",
              style="red", expand=False)
    )

    display = metrics[-30:]
    for m in display:
        if m.cyclic_dep_count > 0:
            bar = _bar(m.cyclic_dep_count, max_cycles)
            label = f"[dim]{m.commit_hash[:7]}[/dim]"
            console.print(f"  {label} [red]{bar}[/red] {m.cyclic_dep_count}")


def display_churn_trend(metrics: list[CommitMetrics]):
    """Display file churn rate trend."""
    if not metrics:
        return

    churn_values = [m.churn_additions + m.churn_deletions for m in metrics]
    max_churn = max(churn_values) if churn_values else 1
    trend = _trend_arrow(churn_values)

    console.print()
    console.print(
        Panel(f"[bold]Code Churn (lines changed){trend}[/bold]",
              style="yellow", expand=False)
    )

    display = metrics[-30:]
    for m in display:
        total = m.churn_additions + m.churn_deletions
        bar = _bar(total, max_churn)
        label = f"[dim]{m.commit_hash[:7]}[/dim]"
        adds = f"[green]+{m.churn_additions}[/green]"
        dels = f"[red]-{m.churn_deletions}[/red]"
        console.print(f"  {label} [yellow]{bar}[/yellow] {adds} {dels}")


def display_revert_patterns(patterns: list[RevertPattern]):
    """Display detected commit-revert patterns."""
    if not patterns:
        console.print()
        console.print("[green]  No commit-revert patterns detected.[/green]")
        return

    console.print()
    table = Table(title="Commit-Revert Patterns Detected", style="magenta")
    table.add_column("File", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Detail", style="white")

    for p in patterns:
        table.add_row(p.file_path, p.pattern_type, p.detail)

    console.print(table)


def display_warnings(metrics: list[CommitMetrics], window: int = 0):
    """Display threshold-based warnings about metric trends."""
    if len(metrics) < 4:
        return

    # Auto-size window: use half the commits, minimum 3
    if window <= 0:
        window = max(3, len(metrics) // 2)

    recent = metrics[-window:]
    older = metrics[:-window] if len(metrics) > window else metrics[:max(1, len(metrics) // 3)]

    warnings = []

    # Coupling trend
    recent_avg_edges = sum(m.edge_count for m in recent) / len(recent)
    older_avg_edges = sum(m.edge_count for m in older) / len(older) if older else 0
    if older_avg_edges > 0:
        pct_change = ((recent_avg_edges - older_avg_edges) / older_avg_edges) * 100
        if pct_change > 10:
            warnings.append(
                f"[red bold]WARNING:[/red bold] Coupling increased by "
                f"{pct_change:.0f}% over the last {window} commits "
                f"(avg {older_avg_edges:.0f} → {recent_avg_edges:.0f} edges)"
            )

    # Churn trend
    recent_avg_churn = sum(
        m.churn_additions + m.churn_deletions for m in recent
    ) / len(recent)
    older_avg_churn = sum(
        m.churn_additions + m.churn_deletions for m in older
    ) / len(older) if older else 0
    if older_avg_churn > 0:
        pct_change = ((recent_avg_churn - older_avg_churn) / older_avg_churn) * 100
        if pct_change > 30:
            warnings.append(
                f"[red bold]WARNING:[/red bold] Code churn increased by "
                f"{pct_change:.0f}% over the last {window} commits"
            )

    # Cyclic deps
    recent_cycles = sum(m.cyclic_dep_count for m in recent[-5:])
    if recent_cycles > 0:
        warnings.append(
            f"[yellow bold]NOTICE:[/yellow bold] {recent_cycles} cyclic "
            f"dependencies detected in the last 5 commits"
        )

    if warnings:
        console.print()
        console.print(Panel("[bold]Architecture Health Warnings[/bold]",
                            style="red", expand=False))
        for w in warnings:
            console.print(f"  {w}")
    else:
        console.print()
        console.print("[green]  Architecture metrics look healthy.[/green]")

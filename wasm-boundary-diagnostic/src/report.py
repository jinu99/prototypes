"""Terminal report renderer using Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .cost_model import CostLevel, FunctionCost
from .recommender import Recommendation

COST_COLORS = {
    CostLevel.ZERO: "green",
    CostLevel.LOW: "cyan",
    CostLevel.MEDIUM: "yellow",
    CostLevel.HIGH: "red",
}

COST_ICONS = {
    CostLevel.ZERO: "●",
    CostLevel.LOW: "●",
    CostLevel.MEDIUM: "▲",
    CostLevel.HIGH: "■",
}


def render_report(
    file_path: str,
    results: list[FunctionCost],
    recommendations: dict[str, list[Recommendation]],
    console: Console | None = None,
) -> None:
    """Render the full diagnostic report to the terminal."""
    console = console or Console()

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]WASM Boundary Diagnostic Report[/bold]\n"
            f"[dim]{file_path}[/dim]",
            border_style="blue",
        )
    )

    # Summary stats
    _render_summary(results, console)

    # Function details table
    _render_function_table(results, console)

    # Detailed analysis for costly functions
    _render_details(results, recommendations, console)

    # Optimization recommendations grouped
    _render_recommendations(recommendations, console)

    console.print()


def _render_summary(results: list[FunctionCost], console: Console) -> None:
    """Render the summary section."""
    exports = [r for r in results if r.function.kind == "export"]
    imports = [r for r in results if r.function.kind == "import"]

    counts = {level: 0 for level in CostLevel}
    for r in results:
        counts[r.overall] += 1

    table = Table(title="Summary", show_header=False, border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total boundary functions", str(len(results)))
    table.add_row("  Exports (JS → WASM)", str(len(exports)))
    table.add_row("  Imports (WASM → JS)", str(len(imports)))
    table.add_row("", "")

    for level in CostLevel:
        color = COST_COLORS[level]
        icon = COST_ICONS[level]
        table.add_row(
            f"  {icon} {level.value.upper()} cost",
            f"[{color}]{counts[level]}[/{color}]",
        )

    console.print(table)
    console.print()


def _render_function_table(results: list[FunctionCost], console: Console) -> None:
    """Render the function overview table."""
    table = Table(
        title="Boundary Functions (sorted by cost)",
        border_style="dim",
    )
    table.add_column("Cost", justify="center", width=8)
    table.add_column("Score", justify="right", width=5)
    table.add_column("Kind", width=8)
    table.add_column("Function", min_width=20)
    table.add_column("Parameters")
    table.add_column("Return")

    for r in results:
        color = COST_COLORS[r.overall]
        icon = COST_ICONS[r.overall]

        param_parts = []
        for pc in r.param_costs:
            pc_color = COST_COLORS[pc.level]
            param_parts.append(f"[{pc_color}]{pc.param.name}: {pc.param.inferred_type}[/{pc_color}]")

        ret_color = COST_COLORS[r.return_cost]

        table.add_row(
            f"[{color}]{icon} {r.overall.value}[/{color}]",
            str(r.total_score),
            r.function.kind,
            f"[bold]{r.function.name}[/bold]",
            ", ".join(param_parts) if param_parts else "[dim]none[/dim]",
            f"[{ret_color}]{r.function.return_type}[/{ret_color}]",
        )

    console.print(table)
    console.print()


def _render_details(
    results: list[FunctionCost],
    recommendations: dict[str, list[Recommendation]],
    console: Console,
) -> None:
    """Render detailed analysis for medium/high cost functions."""
    costly = [r for r in results if r.overall in (CostLevel.MEDIUM, CostLevel.HIGH)]
    if not costly:
        console.print("[green]No high-cost boundary functions found![/green]")
        return

    console.print(
        Panel("[bold]Detailed Analysis — Medium/High Cost Functions[/bold]", border_style="yellow")
    )

    for r in costly:
        color = COST_COLORS[r.overall]
        header = Text()
        header.append(f"{COST_ICONS[r.overall]} ", style=color)
        header.append(r.function.name, style=f"bold {color}")
        header.append(f"  ({r.function.kind}, score: {r.total_score})", style="dim")

        lines: list[str] = []
        lines.append(f"  Line {r.function.line_number} in source\n")

        # Parameters
        for pc in r.param_costs:
            pc_color = COST_COLORS[pc.level]
            marker_str = ""
            if pc.param.cost_markers:
                marker_str = f" [dim](via {', '.join(pc.param.cost_markers)})[/dim]"
            lines.append(
                f"  [{pc_color}]{COST_ICONS[pc.level]}[/{pc_color}] "
                f"param [bold]{pc.param.name}[/bold]: {pc.param.inferred_type} — {pc.reason}{marker_str}"
            )

        # Return
        ret_color = COST_COLORS[r.return_cost]
        lines.append(
            f"  [{ret_color}]{COST_ICONS[r.return_cost]}[/{ret_color}] "
            f"return: {r.function.return_type} — {r.return_reason}"
        )

        console.print(header)
        for line in lines:
            console.print(line)
        console.print()


def _render_recommendations(
    recommendations: dict[str, list[Recommendation]],
    console: Console,
) -> None:
    """Render optimization recommendations grouped by pattern to reduce duplication."""
    if not recommendations:
        return

    console.print(
        Panel("[bold]Optimization Recommendations[/bold]", border_style="green")
    )

    # Group by recommendation pattern, listing affected functions
    pattern_to_funcs: dict[str, list[str]] = {}
    pattern_to_rec: dict[str, Recommendation] = {}
    for func_name, recs in recommendations.items():
        for rec in recs:
            if rec.pattern not in pattern_to_funcs:
                pattern_to_funcs[rec.pattern] = []
                pattern_to_rec[rec.pattern] = rec
            pattern_to_funcs[rec.pattern].append(func_name)

    for i, (pattern, rec) in enumerate(pattern_to_rec.items(), 1):
        funcs = pattern_to_funcs[pattern]
        func_list = ", ".join(f"[bold]{f}[/bold]" for f in funcs)
        console.print(f"  {i}. [bold cyan]{rec.title}[/bold cyan]")
        console.print(f"     {rec.description}")
        console.print(f"     [dim]Applies when: {rec.applies_when}[/dim]")
        console.print(f"     Affected: {func_list}")
        console.print()

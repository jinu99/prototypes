"""Generate terminal performance comparison reports."""

from rich.console import Console
from rich.table import Table
from rich.text import Text

from perf_verify.benchmarker import BenchResult

console = Console()

THRESHOLD_DEFAULT = 2.0  # 2x slowdown


def print_changed_functions(functions: list[dict]):
    """Print a table of changed functions."""
    table = Table(title="Changed Functions")
    table.add_column("Function", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Lines", style="dim")

    for f in functions:
        table.add_row(
            f["name"],
            f["filepath"],
            f"{f['start_line']}-{f['end_line']}",
        )

    console.print(table)


def print_comparison_report(
    comparisons: list[dict],
    threshold: float = THRESHOLD_DEFAULT,
) -> bool:
    """Print before/after comparison table.

    Returns True if any regression exceeds threshold.
    """
    table = Table(title="Performance Comparison", show_lines=True)
    table.add_column("Function", style="cyan", no_wrap=True)
    table.add_column("Before\n(ms)", justify="right")
    table.add_column("After\n(ms)", justify="right")
    table.add_column("Ratio", justify="right")
    table.add_column("Mem Δ\n(KB)", justify="right")
    table.add_column("Status", justify="center")

    has_regression = False

    for comp in comparisons:
        before: BenchResult = comp["before"]
        after: BenchResult = comp["after"]

        if before.error or after.error:
            table.add_row(
                comp["name"],
                _fmt_error(before), _fmt_error(after),
                "-", "-",
                Text("⚠ ERROR", style="yellow"),
            )
            continue

        if before.avg_time_ms == 0:
            ratio = float("inf") if after.avg_time_ms > 0 else 1.0
        else:
            ratio = after.avg_time_ms / before.avg_time_ms

        mem_delta = after.peak_memory_kb - before.peak_memory_kb

        if ratio >= threshold:
            status = Text(f"⚠ {ratio:.1f}x SLOWER", style="bold red")
            has_regression = True
        elif ratio <= 1 / threshold:
            status = Text(f"✓ {1/ratio:.1f}x FASTER", style="bold green")
        else:
            status = Text("✓ OK", style="green")

        table.add_row(
            comp["name"],
            f"{before.avg_time_ms:.2f}",
            f"{after.avg_time_ms:.2f}",
            f"{ratio:.1f}x",
            f"{mem_delta:+.1f}",
            status,
        )

    console.print()
    console.print(table)
    console.print()

    if has_regression:
        console.print(
            f"[bold red]⚠ Performance regression detected! "
            f"(threshold: {threshold:.1f}x)[/bold red]"
        )
    else:
        console.print(
            f"[green]✓ No performance regressions "
            f"(threshold: {threshold:.1f}x)[/green]"
        )

    return has_regression


def _fmt_error(result: BenchResult) -> str:
    if result.error:
        return "ERR"
    return f"{result.avg_time_ms:.2f}"

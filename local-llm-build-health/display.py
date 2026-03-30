"""Terminal display: comparison tables and time series charts."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def show_comparison(tag1: str, tag2: str,
                    results1: list[dict], results2: list[dict],
                    crash_info: dict = None):
    """Show side-by-side comparison table of two tags."""
    table = Table(
        title=f"🔍 Benchmark Comparison: {tag1} vs {tag2}",
        show_header=True, header_style="bold cyan",
    )
    table.add_column("Metric", style="bold")
    table.add_column(tag1, justify="right")
    table.add_column(tag2, justify="right")
    table.add_column("Delta", justify="right")

    # Aggregate results per tag
    agg1 = _aggregate(results1)
    agg2 = _aggregate(results2)

    metrics = [
        ("Prompt tok/s", "tok_s_prompt", "{:.2f}"),
        ("Gen tok/s", "tok_s_gen", "{:.2f}"),
        ("Memory (MB)", "mem_mb", "{:.1f}"),
    ]

    for label, key, fmt in metrics:
        v1 = agg1.get(key, 0)
        v2 = agg2.get(key, 0)
        delta = v2 - v1
        pct = (delta / v1 * 100) if v1 else 0

        if key == "mem_mb":
            # Lower is better for memory
            delta_style = "green" if delta <= 0 else "red"
        else:
            # Higher is better for tok/s
            delta_style = "green" if delta >= 0 else "red"

        delta_str = f"{delta:+.2f} ({pct:+.1f}%)" if v1 else "N/A"
        table.add_row(
            label,
            fmt.format(v1) if v1 else "N/A",
            fmt.format(v2) if v2 else "N/A",
            Text(delta_str, style=delta_style),
        )

    console.print()
    console.print(table)

    # Show crash warnings
    if crash_info:
        for tag, info in crash_info.items():
            if info:
                console.print(Panel(
                    f"[bold red]⚠ CRASH DETECTED[/] in {tag}:\n{info}",
                    title="Crash Report", border_style="red",
                ))


def show_history(records: list[dict]):
    """Show historical benchmark results as a table, merging pp/tg per tag."""
    if not records:
        console.print("[yellow]No benchmark history found.[/]")
        return

    # Merge prompt and gen results per (tag, recorded_at[:16])
    merged = _merge_records(records)

    table = Table(
        title="📊 Benchmark History",
        show_header=True, header_style="bold cyan",
    )
    table.add_column("Date", style="dim", width=10)
    table.add_column("Tag", style="bold")
    table.add_column("Model")
    table.add_column("PP tok/s", justify="right")
    table.add_column("TG tok/s", justify="right")
    table.add_column("Mem MB", justify="right")

    for r in merged:
        date = r["recorded_at"][:10] if r.get("recorded_at") else "?"
        table.add_row(
            date,
            r.get("tag", "?"),
            _short_model(r.get("model", "?")),
            f"{r['tok_s_prompt']:.2f}" if r.get("tok_s_prompt") else "-",
            f"{r['tok_s_gen']:.2f}" if r.get("tok_s_gen") else "-",
            f"{r.get('mem_mb', 0):.1f}",
        )

    console.print()
    console.print(table)


def show_timeline(records: list[dict]):
    """Show ASCII time series chart of tok/s by tag."""
    if not records:
        return

    # Group by tag, get avg gen tok/s (skip zero values)
    tag_vals = {}
    for r in records:
        tag = r.get("tag", "?")
        val = r.get("tok_s_gen", 0)
        if val > 0:
            tag_vals.setdefault(tag, []).append(val)

    avgs = {t: sum(v) / len(v) for t, v in tag_vals.items() if v}
    if not avgs:
        return

    max_val = max(avgs.values()) or 1
    bar_width = 40

    console.print()
    console.print("[bold]📈 Generation tok/s by Version[/]")
    console.print()

    for tag in sorted(avgs.keys()):
        val = avgs[tag]
        bar_len = int(val / max_val * bar_width)
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        console.print(f"  {tag:>15} │ {bar} {val:.2f} tok/s")

    console.print()


def show_crash_report(tag: str, error: str):
    """Display a crash/failure report."""
    console.print(Panel(
        f"[bold red]⚠ BUILD/BENCH FAILURE[/] for [bold]{tag}[/]\n\n{error}",
        title="Crash Report", border_style="red",
    ))


def _aggregate(results: list[dict]) -> dict:
    """Average benchmark results."""
    if not results:
        return {}
    keys = ["tok_s_prompt", "tok_s_gen", "mem_mb"]
    agg = {}
    for k in keys:
        vals = [r.get(k, 0) for r in results if r.get(k, 0) > 0]
        agg[k] = sum(vals) / len(vals) if vals else 0
    return agg


def _merge_records(records: list[dict]) -> list[dict]:
    """Merge prompt/gen records for the same tag into single rows."""
    by_tag = {}
    for r in records:
        tag = r.get("tag", "?")
        if tag not in by_tag:
            by_tag[tag] = {
                "tag": tag,
                "model": r.get("model", "?"),
                "tok_s_prompt": 0,
                "tok_s_gen": 0,
                "mem_mb": r.get("mem_mb", 0),
                "recorded_at": r.get("recorded_at", ""),
            }
        if r.get("tok_s_prompt", 0) > 0:
            by_tag[tag]["tok_s_prompt"] = r["tok_s_prompt"]
        if r.get("tok_s_gen", 0) > 0:
            by_tag[tag]["tok_s_gen"] = r["tok_s_gen"]
    return list(by_tag.values())


def _short_model(name: str) -> str:
    # Extract just filename from full path
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    # Remove .gguf extension
    if name.endswith(".gguf"):
        name = name[:-5]
    if len(name) > 30:
        return name[:27] + "..."
    return name

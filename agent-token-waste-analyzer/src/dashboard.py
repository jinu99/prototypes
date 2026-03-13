"""Terminal dashboard — Rich-based display for session analysis results."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from .analyzer import AnalysisResult, WastePattern
from .parser import SessionData


def fmt_tokens(n: int) -> str:
    """Format token count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def ratio_bar(ratio: float, width: int = 20) -> Text:
    """Create a visual bar for a ratio (0.0–1.0)."""
    filled = int(ratio * width)
    empty = width - filled
    bar = Text()
    bar.append("█" * filled, style="green" if ratio > 0.7 else "yellow" if ratio > 0.4 else "red")
    bar.append("░" * empty, style="dim")
    bar.append(f" {ratio:.1%}")
    return bar


def render_summary_panel(session: SessionData, result: AnalysisResult) -> Panel:
    """Render session summary stats panel."""
    lines = Text()
    lines.append("Session: ", style="dim")
    lines.append(f"{session.session_id[:20]}...\n", style="bold cyan")
    lines.append("Tool Calls: ", style="dim")
    lines.append(f"{len(session.tool_calls)}\n", style="bold")
    lines.append("Messages: ", style="dim")
    lines.append(f"{len(session.messages)}\n", style="bold")
    lines.append("\n")
    lines.append("Total Tokens:     ", style="dim")
    lines.append(f"{fmt_tokens(result.total_tokens)}\n", style="bold")
    lines.append("Effective Tokens: ", style="dim")
    lines.append(f"{fmt_tokens(result.effective_tokens)}\n", style="bold green")
    lines.append("Wasted Tokens:    ", style="dim")
    lines.append(f"{fmt_tokens(result.wasted_tokens)}\n", style="bold red")
    lines.append("\n")
    lines.append("Effective Ratio: ")
    lines.append_text(ratio_bar(result.effective_ratio))

    return Panel(lines, title="📊 Session Summary", border_style="blue", padding=(1, 2))


def render_tool_distribution(session: SessionData) -> Panel:
    """Render tool call distribution."""
    tool_counts: dict[str, int] = {}
    for tc in session.tool_calls:
        tool_counts[tc.name] = tool_counts.get(tc.name, 0) + 1

    sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Tool", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Distribution")

    total = sum(tool_counts.values()) or 1
    for tool_name, count in sorted_tools[:10]:
        pct = count / total
        bar_len = int(pct * 20)
        bar = "▓" * bar_len + "░" * (20 - bar_len)
        table.add_row(tool_name, str(count), f"{bar} {pct:.0%}")

    return Panel(table, title="🔧 Tool Distribution", border_style="cyan")


def render_waste_hotspots(result: AnalysisResult) -> Panel:
    """Render top 5 waste hotspots."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold red")
    table.add_column("#", justify="right", width=3)
    table.add_column("Type", width=16)
    table.add_column("Description", no_wrap=False)
    table.add_column("Wasted", justify="right", width=10)
    table.add_column("Count", justify="right", width=6)

    type_style = {
        "repeated_read": "yellow",
        "unused_search": "magenta",
        "duplicate_context": "red",
    }

    top_patterns = sorted(
        result.waste_patterns, key=lambda p: p.wasted_tokens, reverse=True
    )[:5]

    for i, pattern in enumerate(top_patterns, 1):
        style = type_style.get(pattern.pattern_type, "white")
        desc = pattern.description
        if pattern.target and "/" in pattern.target:
            # Show basename + parent for readability
            from pathlib import PurePosixPath
            p = PurePosixPath(pattern.target)
            short = f".../{p.parent.name}/{p.name}" if p.parent.name else p.name
            desc = desc.replace(pattern.target, short)
        table.add_row(
            str(i),
            Text(pattern.pattern_type, style=style),
            desc,
            fmt_tokens(pattern.wasted_tokens),
            str(pattern.occurrences),
        )

    if not top_patterns:
        table.add_row("-", "-", "No waste patterns detected!", "-", "-")

    return Panel(table, title="🔥 Waste Hotspots (Top 5)", border_style="red")


def render_suggestions(result: AnalysisResult) -> Panel:
    """Render optimization suggestions."""
    lines = Text()
    if not result.suggestions:
        lines.append("✅ No significant optimization opportunities found.", style="green")
    else:
        for i, sug in enumerate(result.suggestions, 1):
            lines.append(f"\n{i}. ", style="bold")
            lines.append(f"{sug.title}\n", style="bold yellow")
            lines.append(f"   {sug.description}\n", style="dim")
            if sug.estimated_savings > 0:
                lines.append(f"   Estimated savings: ", style="dim")
                lines.append(f"{fmt_tokens(sug.estimated_savings)} tokens\n", style="green bold")

    return Panel(lines, title="💡 Optimization Suggestions", border_style="yellow")


def render_dashboard(session: SessionData, result: AnalysisResult, console: Console | None = None):
    """Render the full terminal dashboard."""
    if console is None:
        console = Console()

    console.print()
    console.rule("[bold blue]Agent Token Waste Analyzer[/bold blue]", style="blue")
    console.print()

    # Summary + Tool Distribution side by side
    summary = render_summary_panel(session, result)
    tool_dist = render_tool_distribution(session)
    console.print(Columns([summary, tool_dist], equal=True, expand=True))
    console.print()

    # Waste hotspots
    console.print(render_waste_hotspots(result))
    console.print()

    # Suggestions
    console.print(render_suggestions(result))
    console.print()

    # Footer
    grade = _grade(result.effective_ratio)
    console.print(
        Panel(
            Text.assemble(
                ("Efficiency Grade: ", "bold"),
                (grade, f"bold {'green' if grade in ('A', 'B') else 'yellow' if grade == 'C' else 'red'}"),
                ("  |  ", "dim"),
                (f"Waste: {result.waste_ratio:.1%}", "bold red"),
                ("  |  ", "dim"),
                (f"Patterns: {len(result.waste_patterns)}", "bold"),
            ),
            border_style="bold",
        )
    )
    console.print()


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _grade(ratio: float) -> str:
    if ratio >= 0.9:
        return "A"
    if ratio >= 0.75:
        return "B"
    if ratio >= 0.6:
        return "C"
    if ratio >= 0.4:
        return "D"
    return "F"

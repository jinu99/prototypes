"""Rich TUI for displaying analysis results."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from src.analyzer import format_size

console = Console()


def show_header(total: int) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Inbox Cleaner[/bold cyan]\n"
            f"[dim]{total:,} emails analyzed[/dim]",
            box=box.DOUBLE,
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def show_category_summary(category_summary) -> None:
    table = Table(
        title="Category Summary",
        box=box.ROUNDED,
        title_style="bold magenta",
        show_lines=True,
    )
    table.add_column("Category", style="bold", min_width=14)
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Unread", justify="right", style="yellow")
    table.add_column("Total Size", justify="right", style="green")

    colors = {
        "newsletter": "blue",
        "marketing": "red",
        "notification": "yellow",
        "old": "dim",
        "personal": "green",
    }

    for row in category_summary:
        cat = row["category"] or "uncategorized"
        color = colors.get(cat, "white")
        table.add_row(
            f"[{color}]{cat}[/{color}]",
            f"{row['total']:,}",
            f"{row['unread']:,}",
            format_size(row["total_size"]),
        )

    console.print(table)
    console.print()


def show_sender_stats(sender_stats, limit: int = 20) -> None:
    table = Table(
        title=f"Top {limit} Senders",
        box=box.ROUNDED,
        title_style="bold magenta",
        show_lines=False,
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Sender", style="bold", max_width=35)
    table.add_column("Name", max_width=20)
    table.add_column("Emails", justify="right", style="cyan")
    table.add_column("Unread %", justify="right")
    table.add_column("Last Email", style="dim", max_width=12)
    table.add_column("Size", justify="right", style="green")
    table.add_column("Categories", style="yellow", max_width=25)

    for i, row in enumerate(sender_stats[:limit], 1):
        unread_pct = row["unread_pct"] or 0
        pct_style = "red" if unread_pct > 70 else ("yellow" if unread_pct > 40 else "green")

        last_date = (row["last_date"] or "")[:16]

        table.add_row(
            str(i),
            row["sender"],
            row["sender_name"] or "",
            f"{row['total']:,}",
            f"[{pct_style}]{unread_pct:.0f}%[/{pct_style}]",
            last_date,
            format_size(row["total_size"]),
            row["categories"] or "",
        )

    console.print(table)
    console.print()


def show_unsub_candidates(candidates, limit: int = 15) -> None:
    if not candidates:
        console.print("[dim]No unsubscribe candidates found.[/dim]")
        return

    table = Table(
        title="Unsubscribe Candidates",
        box=box.ROUNDED,
        title_style="bold red",
        show_lines=False,
        caption="[dim]High unread % = you're not reading these. Consider unsubscribing.[/dim]",
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Sender", style="bold", max_width=35)
    table.add_column("Name", max_width=20)
    table.add_column("Emails", justify="right", style="cyan")
    table.add_column("Unread %", justify="right", style="red")
    table.add_column("Size", justify="right", style="green")

    for i, c in enumerate(candidates[:limit], 1):
        table.add_row(
            str(i),
            c["sender"],
            c["sender_name"] or "",
            f"{c['total']:,}",
            f"{c['unread_pct']:.0f}%",
            format_size(c["total_size"]),
        )

    console.print(table)
    console.print()


def show_dry_run(dry_run_results: dict) -> None:
    console.print(
        Panel(
            "[bold yellow]DRY RUN[/bold yellow] — Preview of cleanup impact",
            box=box.HEAVY,
            border_style="yellow",
        )
    )
    console.print()

    total_count = 0
    total_size = 0

    for cat, info in dry_run_results.items():
        total_count += info["count"]
        total_size += info["size"]

        table = Table(
            title=f"{cat.upper()} ({info['count']:,} emails, {info['size_human']})",
            box=box.SIMPLE,
            title_style="bold",
        )
        table.add_column("Top Sender", style="cyan", max_width=40)
        table.add_column("Count", justify="right")

        for sender, count in info["top_senders"]:
            table.add_row(sender, str(count))

        console.print(table)

    console.print()
    console.print(
        Panel(
            f"[bold]Total cleanup:[/bold] {total_count:,} emails | "
            f"{format_size(total_size)} recoverable",
            border_style="green",
        )
    )
    console.print()


def show_cleanup_result(results: dict) -> None:
    console.print()
    for cat, info in results.items():
        console.print(
            f"  [bold green]\u2713[/bold green] {cat}: "
            f"{info['deleted']:,} emails deleted ({format_size(info['size'])})"
        )
    total = sum(v["deleted"] for v in results.values())
    total_size = sum(v["size"] for v in results.values())
    console.print()
    console.print(
        Panel(
            f"[bold green]Cleanup complete:[/bold green] {total:,} emails removed | "
            f"{format_size(total_size)} freed",
            border_style="green",
        )
    )


def confirm_action(message: str) -> bool:
    console.print(f"\n[bold yellow]{message}[/bold yellow]")
    response = console.input("[dim](y/N): [/dim]")
    return response.strip().lower() in ("y", "yes")

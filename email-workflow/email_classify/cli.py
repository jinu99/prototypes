"""CLI entry point for email-classify."""
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import db, classifier, parser
from .imap_client import ImapReader
from .demo_data import generate_demo_emails

console = Console()


@click.group()
@click.option("--demo", is_flag=True, help="Use demo data instead of real IMAP")
@click.pass_context
def cli(ctx, demo: bool):
    """읽기전용 이메일 AI 분류기"""
    ctx.ensure_object(dict)
    ctx.obj["demo"] = demo


@cli.command()
@click.option("--host", envvar="IMAP_HOST", help="IMAP server hostname")
@click.option("--port", envvar="IMAP_PORT", default=993, type=int)
@click.option("--user", envvar="IMAP_USER", help="IMAP username")
@click.option("--password", envvar="IMAP_PASS", help="IMAP password (app password)")
@click.option("--count", default=50, help="Number of recent emails to fetch")
@click.pass_context
def connect(ctx, host, port, user, password, count):
    """IMAP EXAMINE 모드로 연결하여 최근 이메일을 fetch합니다."""
    conn = db.get_conn()

    if ctx.obj["demo"]:
        console.print("[yellow]⚡ Demo mode[/yellow] — using sample emails\n")
        raw_emails = generate_demo_emails()
        _process_emails(conn, raw_emails)
        _show_imap_log("[IMAP] DEMO_MODE: Using generated sample emails")
        return

    # Real IMAP connection
    if not all([host, user, password]):
        console.print("[red]Error:[/red] IMAP credentials required.")
        console.print("Set env vars: IMAP_HOST, IMAP_USER, IMAP_PASS")
        console.print("Or use --demo for sample data.")
        sys.exit(1)

    reader = ImapReader(host, port, user, password)
    try:
        greeting = reader.connect()
        console.print(f"[green]Connected:[/green] {greeting}")

        msg_count = reader.examine_inbox()
        console.print(f"[blue]INBOX:[/blue] {msg_count} messages (EXAMINE mode — read-only)")

        raw_emails = reader.fetch_recent(count)
        _process_emails(conn, raw_emails)
        _show_imap_log(reader.get_log())
    except Exception as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        sys.exit(1)
    finally:
        reader.disconnect()


def _process_emails(conn, raw_emails: list[tuple[str, bytes]]):
    """Parse and store fetched emails."""
    stored = 0
    for uid, raw in raw_emails:
        try:
            parsed = parser.parse_raw_email(raw)
            db.upsert_email(
                conn,
                msg_id=parsed["message_id"],
                subject=parsed["subject"],
                sender=parsed["sender"],
                date=parsed["date"],
                body_preview=parsed["body"][:500],
                thread_id=parsed["thread_id"],
                sender_full=parsed.get("sender_full", ""),
            )
            stored += 1
        except Exception as e:
            console.print(f"[dim]Skip msg {uid}: {e}[/dim]")

    console.print(f"\n[green]✓[/green] {stored} emails fetched and cached to SQLite")


def _show_imap_log(log_text: str):
    """Display IMAP log to verify read-only behavior."""
    console.print()
    console.print(Panel(
        log_text,
        title="[dim]IMAP Log (read-only verification)[/dim]",
        border_style="dim",
    ))
    console.print("[dim]No SELECT, STORE, DELETE, or COPY commands used — server unchanged[/dim]")


@cli.command()
@click.option("--top", default=20, help="Show top N emails by importance")
@click.pass_context
def digest(ctx, top):
    """이메일을 분류하고 중요도순 다이제스트를 출력합니다."""
    conn = db.get_conn()

    # Check if we have emails
    emails = db.get_digest(conn, limit=50)
    if not emails:
        console.print("[yellow]No emails cached.[/yellow] Run 'connect' first.")
        sys.exit(1)

    # Classify unclassified emails
    unclassified = [e for e in emails if e["category"] is None]
    if unclassified:
        console.print(f"[blue]Classifying {len(unclassified)} emails...[/blue]")
        for em in unclassified:
            result = classifier.classify_email(
                em.get("sender_full") or em["sender"] or "",
                em["subject"] or "", em["body_preview"] or ""
            )
            db.upsert_classification(
                conn, em["message_id"],
                result["category"], result["importance"], result["summary"]
            )
        console.print(f"[green]✓[/green] Classification complete")
        # Re-fetch with classifications
        emails = db.get_digest(conn, limit=50)

    # Count important
    important = [e for e in emails if (e["importance"] or 0) >= 4]

    # Header
    console.print()
    console.print(Panel(
        f"[bold]오늘 중요한 이메일 {len(important)}개[/bold] (전체 {len(emails)}개 중)",
        title="📬 Daily Digest",
        border_style="blue",
    ))

    # Table
    table = Table(show_header=True, header_style="bold", show_lines=False, pad_edge=False)
    table.add_column("★", width=3, justify="center")
    table.add_column("카테고리", width=12)
    table.add_column("발신자", width=20, no_wrap=True)
    table.add_column("제목", ratio=1)
    table.add_column("요약", ratio=1, style="dim")

    for em in emails[:top]:
        imp = em["importance"] or 0
        cat = em["category"] or "?"

        # Importance stars
        if imp >= 5:
            star = "[red bold]★★★[/red bold]"
        elif imp >= 4:
            star = "[yellow]★★[/yellow]"
        elif imp >= 3:
            star = "[blue]★[/blue]"
        else:
            star = "[dim]·[/dim]"

        # Category color
        cat_colors = {
            "work": "cyan", "finance": "green", "security": "red",
            "travel": "magenta", "shopping": "yellow", "newsletter": "dim",
            "marketing": "dim", "notification": "blue", "social": "magenta",
            "personal": "white",
        }
        color = cat_colors.get(cat, "white")

        table.add_row(
            star,
            f"[{color}]{cat}[/{color}]",
            (em["sender"] or "")[:20],
            (em["subject"] or "")[:50],
            (em["summary"] or "")[:40],
        )

    console.print(table)

    # Category summary
    console.print()
    cats: dict[str, int] = {}
    for em in emails:
        c = em["category"] or "unclassified"
        cats[c] = cats.get(c, 0) + 1

    parts = [f"[bold]{c}[/bold]: {n}" for c, n in sorted(cats.items(), key=lambda x: -x[1])]
    console.print(f"[dim]분류 분포: {' │ '.join(parts)}[/dim]")


@cli.command()
@click.argument("message_id")
@click.pass_context
def thread(ctx, message_id):
    """특정 스레드의 시간순 1줄 요약을 출력합니다."""
    conn = db.get_conn()

    # Find thread ID from message ID
    # Try direct match or partial match
    thread_id = db.find_thread_by_message(conn, message_id)
    if not thread_id:
        # Try partial match
        row = conn.execute(
            "SELECT thread_id FROM emails WHERE message_id LIKE ?",
            (f"%{message_id}%",)
        ).fetchone()
        if row:
            thread_id = row["thread_id"]

    if not thread_id:
        console.print(f"[red]Message not found:[/red] {message_id}")
        console.print("[dim]Hint: use message ID from digest output[/dim]")
        sys.exit(1)

    messages = db.get_thread_messages(conn, thread_id)

    if not messages:
        console.print(f"[yellow]No thread messages found for thread: {thread_id}[/yellow]")
        sys.exit(1)

    # Classify if needed
    for msg in messages:
        if not msg["summary"]:
            result = classifier.classify_email(
                msg["sender"] or "", msg["subject"] or "", msg["body_preview"] or ""
            )
            db.upsert_classification(
                conn, msg["message_id"],
                result["category"], result["importance"], result["summary"]
            )
            msg["summary"] = result["summary"]

    # Display thread
    console.print()
    console.print(Panel(
        f"Thread: [bold]{messages[0]['subject']}[/bold]\n"
        f"Messages: {len(messages)}",
        title="🧵 Thread Summary",
        border_style="cyan",
    ))

    for i, msg in enumerate(messages):
        prefix = "└─" if i == len(messages) - 1 else "├─"
        date_str = (msg["date"] or "")[:19]
        sender = (msg["sender"] or "unknown")[:20]
        summary = msg["summary"] or msg["subject"] or ""

        console.print(
            f"  {prefix} [dim]{date_str}[/dim]  "
            f"[cyan]{sender}[/cyan]  "
            f"{summary}"
        )

    console.print()


def main():
    cli(obj={})


if __name__ == "__main__":
    main()

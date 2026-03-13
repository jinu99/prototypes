"""CLI entry point for Agent Token Waste Analyzer."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from .parser import parse_session, find_session_logs
from .analyzer import analyze_session
from .dashboard import render_dashboard


def list_sessions(base_dir: Path | None, limit: int = 20):
    """List available session logs."""
    console = Console()
    logs = find_session_logs(base_dir)
    if not logs:
        console.print("[red]No session logs found.[/red]")
        return

    console.print(f"\n[bold]Found {len(logs)} session log(s):[/bold]\n")
    for i, log_path in enumerate(logs[:limit]):
        size_kb = log_path.stat().st_size / 1024
        console.print(f"  [dim]{i:3d}[/dim]  [cyan]{log_path.name}[/cyan]  [dim]({size_kb:.0f} KB)[/dim]")
        console.print(f"       [dim]{log_path.parent}[/dim]")
    if len(logs) > limit:
        console.print(f"\n  [dim]... and {len(logs) - limit} more[/dim]")
    console.print()


def analyze_and_display(log_path: Path):
    """Parse, analyze, and display dashboard for a session log."""
    console = Console()

    console.print(f"\n[dim]Parsing:[/dim] {log_path}")
    session = parse_session(log_path)
    console.print(f"[dim]Found {len(session.tool_calls)} tool calls in {len(session.messages)} messages[/dim]")

    console.print("[dim]Analyzing waste patterns...[/dim]")
    result = analyze_session(session)

    render_dashboard(session, result, console)


def main():
    parser = argparse.ArgumentParser(
        prog="agent-token-waste-analyzer",
        description="Analyze Claude Code sessions for token waste patterns",
    )
    subparsers = parser.add_subparsers(dest="command")

    # list command
    list_parser = subparsers.add_parser("list", help="List available session logs")
    list_parser.add_argument("--dir", type=Path, help="Custom logs directory")
    list_parser.add_argument("-n", type=int, default=20, help="Max entries to show")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a session log")
    analyze_parser.add_argument("path", type=Path, help="Path to JSONL session log")

    # latest command
    latest_parser = subparsers.add_parser("latest", help="Analyze the most recent session")
    latest_parser.add_argument("--dir", type=Path, help="Custom logs directory")

    args = parser.parse_args()

    if args.command == "list":
        list_sessions(args.dir, args.n)
    elif args.command == "analyze":
        if not args.path.exists():
            Console().print(f"[red]File not found: {args.path}[/red]")
            sys.exit(1)
        analyze_and_display(args.path)
    elif args.command == "latest":
        logs = find_session_logs(args.dir)
        if not logs:
            Console().print("[red]No session logs found.[/red]")
            sys.exit(1)
        analyze_and_display(logs[0])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

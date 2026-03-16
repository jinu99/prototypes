"""Local Email Inbox Cleaner — CLI entry point."""

import argparse
import sys
import time

from rich.console import Console

console = Console()


def cmd_fetch(args):
    """Fetch emails from IMAP or load mock data."""
    from src.imap_client import fetch_from_imap, load_mock_data

    if args.mock:
        console.print("[cyan]Loading mock data...[/cyan]")
        start = time.time()
        count = load_mock_data(count=args.count)
        elapsed = time.time() - start
        console.print(
            f"[green]Loaded {count:,} mock emails in {elapsed:.1f}s[/green]"
        )
    else:
        if not all([args.host, args.user, args.password]):
            console.print(
                "[red]Error: --host, --user, --password required for IMAP fetch[/red]"
            )
            console.print("[dim]Or use --mock to load test data[/dim]")
            sys.exit(1)

        console.print(f"[cyan]Connecting to {args.host}...[/cyan]")
        start = time.time()
        count = fetch_from_imap(
            host=args.host,
            user=args.user,
            password=args.password,
            port=args.port,
            mailbox=args.mailbox,
        )
        elapsed = time.time() - start
        console.print(
            f"[green]Fetched {count:,} emails in {elapsed:.1f}s[/green]"
        )


def cmd_classify(args):
    """Run heuristic classification on cached emails."""
    from src.classifier import classify_all

    console.print("[cyan]Classifying emails...[/cyan]")
    start = time.time()
    counts = classify_all()
    elapsed = time.time() - start

    console.print(f"[green]Classification complete in {elapsed:.1f}s:[/green]")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        console.print(f"  {cat}: {n:,}")


def cmd_analyze(args):
    """Show analysis dashboard."""
    from src.analyzer import get_analysis
    from src.tui import (
        show_header,
        show_category_summary,
        show_sender_stats,
        show_unsub_candidates,
    )

    analysis = get_analysis()

    show_header(analysis["total_emails"])
    show_category_summary(analysis["category_summary"])
    show_sender_stats(analysis["sender_stats"], limit=args.top)
    show_unsub_candidates(analysis["unsub_candidates"])


def cmd_dryrun(args):
    """Preview cleanup impact."""
    from src.cleanup import dry_run
    from src.tui import show_dry_run

    results = dry_run()
    if not results:
        console.print("[dim]No cleanup candidates found. Run classify first.[/dim]")
        return
    show_dry_run(results)


def cmd_clean(args):
    """Execute cleanup."""
    from src.cleanup import dry_run, execute_cleanup_local, execute_cleanup_imap
    from src.tui import show_dry_run, show_cleanup_result, confirm_action

    # Show dry run first
    dr = dry_run()
    if not dr:
        console.print("[dim]No cleanup candidates found.[/dim]")
        return

    show_dry_run(dr)

    categories = args.categories.split(",") if args.categories else list(dr.keys())

    if args.imap:
        if not all([args.host, args.user, args.password]):
            console.print("[red]--host, --user, --password required for IMAP cleanup[/red]")
            sys.exit(1)

        uids = []
        for cat in categories:
            if cat in dr:
                uids.extend(dr[cat]["uids"])

        if not args.force and not confirm_action(
            f"Delete {len(uids):,} emails from IMAP server?"
        ):
            console.print("[dim]Aborted.[/dim]")
            return

        result = execute_cleanup_imap(
            host=args.host,
            user=args.user,
            password=args.password,
            uids=uids,
            action=args.action,
        )
        console.print(
            f"[green]IMAP cleanup: {result['success']} succeeded, "
            f"{result['failed']} failed[/green]"
        )
    else:
        if not args.force and not confirm_action(
            f"Delete {sum(dr[c]['count'] for c in categories if c in dr):,} "
            f"emails from local cache?"
        ):
            console.print("[dim]Aborted.[/dim]")
            return

        results = execute_cleanup_local(categories)
        show_cleanup_result(results)


def cmd_all(args):
    """Run the full pipeline: fetch → classify → analyze → dry-run."""
    args.mock = True
    args.count = args.count if hasattr(args, "count") and args.count else 12000
    cmd_fetch(args)
    cmd_classify(args)

    args.top = 20
    cmd_analyze(args)
    cmd_dryrun(args)


def main():
    parser = argparse.ArgumentParser(
        description="Local Email Inbox Cleaner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch emails from IMAP or load mock data")
    p_fetch.add_argument("--mock", action="store_true", help="Use mock data")
    p_fetch.add_argument("--count", type=int, default=12000, help="Mock email count")
    p_fetch.add_argument("--host", help="IMAP server host")
    p_fetch.add_argument("--user", help="IMAP username")
    p_fetch.add_argument("--password", help="IMAP password (app password)")
    p_fetch.add_argument("--port", type=int, default=993, help="IMAP port")
    p_fetch.add_argument("--mailbox", default="INBOX", help="Mailbox to fetch")
    p_fetch.set_defaults(func=cmd_fetch)

    # classify
    p_classify = sub.add_parser("classify", help="Classify cached emails")
    p_classify.set_defaults(func=cmd_classify)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Show analysis dashboard")
    p_analyze.add_argument("--top", type=int, default=20, help="Top N senders")
    p_analyze.set_defaults(func=cmd_analyze)

    # dryrun
    p_dry = sub.add_parser("dryrun", help="Preview cleanup impact")
    p_dry.set_defaults(func=cmd_dryrun)

    # clean
    p_clean = sub.add_parser("clean", help="Execute cleanup")
    p_clean.add_argument("--categories", help="Comma-separated categories to clean")
    p_clean.add_argument("--force", action="store_true", help="Skip confirmation")
    p_clean.add_argument("--imap", action="store_true", help="Clean on IMAP server too")
    p_clean.add_argument("--action", choices=["delete", "archive"], default="delete")
    p_clean.add_argument("--host", help="IMAP server host")
    p_clean.add_argument("--user", help="IMAP username")
    p_clean.add_argument("--password", help="IMAP password")
    p_clean.set_defaults(func=cmd_clean)

    # all (demo)
    p_all = sub.add_parser("all", help="Full demo: fetch mock → classify → analyze → dryrun")
    p_all.add_argument("--count", type=int, default=12000, help="Mock email count")
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

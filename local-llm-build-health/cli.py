"""CLI entry point for build-health."""

import argparse
import sys

from builder import build_tag
from benchmark import ensure_model, run_bench
from storage import get_connection, save_build, save_bench_result, get_history, get_results_by_tag
from display import (
    console, show_comparison, show_history, show_timeline,
    show_crash_report,
)


def cmd_compare(args):
    """Compare two llama.cpp tags: build, bench, and show results."""
    tag1, tag2 = args.tags
    model_path = args.model
    conn = get_connection()

    # Download model if needed
    if not model_path:
        model_path = str(ensure_model())

    crash_info = {}
    all_results = {}

    for tag in [tag1, tag2]:
        console.print(f"\n[bold blue]═══ Processing {tag} ═══[/]")

        # Build
        console.print(f"[cyan]Building {tag}...[/]")
        build = build_tag(tag)
        build_id = save_build(conn, tag, build["success"], build.get("error"))

        if not build["success"]:
            show_crash_report(tag, build["error"])
            crash_info[tag] = build["error"]
            all_results[tag] = []
            continue

        # Benchmark
        bench_bin = build["binaries"].get("llama-bench")
        if not bench_bin:
            err = f"llama-bench binary not found in build output for {tag}"
            show_crash_report(tag, err)
            crash_info[tag] = err
            all_results[tag] = []
            continue

        console.print(f"[cyan]Benchmarking {tag}...[/]")
        bench = run_bench(bench_bin, model_path)

        if bench.get("crash"):
            show_crash_report(tag, bench["error"])
            crash_info[tag] = bench["error"]

        if not bench["success"]:
            if not bench.get("crash"):
                show_crash_report(tag, bench.get("error", "Unknown error"))
                crash_info[tag] = bench.get("error")
            all_results[tag] = []
            continue

        # Save results
        for r in bench["results"]:
            save_bench_result(conn, build_id, tag, r)

        all_results[tag] = bench["results"]
        console.print(f"[green]✓ {tag}: {len(bench['results'])} benchmark results[/]")

    # Show comparison
    show_comparison(tag1, tag2, all_results.get(tag1, []),
                    all_results.get(tag2, []), crash_info)


def cmd_history(args):
    """Show benchmark history."""
    conn = get_connection()
    records = get_history(conn, limit=args.limit)
    show_history(records)
    show_timeline(records)


def main():
    parser = argparse.ArgumentParser(
        prog="build-health",
        description="Local LLM Build Health Advisor — "
                    "compare llama.cpp releases by build & benchmark",
    )
    sub = parser.add_subparsers(dest="command")

    # compare
    p_cmp = sub.add_parser("compare", help="Compare two llama.cpp tags")
    p_cmp.add_argument("tags", nargs=2, help="Two git tags to compare (e.g. b5000 b5100)")
    p_cmp.add_argument("--model", "-m", help="Path to GGUF model (auto-downloads if omitted)")
    p_cmp.set_defaults(func=cmd_compare)

    # history
    p_hist = sub.add_parser("history", help="Show benchmark history")
    p_hist.add_argument("--limit", "-n", type=int, default=20, help="Max rows")
    p_hist.set_defaults(func=cmd_history)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

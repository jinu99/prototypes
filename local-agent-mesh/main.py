"""Local Agent Mesh — CLI entry point.

Usage:
    uv run python main.py ask "Summarize this article about AI"
    uv run python main.py ask "Implement a self-balancing AVL tree"
    uv run python main.py demo
    uv run python main.py demo --verbose
"""

from __future__ import annotations

import argparse
import sys

from agent_mesh.mesh import AgentMesh
from agent_mesh.display import render_result
from agent_mesh.models import (
    SMALL_MODEL, LARGE_MODEL,
    check_ollama_available,
)


# Demo scenarios showing different routing and escalation paths
DEMO_SCENARIOS = [
    {
        "label": "Simple summary (should stay on small model)",
        "prompt": "Summarize the key benefits of renewable energy in 3 sentences.",
    },
    {
        "label": "Simple Q&A (should stay on small model)",
        "prompt": "What is Python and why is it popular?",
    },
    {
        "label": "Complex code (should route directly to large model)",
        "prompt": (
            "Implement a self-balancing AVL tree in Python with insert, delete, "
            "and search operations. Include proper rotation logic."
        ),
    },
    {
        "label": "Reasoning task — escalation expected (small model lacks confidence)",
        "prompt": (
            "Why do some technology startups succeed while the vast majority fail "
            "within their first five years of operation? Walk me through the key "
            "factors and reasoning step by step."
        ),
    },
    {
        "label": "Complex reasoning (should route to large model)",
        "prompt": (
            "Design a distributed rate limiter using a sliding window algorithm "
            "that works across multiple server instances. Explain the trade-offs "
            "between consistency and performance."
        ),
    },
]


def cmd_ask(args: argparse.Namespace) -> None:
    """Handle a single prompt."""
    mesh = AgentMesh(
        small_model=args.small_model,
        large_model=args.large_model,
        confidence_threshold=args.threshold,
    )
    result = mesh.process(args.prompt)
    render_result(result, verbose=args.verbose)


def cmd_demo(args: argparse.Namespace) -> None:
    """Run all demo scenarios."""
    mesh = AgentMesh(
        small_model=args.small_model,
        large_model=args.large_model,
        confidence_threshold=args.threshold,
    )

    ollama_status = "CONNECTED" if check_ollama_available() else "MOCK MODE"
    print(f"\n{'=' * 60}")
    print(f"  LOCAL AGENT MESH — DEMO  [{ollama_status}]")
    print(f"  Small: {args.small_model} | Large: {args.large_model}")
    print(f"  Confidence threshold: {args.threshold}")
    print(f"{'=' * 60}")

    summary = {"total": 0, "small_accepted": 0, "escalated": 0, "direct_large": 0}

    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        print(f"\n\033[1m▶ Scenario {i}/{len(DEMO_SCENARIOS)}: {scenario['label']}\033[0m")

        result = mesh.process(scenario["prompt"])
        render_result(result, verbose=args.verbose)

        summary["total"] += 1
        if result.was_escalated:
            summary["escalated"] += 1
        elif result.routing and result.routing.complexity.value == "complex":
            summary["direct_large"] += 1
        else:
            summary["small_accepted"] += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  DEMO SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total scenarios:         {summary['total']}")
    print(f"  Small model accepted:    {summary['small_accepted']}")
    print(f"  Escalated to large:      {summary['escalated']}")
    print(f"  Direct to large:         {summary['direct_large']}")
    saved = summary["small_accepted"]
    total = summary["total"]
    pct = (saved / total * 100) if total else 0
    print(f"  Large model calls saved: {saved}/{total} ({pct:.0f}%)")
    print(f"{'=' * 60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-mesh",
        description="Local Agent Mesh — smart routing + self-delegation for local LLMs",
    )
    parser.add_argument(
        "--small-model", default=SMALL_MODEL,
        help=f"Small model name (default: {SMALL_MODEL})",
    )
    parser.add_argument(
        "--large-model", default=LARGE_MODEL,
        help=f"Large model name (default: {LARGE_MODEL})",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.6,
        help="Confidence threshold for escalation (default: 0.6)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed routing and confidence reasons",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ask command
    ask_parser = sub.add_parser("ask", help="Send a single prompt")
    ask_parser.add_argument("prompt", help="The prompt to process")
    ask_parser.add_argument("--verbose", "-v", action="store_true")

    # demo command
    demo_parser = sub.add_parser("demo", help="Run demo scenarios")
    demo_parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.command == "ask":
        cmd_ask(args)
    elif args.command == "demo":
        cmd_demo(args)


if __name__ == "__main__":
    main()

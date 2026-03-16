"""CLI entry point for soak monitor."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .cluster import SimulatedCluster
from .demo import SCENARIOS, run_scenario
from .monitor import SoakMonitor
from .reporter import BOLD, CYAN, DIM, RESET, Reporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="soak",
        description="Deploy Soak Monitor — watch deployments and catch anomalies",
    )
    sub = parser.add_subparsers(dest="command")

    # soak watch <namespace>
    watch = sub.add_parser(
        "watch", help="Watch a namespace for deployment changes"
    )
    watch.add_argument("namespace", help="Kubernetes namespace to watch")
    watch.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Soak window duration in seconds (default: 30 for demo)",
    )
    watch.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="healthy",
        help="Demo scenario to simulate (default: healthy)",
    )
    watch.add_argument(
        "--deploy",
        default="web-api",
        help="Deployment name to simulate (default: web-api)",
    )

    # soak scenarios — list available scenarios
    sub.add_parser("scenarios", help="List available demo scenarios")

    return parser


async def cmd_watch(args: argparse.Namespace) -> int:
    cluster = SimulatedCluster()
    reporter = Reporter()
    monitor = SoakMonitor(
        cluster=cluster,
        namespace=args.namespace,
        duration=args.duration,
        reporter=reporter,
    )

    # Run scenario and monitor concurrently
    scenario_task = asyncio.create_task(
        run_scenario(
            cluster,
            scenario=args.scenario,
            namespace=args.namespace,
            deploy_name=args.deploy,
        )
    )
    result = await monitor.run()
    await scenario_task

    return 0 if result else 1


def cmd_scenarios() -> None:
    print(f"\n{BOLD}Available demo scenarios:{RESET}\n")
    for name, desc in SCENARIOS.items():
        print(f"  {CYAN}{name:12}{RESET} {DIM}{desc}{RESET}")
    print(
        f"\n{DIM}Usage: soak watch <namespace> --scenario <name> "
        f"--duration <seconds>{RESET}\n"
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "scenarios":
        cmd_scenarios()
        return

    if args.command == "watch":
        exit_code = asyncio.run(cmd_watch(args))
        sys.exit(exit_code)


if __name__ == "__main__":
    main()

"""CLI entry point for oncall gap predetector."""

import argparse
import sys
from pathlib import Path

from analyzer import analyze_gaps
from parser import parse_alert_rules, parse_docker_compose, parse_prometheus_config
from reporter import to_json, to_markdown


def main():
    args = parse_args()
    args.func(args)


def parse_args():
    p = argparse.ArgumentParser(
        prog="oncall-gap-predetector",
        description="Detect monitoring gaps by analyzing Docker Compose + Prometheus configs",
    )
    sub = p.add_subparsers(dest="command")

    # scan command
    scan = sub.add_parser("scan", help="Scan config files for monitoring gaps")
    scan.add_argument("--compose", required=True, type=Path, help="Docker Compose YAML")
    scan.add_argument("--prometheus", required=True, type=Path, help="Prometheus config YAML")
    scan.add_argument("--alerts", required=True, type=Path, help="Alert rules YAML")
    scan.add_argument(
        "--format", choices=["json", "markdown", "both"], default="both",
        help="Output format (default: both)",
    )
    scan.add_argument("--output", type=Path, help="Output directory (default: stdout)")
    scan.set_defaults(func=cmd_scan)

    # demo command
    demo = sub.add_parser("demo", help="Run demo with sample configs")
    demo.add_argument(
        "--format", choices=["json", "markdown", "both"], default="both",
        help="Output format (default: both)",
    )
    demo.set_defaults(func=cmd_demo)

    args = p.parse_args()
    if not args.command:
        p.print_help()
        sys.exit(1)
    return args


def cmd_scan(args):
    """Run gap analysis on provided config files."""
    for path, label in [(args.compose, "compose"), (args.prometheus, "prometheus"), (args.alerts, "alerts")]:
        if not path.exists():
            print(f"Error: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    services = parse_docker_compose(args.compose)
    targets = parse_prometheus_config(args.prometheus)
    rules = parse_alert_rules(args.alerts)
    reports = analyze_gaps(services, targets, rules)

    _output_reports(reports, args.format, args.output)


def cmd_demo(args):
    """Run demo with bundled sample configs."""
    samples = Path(__file__).parent / "samples"
    services = parse_docker_compose(samples / "docker-compose.yml")
    targets = parse_prometheus_config(samples / "prometheus.yml")
    rules = parse_alert_rules(samples / "alert_rules.yml")
    reports = analyze_gaps(services, targets, rules)

    print("=== Oncall Gap Predetector — Demo ===\n")
    _output_reports(reports, args.format, None)


def _output_reports(reports, fmt, output_dir):
    """Output reports in the requested format."""
    json_out = to_json(reports) if fmt in ("json", "both") else None
    md_out = to_markdown(reports) if fmt in ("markdown", "both") else None

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        if json_out:
            (output_dir / "report.json").write_text(json_out)
            print(f"JSON report: {output_dir / 'report.json'}")
        if md_out:
            (output_dir / "report.md").write_text(md_out)
            print(f"Markdown report: {output_dir / 'report.md'}")
    else:
        if json_out:
            print(json_out)
        if md_out and json_out:
            print("\n" + "=" * 60 + "\n")
        if md_out:
            print(md_out)

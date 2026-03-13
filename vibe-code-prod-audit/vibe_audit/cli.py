"""CLI interface for vibe-audit.

Usage:
    vibe-audit scan <project-dir> [--output-dir DIR] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scanner import scan_project
from .checklist import evaluate
from .generator import generate_remediation

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _score_color(score: int) -> str:
    if score >= 80:
        return GREEN
    if score >= 50:
        return YELLOW
    return RED


def _bar(score: int, width: int = 30) -> str:
    filled = round(score / 100 * width)
    color = _score_color(score)
    return f"{color}{'█' * filled}{'░' * (width - filled)}{RESET}"


def cmd_scan(args: argparse.Namespace) -> int:
    project_dir = str(Path(args.project_dir).resolve())

    if not Path(project_dir).is_dir():
        print(f"{RED}Error: '{project_dir}' is not a directory{RESET}", file=sys.stderr)
        return 1

    # Scan
    out = sys.stderr if args.json else sys.stdout
    print(f"\n{BOLD}🔍 Scanning:{RESET} {project_dir}\n", file=out, flush=True)
    scan = scan_project(project_dir)

    if not scan.python_files:
        print(f"{RED}No Python files found in {project_dir}{RESET}", file=out, flush=True)
        return 1

    print(f"{DIM}   Found {len(scan.python_files)} Python file(s), {len(scan.routes)} route(s){RESET}\n", file=out)

    # Evaluate
    report = evaluate(scan)

    if args.json:
        _output_json(report)
        return 0

    # Display report
    _display_report(report)

    # Generate remediation if there are failures
    if report.failed_items:
        output_dir = args.output_dir or str(Path(project_dir) / "generated")
        print(f"\n{BOLD}🔧 Generating remediation code...{RESET}\n")
        generated = generate_remediation(report, project_dir, output_dir)
        if generated:
            for f in generated:
                print(f"   {GREEN}✓{RESET} {f}")
            print(f"\n   {DIM}Generated {len(generated)} file(s) in {output_dir}{RESET}")
        else:
            print(f"   {DIM}No remediation files generated{RESET}")
    else:
        print(f"\n{GREEN}✨ All checks passed! Your project is production-ready.{RESET}")

    print()
    return 0


def _display_report(report):
    color = _score_color(report.score)
    print(f"{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}  Production Readiness Score{RESET}")
    print(f"  {_bar(report.score)}  {color}{BOLD}{report.score}/100{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}\n")

    # Routes summary
    if report.scan.routes:
        print(f"{BOLD}  📡 Routes ({len(report.scan.routes)}):{RESET}")
        for r in report.scan.routes[:10]:
            print(f"   {DIM}{r.method:7s}{RESET} {r.path}  {DIM}← {r.file}:{r.line}{RESET}")
        if len(report.scan.routes) > 10:
            print(f"   {DIM}... and {len(report.scan.routes) - 10} more{RESET}")
        print()

    # Checklist
    print(f"{BOLD}  📋 Checklist:{RESET}\n")

    categories = {}
    for item in report.items:
        categories.setdefault(item.category, []).append(item)

    category_labels = {
        "structure": "Structure",
        "reliability": "Reliability",
        "quality": "Quality",
        "security": "Security",
        "deployment": "Deployment",
    }

    for cat, items in categories.items():
        label = category_labels.get(cat, cat.title())
        print(f"   {BOLD}{label}{RESET}")
        for item in items:
            icon = f"{GREEN}✓{RESET}" if item.passed else f"{RED}✗{RESET}"
            weight_str = f"{DIM}(w:{item.weight}){RESET}"
            print(f"    {icon} {item.name} {weight_str}")
            print(f"      {DIM}{item.detail}{RESET}")
        print()


def _output_json(report):
    data = {
        "score": report.score,
        "routes": [
            {
                "method": r.method,
                "path": r.path,
                "function": r.function_name,
                "file": r.file,
                "line": r.line,
            }
            for r in report.scan.routes
        ],
        "checks": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "passed": item.passed,
                "detail": item.detail,
                "weight": item.weight,
            }
            for item in report.items
        ],
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        prog="vibe-audit",
        description="Production readiness audit for vibe-coded FastAPI projects",
    )
    sub = parser.add_subparsers(dest="command")

    scan_parser = sub.add_parser("scan", help="Scan a FastAPI project directory")
    scan_parser.add_argument("project_dir", help="Path to the FastAPI project")
    scan_parser.add_argument("--output-dir", help="Directory for generated remediation files")
    scan_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "scan":
        return cmd_scan(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())

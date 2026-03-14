"""CLI entry point for sql-ci-static-guard."""

from __future__ import annotations

import json
import sys

import click

from sql_guard.analyzer import analyze_path


def format_text(results) -> str:
    """Format results as human-readable text."""
    lines = []
    total_violations = 0
    total_errors = 0

    for result in results:
        if result.parse_error:
            lines.append(f"\n⚠  {result.path} (parse error)")
            lines.append(f"   {result.parse_error}")
            total_errors += 1
            continue

        if not result.violations:
            lines.append(f"\n✓  {result.path} — clean")
            continue

        lines.append(f"\n✗  {result.path} [{result.dialect}]")
        for v in result.violations:
            icon = "🔴" if v.severity == "error" else "🟡"
            lines.append(f"   {icon} [{v.rule}] {v.message}")
            total_violations += 1

    lines.append(f"\n{'─' * 50}")
    lines.append(f"Files scanned: {len(results)}")
    lines.append(f"Violations: {total_violations}")
    if total_errors:
        lines.append(f"Parse errors: {total_errors}")
    lines.append("")
    return "\n".join(lines)


def format_json(results) -> str:
    """Format results as JSON."""
    data = []
    for result in results:
        entry = {
            "path": result.path,
            "dialect": result.dialect,
            "violations": [
                {"rule": v.rule, "message": v.message, "severity": v.severity}
                for v in result.violations
            ],
        }
        if result.parse_error:
            entry["parse_error"] = result.parse_error
        data.append(entry)
    return json.dumps(data, indent=2, ensure_ascii=False)


@click.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--dialect", "-d", default=None, help="SQL dialect (postgres, mysql, snowflake)")
@click.option("--format", "-f", "fmt", default="text", type=click.Choice(["text", "json"]))
@click.option("--strict", is_flag=True, help="Exit 1 on any violation (for CI)")
def main(paths: tuple[str, ...], dialect: str | None, fmt: str, strict: bool):
    """Scan SQL files for anti-patterns and security issues."""
    all_results = []
    for path in paths:
        all_results.extend(analyze_path(path, dialect=dialect))

    if fmt == "json":
        click.echo(format_json(all_results))
    else:
        click.echo(format_text(all_results))

    has_violations = any(r.violations for r in all_results)
    has_errors = any(
        v.severity == "error" for r in all_results for v in r.violations
    )

    if strict and has_violations:
        sys.exit(1)
    elif has_errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

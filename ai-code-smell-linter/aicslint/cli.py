"""CLI entrypoint for aicslint."""

import json
import sys

import click

from .scanner import scan_file, scan_diff_lines, results_to_json, SUPPORTED_EXTS
from .diff import get_staged_files


def format_result_text(r) -> str:
    sev_colors = {"critical": "red", "warning": "yellow", "info": "blue"}
    sev = click.style(f"[{r.severity.upper()}]", fg=sev_colors.get(r.severity, "white"), bold=True)
    rule = click.style(f"{r.rule_id}", dim=True)
    return f"  {sev} {r.file}:{r.line} — {r.message} {rule}\n    {r.snippet}"


@click.group()
def cli():
    """aicslint — AI Code Smell Linter

    Detects structural code smells typical of AI-generated code,
    using tree-sitter AST analysis. Catches patterns that ESLint/Pylint miss.
    """
    pass


@cli.command()
@click.argument("paths", nargs=-1, required=True)
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def scan(paths, json_output):
    """Scan files or directories for code smells."""
    all_results = []
    for path in paths:
        from pathlib import Path as P
        p = P(path)
        if p.is_file():
            all_results.extend(scan_file(str(p)))
        elif p.is_dir():
            for ext in SUPPORTED_EXTS:
                for f in p.rglob(f"*{ext}"):
                    all_results.extend(scan_file(str(f)))
        else:
            click.echo(f"Warning: '{path}' not found, skipping.", err=True)

    _output(all_results, json_output)


@cli.command()
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def diff(json_output):
    """Scan only git staged changes for code smells."""
    staged = get_staged_files()
    if not staged:
        click.echo("No staged changes found (or not in a git repo).")
        sys.exit(0)

    all_results = []
    for filepath, lines in staged.items():
        ext = "." + filepath.rsplit(".", 1)[-1] if "." in filepath else ""
        if ext in SUPPORTED_EXTS:
            all_results.extend(scan_diff_lines(filepath, lines))

    _output(all_results, json_output)


def _output(results, as_json):
    if as_json:
        click.echo(json.dumps(results_to_json(results), indent=2, ensure_ascii=False))
    else:
        if not results:
            click.echo(click.style("✓ No code smells detected.", fg="green", bold=True))
            return

        # Group by severity
        by_sev = {"critical": [], "warning": [], "info": []}
        for r in results:
            by_sev.get(r.severity, by_sev["info"]).append(r)

        total = len(results)
        click.echo(click.style(f"\n⚠ Found {total} code smell(s):\n", fg="yellow", bold=True))

        for sev in ("critical", "warning", "info"):
            for r in by_sev[sev]:
                click.echo(format_result_text(r))

        # Summary
        counts = {k: len(v) for k, v in by_sev.items() if v}
        summary = ", ".join(f"{v} {k}" for k, v in counts.items())
        click.echo(f"\nSummary: {summary}")

    sys.exit(1 if results else 0)


def main():
    cli()


if __name__ == "__main__":
    main()

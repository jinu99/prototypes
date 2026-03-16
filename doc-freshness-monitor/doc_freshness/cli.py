"""CLI entry point for doc-freshness monitor."""

import sys
from pathlib import Path

import click

from .symbol_extractor import scan_docs
from .git_tracker import track_symbols
from .scorer import score_records
from .reporter import to_json, to_markdown, format_scan_table


@click.group()
def main():
    """Doc Freshness Monitor — detect stale documentation by tracking code symbol references."""
    pass


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table",
              help="Output format")
def scan(repo_path: str, fmt: str):
    """Scan docs for code symbol references and show mapping table."""
    repo = Path(repo_path).resolve()
    doc_symbols = scan_docs(repo)

    if not doc_symbols:
        click.echo("No documentation files with code references found.")
        return

    if fmt == "json":
        import json
        click.echo(json.dumps(doc_symbols, indent=2))
    else:
        click.echo(format_scan_table(doc_symbols))


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option("--threshold", type=int, default=50,
              help="Staleness score threshold for warnings (0-100)")
@click.option("--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown",
              help="Report format")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Write report to file instead of stdout")
def check(repo_path: str, threshold: int, fmt: str, output: str):
    """Check docs for staleness and report warnings.

    Exits with code 1 if any doc-symbol pair exceeds the threshold.
    """
    repo = Path(repo_path).resolve()

    click.echo(f"Scanning docs in {repo}...", err=True)
    doc_symbols = scan_docs(repo)

    if not doc_symbols:
        click.echo("No documentation files with code references found.", err=True)
        return

    total_symbols = sum(len(v) for v in doc_symbols.values())
    click.echo(f"Found {total_symbols} symbol references in {len(doc_symbols)} doc files.", err=True)

    click.echo("Tracking symbol changes via git log...", err=True)
    records = track_symbols(repo, doc_symbols)

    click.echo(f"Resolved {len(records)} doc-symbol pairs to code files.", err=True)

    scored = score_records(records)

    if fmt == "json":
        report = to_json(scored)
    else:
        report = to_markdown(scored)

    if output:
        Path(output).write_text(report)
        click.echo(f"Report written to {output}", err=True)
    else:
        click.echo(report)

    # Check threshold
    warnings = [r for r in scored if r["staleness_score"] >= threshold]
    if warnings:
        click.echo(
            f"\n⚠ {len(warnings)} doc-symbol pair(s) exceed staleness threshold ({threshold}):",
            err=True,
        )
        for w in warnings[:10]:
            click.echo(
                f"  [{w['staleness_score']}] {w['doc_path']}:{w['doc_line']} → "
                f"`{w['symbol']}` ({w['kind']})",
                err=True,
            )
        sys.exit(1)
    else:
        click.echo(f"\nAll docs within staleness threshold ({threshold}).", err=True)


if __name__ == "__main__":
    main()

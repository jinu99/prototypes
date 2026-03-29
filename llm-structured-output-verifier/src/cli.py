"""CLI for LLM Structured Output Verifier."""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .pipeline import run_one_pass, run_two_pass, compare_passes
from .models import EXTRACTION_MODELS, VerificationReport


console = Console()


def print_extraction(data: dict, title: str = "Extracted Data") -> None:
    """Pretty-print extracted data."""
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Field", style="cyan", min_width=15)
    table.add_column("Value", style="white")

    for k, v in data.items():
        if isinstance(v, list):
            v_str = "\n".join(f"• {item}" for item in v) if v else "(empty)"
        else:
            v_str = str(v) if v is not None else "(null)"
        table.add_row(k, v_str)

    console.print(table)


def print_report(report: VerificationReport) -> None:
    """Pretty-print a verification report."""
    console.print()
    console.print(Panel(
        f"Schema: [bold]{report.model_name}[/bold]  |  "
        f"Fields: {report.total_fields}  |  "
        f"Verified: [green]{report.verified_fields}[/green]  |  "
        f"Hallucination candidates: [red]{report.hallucination_candidates}[/red]  |  "
        f"Rate: [bold]{report.hallucination_rate:.0%}[/bold]",
        title="[bold]Verification Summary[/bold]",
        border_style="blue",
    ))

    table = Table(
        title="Field Evidence Report",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Field", style="cyan", min_width=12)
    table.add_column("Value", min_width=15)
    table.add_column("Confidence", justify="center", min_width=10)
    table.add_column("Evidence Span", min_width=20)
    table.add_column("Status", justify="center", min_width=8)
    table.add_column("Reasoning", min_width=20)

    for ev in report.field_evidences:
        conf_color = "green" if ev.confidence >= 0.8 else "yellow" if ev.confidence >= 0.5 else "red"
        status = Text("✗ HALLU", style="bold red") if ev.is_hallucination else Text("✓ OK", style="bold green")
        span_text = f'"{ev.evidence_span}"' if ev.evidence_span else "(none)"

        table.add_row(
            ev.field_name,
            ev.extracted_value[:50],
            f"[{conf_color}]{ev.confidence:.2f}[/{conf_color}]",
            span_text[:60],
            status,
            ev.reasoning[:60],
        )

    console.print(table)


def cmd_verify(args: argparse.Namespace) -> None:
    """Run 2-pass verification on a document."""
    text = Path(args.file).read_text()
    console.print(f"\n[bold]Source:[/bold] {args.file}")
    console.print(f"[dim]{text[:200]}{'...' if len(text) > 200 else ''}[/dim]\n")

    report = run_two_pass(text, args.schema)
    print_extraction(report.extracted_data, title="Pass 1 — Extracted Data")
    print_report(report)


def cmd_extract(args: argparse.Namespace) -> None:
    """Run 1-pass extraction only."""
    text = Path(args.file).read_text()
    console.print(f"\n[bold]Source:[/bold] {args.file}")
    result = run_one_pass(text, args.schema)
    print_extraction(result, title="1-Pass Extraction (no verification)")
    console.print("[yellow]⚠ No verification performed — hallucinations may be present[/yellow]\n")


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare 1-pass vs 2-pass on test documents."""
    doc_dir = Path(args.dir)
    if not doc_dir.is_dir():
        console.print(f"[red]Error: {args.dir} is not a directory[/red]")
        sys.exit(1)

    files = sorted(doc_dir.glob("*.txt"))
    if not files:
        console.print(f"[red]No .txt files found in {args.dir}[/red]")
        sys.exit(1)

    console.print(Panel(
        f"Comparing 1-pass vs 2-pass on {len(files)} documents",
        title="[bold]Comparison Mode[/bold]",
        border_style="magenta",
    ))

    total_fields_all = 0
    total_hallucinations_detected = 0

    for fpath in files:
        text = fpath.read_text()
        # Infer schema from filename
        schema = "person"
        if "product" in fpath.name:
            schema = "product"
        elif "event" in fpath.name:
            schema = "event"

        console.print(f"\n{'='*60}")
        console.print(f"[bold]Document:[/bold] {fpath.name}  |  Schema: {schema}")
        console.print(f"[dim]{text[:120]}...[/dim]\n")

        comparison = compare_passes(text, schema)

        # 1-pass result
        print_extraction(comparison["one_pass_result"], title=f"1-Pass Result ({fpath.name})")

        # 2-pass report
        report = comparison["two_pass_report"]
        print_report(report)

        if comparison["flagged_as_hallucination"]:
            console.print(
                f"[red bold]⚠ Flagged fields: {', '.join(comparison['flagged_as_hallucination'])}[/red bold]"
            )

        total_fields_all += report.total_fields
        total_hallucinations_detected += report.hallucination_candidates

    # Summary
    console.print(f"\n{'='*60}")
    detection_rate = (
        total_hallucinations_detected / total_fields_all * 100
        if total_fields_all > 0 else 0
    )
    console.print(Panel(
        f"Documents analyzed: {len(files)}\n"
        f"Total fields checked: {total_fields_all}\n"
        f"Hallucination candidates detected: [red bold]{total_hallucinations_detected}[/red bold]\n"
        f"Detection rate: [bold]{detection_rate:.1f}%[/bold]\n\n"
        f"[dim]The 2-pass pipeline identifies fields that lack evidence in the\n"
        f"source text, catching hallucinations that 1-pass extraction misses.[/dim]",
        title="[bold]Overall Comparison Summary[/bold]",
        border_style="green",
    ))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM Structured Output Verifier — 2-pass extraction + verification",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # verify
    p_verify = sub.add_parser("verify", help="Run 2-pass verify on a document")
    p_verify.add_argument("file", help="Path to text file")
    p_verify.add_argument(
        "-s", "--schema",
        choices=list(EXTRACTION_MODELS.keys()),
        required=True,
        help="Extraction schema type",
    )

    # extract
    p_extract = sub.add_parser("extract", help="Run 1-pass extraction only")
    p_extract.add_argument("file", help="Path to text file")
    p_extract.add_argument(
        "-s", "--schema",
        choices=list(EXTRACTION_MODELS.keys()),
        required=True,
        help="Extraction schema type",
    )

    # compare
    p_compare = sub.add_parser("compare", help="Compare 1-pass vs 2-pass on test docs")
    p_compare.add_argument(
        "-d", "--dir",
        default="test_docs",
        help="Directory with test .txt files (default: test_docs)",
    )

    args = parser.parse_args()
    if args.command == "verify":
        cmd_verify(args)
    elif args.command == "extract":
        cmd_extract(args)
    elif args.command == "compare":
        cmd_compare(args)


if __name__ == "__main__":
    main()

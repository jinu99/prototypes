"""CLI interface: diagnose and clean commands."""

import argparse
import json
import sys
from pathlib import Path

from .chunker import compute_stats
from .cleaner import clean_document
from .detector import diagnose
from .extractor import extract_document


def cmd_diagnose(args: argparse.Namespace) -> None:
    """Run diagnosis on a PDF and output JSON report."""
    pdf_path = args.file
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Diagnosing: {pdf_path}", file=sys.stderr)
    doc = extract_document(pdf_path)
    report = diagnose(doc)
    report_dict = report.to_dict()

    # Add chunking stats if requested
    if args.stats:
        cleaned = clean_document(doc, report)
        stats = compute_stats(cleaned.cleaned_text, chunk_size=args.chunk_size)
        report_dict["chunking_stats"] = stats.to_dict()

    if args.output:
        Path(args.output).write_text(json.dumps(report_dict, indent=2, ensure_ascii=False))
        print(f"Report saved to: {args.output}", file=sys.stderr)
    else:
        print(json.dumps(report_dict, indent=2, ensure_ascii=False))


def cmd_clean(args: argparse.Namespace) -> None:
    """Clean a PDF and output cleaned text with diff report."""
    pdf_path = args.file
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Cleaning: {pdf_path}", file=sys.stderr)
    doc = extract_document(pdf_path)
    report = diagnose(doc)
    result = clean_document(doc, report)

    # Output diff report to stderr
    diff = result.diff_report()
    if diff:
        print("\n--- Changes ---", file=sys.stderr)
        for page_diff in diff:
            print(f"\n  Page {page_diff['page']}:", file=sys.stderr)
            for item in page_diff["removed"]:
                print(f"    - [{item['type']}] {item['text'][:60]}", file=sys.stderr)
            print(
                f"    → {page_diff['reduction_pct']}% reduction "
                f"({page_diff['original_length']} → {page_diff['cleaned_length']} chars)",
                file=sys.stderr,
            )
    else:
        print("No noise detected.", file=sys.stderr)

    print(f"\nTotal items removed: {result.total_removed}", file=sys.stderr)

    # Output cleaned text
    if args.output:
        Path(args.output).write_text(result.cleaned_text, encoding="utf-8")
        print(f"Cleaned text saved to: {args.output}", file=sys.stderr)
    else:
        print("\n--- Cleaned Text ---\n")
        print(result.cleaned_text)

    # Optional chunking stats
    if args.stats:
        stats = compute_stats(result.cleaned_text, chunk_size=args.chunk_size)
        print("\n--- Chunking Statistics ---", file=sys.stderr)
        stats_dict = stats.to_dict()
        for key, val in stats_dict.items():
            if key == "size_distribution":
                print(f"  {key}:", file=sys.stderr)
                for bucket, count in val.items():
                    bar = "█" * count
                    print(f"    {bucket:>10}: {count:3d} {bar}", file=sys.stderr)
            else:
                print(f"  {key}: {val}", file=sys.stderr)


def cmd_stats(args: argparse.Namespace) -> None:
    """Output chunking statistics for a PDF (after cleaning)."""
    pdf_path = args.file
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    doc = extract_document(pdf_path)
    report = diagnose(doc)
    result = clean_document(doc, report)
    stats = compute_stats(result.cleaned_text, chunk_size=args.chunk_size)

    print(json.dumps(stats.to_dict(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rag-doc-cleaner",
        description="RAG Document Quality Diagnosis and Preprocessing Tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # diagnose
    p_diag = subparsers.add_parser(
        "diagnose", help="Diagnose PDF for noise (watermarks, headers, OCR artifacts)"
    )
    p_diag.add_argument("file", help="Path to PDF file")
    p_diag.add_argument("-o", "--output", help="Save JSON report to file")
    p_diag.add_argument("--stats", action="store_true", help="Include chunking stats")
    p_diag.add_argument("--chunk-size", type=int, default=500, help="Chunk size (default: 500)")
    p_diag.set_defaults(func=cmd_diagnose)

    # clean
    p_clean = subparsers.add_parser(
        "clean", help="Clean PDF by removing detected noise"
    )
    p_clean.add_argument("file", help="Path to PDF file")
    p_clean.add_argument("-o", "--output", help="Save cleaned text to file")
    p_clean.add_argument("--stats", action="store_true", help="Show chunking stats")
    p_clean.add_argument("--chunk-size", type=int, default=500, help="Chunk size (default: 500)")
    p_clean.set_defaults(func=cmd_clean)

    # stats
    p_stats = subparsers.add_parser(
        "stats", help="Show chunking statistics for cleaned document"
    )
    p_stats.add_argument("file", help="Path to PDF file")
    p_stats.add_argument("--chunk-size", type=int, default=500, help="Chunk size (default: 500)")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

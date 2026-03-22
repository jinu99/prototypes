"""agent-knowledge-loop: Extract lessons from agent session logs."""
import argparse
import sys
from pathlib import Path

from src.db import get_conn, upsert_lesson, get_all_lessons, get_lesson_count
from src.extractor import extract_lessons
from src.exporter import EXPORTERS


def cmd_ingest(args):
    """Ingest session log files and extract lessons."""
    conn = get_conn(Path(args.db))
    total_new, total_merged = 0, 0

    for log_file in args.files:
        path = Path(log_file)
        if not path.exists():
            print(f"  ✗ File not found: {path}")
            continue

        print(f"  → Processing: {path.name}")
        lessons = extract_lessons(path)

        if not lessons:
            print(f"    No lessons extracted.")
            continue

        for lesson in lessons:
            lid, was_merged = upsert_lesson(conn, lesson)
            if was_merged:
                total_merged += 1
                print(f"    ↻ Merged: {lesson['failure'][:60]}...")
            else:
                total_new += 1
                print(f"    ✓ New: {lesson['failure'][:60]}...")

    total = get_lesson_count(conn)
    conn.close()
    print(f"\n  Summary: {total_new} new, {total_merged} merged. Total in DB: {total}")


def cmd_export(args):
    """Export lessons to rule file format."""
    conn = get_conn(Path(args.db))
    lessons = get_all_lessons(conn)
    conn.close()

    if not lessons:
        print("  No lessons in DB. Run 'ingest' first.")
        return

    fmt = args.format
    if fmt not in EXPORTERS:
        print(f"  Unknown format: {fmt}. Available: {', '.join(EXPORTERS.keys())}")
        return

    output = EXPORTERS[fmt](lessons)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"  ✓ Exported {len(lessons)} lessons to {out_path}")
    else:
        print(output)


def cmd_list(args):
    """List all lessons in the DB."""
    conn = get_conn(Path(args.db))
    lessons = get_all_lessons(conn)
    conn.close()

    if not lessons:
        print("  No lessons in DB.")
        return

    for i, lesson in enumerate(lessons, 1):
        merge = f" (×{lesson['merge_count']})" if lesson["merge_count"] > 1 else ""
        print(f"  [{i}] [{lesson['category']}] {lesson['failure'][:70]}{merge}")
        print(f"      → {lesson['resolution'][:70]}")
        print()


def cmd_reset(args):
    """Reset (delete) the lesson database."""
    db = Path(args.db)
    if db.exists():
        db.unlink()
        print(f"  ✓ Deleted {db}")
    else:
        print(f"  DB not found: {db}")


def main():
    parser = argparse.ArgumentParser(
        prog="agent-knowledge-loop",
        description="Extract lessons from agent session logs and sync to rule files.",
    )
    parser.add_argument("--db", default="lessons.db", help="SQLite DB path (default: lessons.db)")
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Ingest session logs and extract lessons")
    p_ingest.add_argument("files", nargs="+", help="Session log files (JSONL or text)")

    # export
    p_export = sub.add_parser("export", help="Export lessons to rule file format")
    p_export.add_argument("format", choices=list(EXPORTERS.keys()), help="Output format")
    p_export.add_argument("-o", "--output", help="Output file path (default: stdout)")

    # list
    sub.add_parser("list", help="List all lessons in the DB")

    # reset
    sub.add_parser("reset", help="Delete the lesson database")

    args = parser.parse_args()
    commands = {
        "ingest": cmd_ingest,
        "export": cmd_export,
        "list": cmd_list,
        "reset": cmd_reset,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()

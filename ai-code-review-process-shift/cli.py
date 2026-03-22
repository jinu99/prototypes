"""CLI entry point: ai-review analyze --session <id>"""

import argparse
import sys
from pathlib import Path

from parser import parse_session
from reporter import generate_html


CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def find_session_file(session_id: str) -> Path | None:
    """Find JSONL file by session ID (UUID) or direct path."""
    # Direct path
    direct = Path(session_id)
    if direct.exists() and direct.suffix == ".jsonl":
        return direct

    # Search in Claude projects directory
    if CLAUDE_PROJECTS_DIR.exists():
        for jsonl in CLAUDE_PROJECTS_DIR.rglob(f"{session_id}.jsonl"):
            return jsonl
        # Partial match
        for jsonl in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
            if session_id in jsonl.stem:
                return jsonl

    return None


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run analysis on a session."""
    session_id = args.session
    jsonl_path = find_session_file(session_id)

    if jsonl_path is None:
        print(f"Error: Session '{session_id}' not found.", file=sys.stderr)
        print(f"Searched in: {CLAUDE_PROJECTS_DIR}", file=sys.stderr)
        print("Tip: Pass a direct path to a .jsonl file.", file=sys.stderr)
        return 1

    print(f"Parsing: {jsonl_path}")
    segments = parse_session(jsonl_path)
    print(f"Found {len(segments)} prompt segments")

    changes_count = sum(len(s.file_changes) for s in segments)
    print(f"Found {changes_count} file changes")

    output = Path(args.output) if args.output else Path(f"report_{jsonl_path.stem}.html")
    sid = jsonl_path.stem if len(session_id) > 40 else session_id

    result = generate_html(segments, sid, output)
    print(f"Report generated: {result}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List available sessions."""
    if not CLAUDE_PROJECTS_DIR.exists():
        print("No Claude projects directory found.")
        return 1

    sessions = sorted(CLAUDE_PROJECTS_DIR.rglob("*.jsonl"))
    # Filter out subagent files
    sessions = [s for s in sessions if "subagents" not in str(s)]

    if not sessions:
        print("No session files found.")
        return 1

    print(f"Found {len(sessions)} sessions:\n")
    for s in sessions[-20:]:  # Show latest 20
        size_kb = s.stat().st_size / 1024
        project = s.parent.name
        print(f"  {s.stem}  ({size_kb:.0f}KB)  [{project}]")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="ai-review",
        description="Analyze Claude Code sessions for prompt→code mapping",
    )
    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze a session")
    p_analyze.add_argument("--session", "-s", required=True,
                           help="Session ID (UUID) or path to .jsonl file")
    p_analyze.add_argument("--output", "-o", help="Output HTML path")

    # list
    sub.add_parser("list", help="List available sessions")

    args = parser.parse_args()
    if args.command == "analyze":
        sys.exit(cmd_analyze(args))
    elif args.command == "list":
        sys.exit(cmd_list(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

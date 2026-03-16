"""AI Agent Secret Scrubber — CLI entry point.

Usage:
    uv run main.py wrap <command> [args...]   — Run command with secret masking
    uv run main.py scan [directory]           — Scan directory and show discovered secrets
    uv run main.py demo                       — Run built-in demo with sample .env
"""

from __future__ import annotations

import sys
from pathlib import Path

from detector import SecretDetector
from registry import SecretRegistry
from scrubber import run_wrapped


def cmd_scan(directory: str = ".") -> None:
    """Scan a directory for secrets and display the registry."""
    registry = SecretRegistry()
    count = registry.auto_discover(directory)
    print(f"Scanned: {Path(directory).resolve()}")
    print(registry.summary())
    if count == 0:
        print("(No secrets found. Place a .env file in the target directory.)")


def cmd_wrap(command: list[str], scan_dir: str = ".") -> int:
    """Wrap a command, masking secrets in its output."""
    registry = SecretRegistry()
    count = registry.auto_discover(scan_dir)

    if count == 0:
        print("[scrubber] Warning: no secrets loaded. Output will not be masked.",
              file=sys.stderr)

    detector = SecretDetector(
        registry_values=registry.values,
        enable_entropy=True,
        enable_patterns=True,
    )

    log_path = str(Path(scan_dir) / ".scrubber_log.json")

    print(f"[scrubber] Loaded {count} secrets from registry", file=sys.stderr)
    print(f"[scrubber] Wrapping: {' '.join(command)}", file=sys.stderr)
    print(f"[scrubber] {'=' * 50}", file=sys.stderr)

    exit_code = run_wrapped(command, registry, detector, log_path=log_path)

    print(f"[scrubber] {'=' * 50}", file=sys.stderr)
    print(f"[scrubber] {detector.stats_summary()}", file=sys.stderr)
    print(f"[scrubber] Exit code: {exit_code}", file=sys.stderr)

    return exit_code


def cmd_demo() -> None:
    """Create a sample .env and demonstrate masking."""
    demo_dir = Path("demo_workspace")
    demo_dir.mkdir(exist_ok=True)

    env_file = demo_dir / ".env"
    env_file.write_text(
        '# Demo secrets\n'
        'DATABASE_URL=postgres://user:p4ssw0rd_secret@localhost:5432/mydb\n'
        'API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr678\n'
        'AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n'
        'STRIPE_SECRET_KEY=sk_test_FAKE000000000000000000000\n'
        'SLACK_TOKEN=xoxb-fake-token-for-demo-purposes-only\n'
        'HARMLESS_VAR=hello\n'
        'SHORT=abc\n'
    )

    print("=== Demo: AI Agent Secret Scrubber ===\n")
    print(f"Created sample .env at: {env_file.resolve()}\n")

    # Step 1: Show what's in the registry
    print("--- Step 1: Scanning for secrets ---")
    cmd_scan(str(demo_dir))

    # Step 2: Wrap `cat .env` and show masking
    print("\n--- Step 2: Running `cat .env` through scrubber ---")
    exit_code = cmd_wrap(["cat", str(env_file)], scan_dir=str(demo_dir))

    # Step 3: Show the log
    log_path = demo_dir / ".scrubber_log.json"
    if log_path.exists():
        print(f"\n--- Step 3: Masking log ({log_path}) ---")
        print(log_path.read_text())

    print(f"\n--- Demo complete (exit code preserved: {exit_code}) ---")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]

    if command == "scan":
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        cmd_scan(directory)
    elif command == "wrap":
        if len(sys.argv) < 3:
            print("Usage: uv run main.py wrap <command> [args...]")
            sys.exit(1)
        # Optional: --scan-dir <dir> before the command
        scan_dir = "."
        cmd_args = sys.argv[2:]
        if cmd_args[0] == "--scan-dir" and len(cmd_args) >= 3:
            scan_dir = cmd_args[1]
            cmd_args = cmd_args[2:]
        exit_code = cmd_wrap(cmd_args, scan_dir=scan_dir)
        sys.exit(exit_code)
    elif command == "demo":
        cmd_demo()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

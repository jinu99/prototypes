"""CLI entry point for Runtime Debug Bridge."""

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="rdb",
        description="Runtime Debug Bridge — capture and inspect running process state via MCP",
    )
    sub = parser.add_subparsers(dest="command")

    # rdb wrap -- <command>
    wrap_p = sub.add_parser("wrap", help="Wrap a command and capture its runtime output")
    wrap_p.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (after --)")

    # rdb mcp
    sub.add_parser("mcp", help="Start the MCP server (stdio transport)")

    # rdb logs
    logs_p = sub.add_parser("logs", help="Show recent captured logs")
    logs_p.add_argument("-n", type=int, default=30, help="Number of lines")
    logs_p.add_argument("--session", type=str, default=None)
    logs_p.add_argument("--stream", choices=["stdout", "stderr"], default=None)

    # rdb http
    http_p = sub.add_parser("http", help="Show recent captured HTTP traffic")
    http_p.add_argument("-n", type=int, default=10, help="Number of exchanges")
    http_p.add_argument("--session", type=str, default=None)

    # rdb ps <pid>
    ps_p = sub.add_parser("ps", help="Show process state from /proc")
    ps_p.add_argument("pid", type=int, help="Process ID")

    args = parser.parse_args()

    if args.command == "wrap":
        cmd = args.cmd
        # Strip leading '--' if present
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            wrap_p.error("No command specified. Usage: rdb wrap -- <command>")
        from rdb.capture import wrap_and_capture
        exit_code = asyncio.run(wrap_and_capture(cmd))
        sys.exit(exit_code)

    elif args.command == "mcp":
        from rdb.mcp_server import run_mcp_server
        run_mcp_server()

    elif args.command == "logs":
        import json
        from rdb.storage import get_db, get_recent_logs, get_latest_session
        conn = get_db()
        session = args.session or get_latest_session(conn)
        if not session:
            print("No sessions found. Run `rdb wrap -- <command>` first.")
            sys.exit(1)
        logs = get_recent_logs(conn, n=args.n, session_id=session, stream=args.stream)
        for entry in logs:
            tag = "OUT" if entry["stream"] == "stdout" else "ERR"
            print(f"[{tag}] {entry['line']}")
        conn.close()

    elif args.command == "http":
        import json
        from rdb.storage import get_db, get_recent_http, get_latest_session
        conn = get_db()
        session = args.session or get_latest_session(conn)
        if not session:
            print("No sessions found. Run `rdb wrap -- <command>` first.")
            sys.exit(1)
        traffic = get_recent_http(conn, n=args.n, session_id=session)
        for t in traffic:
            print(f"{t['method']} {t['url']} → {t['status_code']}")
        conn.close()

    elif args.command == "ps":
        import json
        from rdb.procinfo import get_process_state
        state = get_process_state(args.pid)
        print(json.dumps(state, indent=2, default=str))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

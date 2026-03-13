"""CLI entry point for log-incident-correlator."""

import argparse
import sys
from pathlib import Path

from db import get_connection, init_db, upsert_template, insert_deploy_event
from log_parser import parse_log_file
from deploy_events import load_deploy_events
from correlator import correlate


def cmd_ingest(args):
    """Ingest a log file and extract templates."""
    conn = get_connection(Path(args.db))
    init_db(conn)

    print(f"Parsing log file: {args.logfile}")
    new_count = 0
    total = 0

    for line_num, timestamp, cluster_id, template, is_new in parse_log_file(args.logfile):
        was_new = upsert_template(conn, cluster_id, template, timestamp)
        if was_new:
            new_count += 1
            print(f"  [NEW] Cluster #{cluster_id}: {template[:100]}")
        total += 1

        if total % 2000 == 0:
            conn.commit()
            print(f"  ... processed {total} lines")

    conn.commit()
    conn.close()
    print(f"\nDone: {total} lines processed, {new_count} new templates found")


def cmd_deploys(args):
    """Load deploy events from file."""
    conn = get_connection(Path(args.db))
    init_db(conn)

    events = load_deploy_events(args.file)
    for ev in events:
        deploy_id = insert_deploy_event(
            conn, ev["timestamp"], ev["commit_hash"], ev["description"]
        )
        print(f"  Deploy #{deploy_id}: {ev['timestamp']} [{ev['commit_hash']}] {ev['description']}")

    conn.commit()
    conn.close()
    print(f"\nLoaded {len(events)} deploy events")


def cmd_correlate(args):
    """Run correlation analysis."""
    conn = get_connection(Path(args.db))
    init_db(conn)

    window = args.window
    print(f"Correlating with {window}-minute window...\n")
    results = correlate(conn, window_minutes=window)

    if not results:
        print("No correlations found.")
        conn.close()
        return

    # Group by deploy
    by_deploy = {}
    for r in results:
        key = (r["deploy_time"], r["commit_hash"], r["deploy_desc"])
        by_deploy.setdefault(key, []).append(r)

    for (dt, commit, desc), corrs in by_deploy.items():
        print(f"{'='*70}")
        print(f"DEPLOY: {dt}  [{commit}]  {desc}")
        print(f"{'='*70}")
        for c in sorted(corrs, key=lambda x: x["time_delta_sec"]):
            delta_min = c["time_delta_sec"] / 60
            print(f"  +{delta_min:5.1f}min  [Cluster #{c['cluster_id']}]")
            print(f"           {c['template'][:90]}")
            print(f"           first seen: {c['first_seen']}")
            print()

    conn.close()
    print(f"Total: {len(results)} correlations across {len(by_deploy)} deploys")


def cmd_serve(args):
    """Start the dashboard web server."""
    from server import run_server
    run_server(db_path=Path(args.db), port=args.port)


def cmd_demo(args):
    """Run full demo: generate sample data, ingest, correlate."""
    from generate_sample import generate

    db_path = Path(args.db)
    # Remove old DB for clean demo
    if db_path.exists():
        db_path.unlink()

    print("=" * 60)
    print("LOG-INCIDENT CORRELATOR — DEMO")
    print("=" * 60)

    # Step 1: Generate sample data
    print("\n[1/3] Generating sample data...")
    log_path, deploy_path = generate()
    print(f"  Log file: {log_path} ({log_path.stat().st_size // 1024}KB)")
    print(f"  Deploy events: {deploy_path}")

    # Step 2: Ingest
    print(f"\n[2/3] Ingesting logs and deploy events...")
    conn = get_connection(db_path)
    init_db(conn)

    new_count = 0
    total = 0
    for line_num, timestamp, cluster_id, template, is_new in parse_log_file(str(log_path)):
        was_new = upsert_template(conn, cluster_id, template, timestamp)
        if was_new:
            new_count += 1
        total += 1
    conn.commit()
    print(f"  Parsed {total} lines, found {new_count} unique templates")

    events = load_deploy_events(str(deploy_path))
    for ev in events:
        insert_deploy_event(conn, ev["timestamp"], ev["commit_hash"], ev["description"])
    conn.commit()
    print(f"  Loaded {len(events)} deploy events")

    # Step 3: Correlate
    print(f"\n[3/3] Correlating (window={args.window}min)...\n")
    results = correlate(conn, window_minutes=args.window)

    by_deploy = {}
    for r in results:
        key = (r["deploy_time"], r["commit_hash"], r["deploy_desc"])
        by_deploy.setdefault(key, []).append(r)

    for (dt, commit, desc), corrs in by_deploy.items():
        print(f"{'='*70}")
        print(f"  DEPLOY: {dt}")
        print(f"  COMMIT: {commit}")
        print(f"  DESC:   {desc}")
        print(f"  NEW TEMPLATES AFTER DEPLOY: {len(corrs)}")
        print(f"{'='*70}")
        for c in sorted(corrs, key=lambda x: x["time_delta_sec"]):
            delta_min = c["time_delta_sec"] / 60
            print(f"  ⏱ +{delta_min:.1f}min  │ {c['template'][:80]}")
        print()

    conn.close()
    print(f"RESULT: {len(results)} new templates correlated to {len(by_deploy)} deploys")
    print(f"\nRun 'uv run python cli.py serve' to see the dashboard.")


def main():
    parser = argparse.ArgumentParser(
        prog="log-incident-correlator",
        description="Correlate first-seen log patterns with deploy events"
    )
    parser.add_argument("--db", default="correlator.db", help="SQLite database path")

    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Parse a log file and extract templates")
    p_ingest.add_argument("logfile", help="Path to log file")

    # deploys
    p_deploys = sub.add_parser("deploys", help="Load deploy events from JSON/CSV")
    p_deploys.add_argument("file", help="Path to deploy events file")

    # correlate
    p_corr = sub.add_parser("correlate", help="Run correlation analysis")
    p_corr.add_argument("--window", type=int, default=30, help="Time window in minutes (default: 30)")

    # serve
    p_serve = sub.add_parser("serve", help="Start dashboard web server")
    p_serve.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")

    # demo
    p_demo = sub.add_parser("demo", help="Run full demo with sample data")
    p_demo.add_argument("--window", type=int, default=30, help="Time window in minutes (default: 30)")

    args = parser.parse_args()

    commands = {
        "ingest": cmd_ingest,
        "deploys": cmd_deploys,
        "correlate": cmd_correlate,
        "serve": cmd_serve,
        "demo": cmd_demo,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()

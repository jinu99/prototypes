"""CLI tool to query the audit log."""

import argparse
import json
import datetime
import db


def format_row(row: dict) -> str:
    ts = datetime.datetime.fromtimestamp(row["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
    amount_str = f"${row['amount']:.2f}" if row["amount"] else "N/A"
    pii = row.get("pii_detected") or ""
    decision_icon = "✅" if row["decision"] == "approved" else "🚫"

    return (
        f"  {decision_icon} [{ts}] {row['api_pattern']:30s} "
        f"{amount_str:>10s} {row['currency'] or '':>4s}  "
        f"{row['decision']:10s} {row.get('reason', '')}"
        + (f"  PII: {pii}" if pii else "")
    )


def main():
    parser = argparse.ArgumentParser(description="Query spending guard audit log")
    parser.add_argument("-n", "--limit", type=int, default=20, help="Number of records")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--daily-total", action="store_true", help="Show daily total")
    parser.add_argument("--monthly-total", action="store_true", help="Show monthly total")
    args = parser.parse_args()

    if args.daily_total:
        total = db.get_daily_total()
        print(f"Daily approved total: ${total:.2f}")
        return

    if args.monthly_total:
        total = db.get_monthly_total()
        print(f"Monthly approved total: ${total:.2f}")
        return

    rows = db.get_recent_transactions(args.limit)

    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return

    if not rows:
        print("No transactions recorded yet.")
        return

    print(f"\nRecent transactions (last {len(rows)}):")
    print("-" * 100)
    for row in reversed(rows):  # Show oldest first
        print(format_row(row))
    print("-" * 100)
    print(f"Daily total:   ${db.get_daily_total():.2f}")
    print(f"Monthly total: ${db.get_monthly_total():.2f}")


if __name__ == "__main__":
    main()

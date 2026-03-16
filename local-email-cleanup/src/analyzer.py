"""Analyze email data and generate cleanup suggestions."""

from src.db import (
    get_connection,
    get_sender_stats,
    get_category_summary,
    get_cleanup_candidates,
    get_email_count,
)


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_analysis(db_path=None) -> dict:
    """Run full analysis and return structured results."""
    conn = get_connection(db_path)

    total = get_email_count(conn)
    sender_stats = get_sender_stats(conn)
    category_summary = get_category_summary(conn)
    candidates = get_cleanup_candidates(conn)

    # Unsubscribe candidates: senders with newsletter/marketing + high volume
    unsub_candidates = []
    for s in sender_stats:
        cats = (s["categories"] or "").split(",")
        if any(c in ("newsletter", "marketing") for c in cats) and s["total"] >= 3:
            unsub_candidates.append({
                "sender": s["sender"],
                "sender_name": s["sender_name"],
                "total": s["total"],
                "unread_pct": s["unread_pct"],
                "total_size": s["total_size"],
            })

    # Sort by unread percentage (high unread = not reading = should unsubscribe)
    unsub_candidates.sort(key=lambda x: (-x["unread_pct"], -x["total"]))

    # Cleanup summary per category
    cleanup_by_category = {}
    for row in candidates:
        cat = row["category"]
        if cat not in cleanup_by_category:
            cleanup_by_category[cat] = {"count": 0, "size": 0, "uids": []}
        cleanup_by_category[cat]["count"] += 1
        cleanup_by_category[cat]["size"] += row["size"]
        cleanup_by_category[cat]["uids"].append(row["uid"])

    # Total savings
    total_cleanup_size = sum(c["size"] for c in cleanup_by_category.values())
    total_cleanup_count = sum(c["count"] for c in cleanup_by_category.values())

    conn.close()

    return {
        "total_emails": total,
        "sender_stats": sender_stats,
        "category_summary": category_summary,
        "unsub_candidates": unsub_candidates,
        "cleanup_by_category": cleanup_by_category,
        "total_cleanup_count": total_cleanup_count,
        "total_cleanup_size": total_cleanup_size,
    }

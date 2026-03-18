"""UTM-to-payment matching engine (first-touch attribution)."""
import sqlite3
from datetime import datetime, timedelta


# Attribution window: match payment to session within this time range
ATTRIBUTION_WINDOW_HOURS = 72


def derive_channel(utm_source: str | None, utm_medium: str | None, referrer: str | None) -> str:
    """Derive marketing channel from UTM params or referrer."""
    if utm_source:
        source = utm_source.lower()
        medium = (utm_medium or "").lower()
        if source in ("google", "bing") and medium == "cpc":
            return "paid-search"
        if source in ("facebook", "instagram", "twitter", "x", "linkedin") and medium in ("cpc", "paid", "ad"):
            return "paid-social"
        if source in ("facebook", "instagram", "twitter", "x", "linkedin", "reddit", "hackernews"):
            return "organic-social"
        if medium == "email":
            return "email"
        if source == "producthunt":
            return "producthunt"
        return f"{source}/{medium}" if medium else source

    if referrer:
        ref = referrer.lower()
        if "google" in ref or "bing" in ref:
            return "organic-search"
        if any(s in ref for s in ("twitter", "facebook", "reddit", "linkedin")):
            return "organic-social"
        return "referral"

    return "direct"


def match_payments(conn: sqlite3.Connection) -> dict:
    """Match unmatched payments to sessions using first-touch attribution.

    Strategy:
    1. For each unmatched payment, find sessions from the same visitor
       (matched by email or visitor_id) within the attribution window.
    2. Use the FIRST session (earliest) as the attribution source.
    3. Derive the channel from that session's UTM params.
    """
    cursor = conn.cursor()

    # Get unmatched payments
    unmatched = cursor.execute(
        "SELECT id, customer_email, created_at FROM payments WHERE matched_channel IS NULL"
    ).fetchall()

    stats = {"matched": 0, "unmatched": 0, "total": len(unmatched)}

    for payment in unmatched:
        payment_time = datetime.fromisoformat(payment["created_at"])
        window_start = (payment_time - timedelta(hours=ATTRIBUTION_WINDOW_HOURS)).isoformat()

        # Find earliest session for this visitor within attribution window
        session = cursor.execute("""
            SELECT id, utm_source, utm_medium, referrer
            FROM sessions
            WHERE visitor_id = ?
              AND started_at >= ?
              AND started_at <= ?
            ORDER BY started_at ASC
            LIMIT 1
        """, (payment["customer_email"], window_start, payment["created_at"])).fetchone()

        if session:
            channel = derive_channel(session["utm_source"], session["utm_medium"], session["referrer"])
            cursor.execute(
                "UPDATE payments SET matched_session_id = ?, matched_channel = ? WHERE id = ?",
                (session["id"], channel, payment["id"])
            )
            stats["matched"] += 1
        else:
            # No session found — attribute to 'direct'
            cursor.execute(
                "UPDATE payments SET matched_channel = 'direct' WHERE id = ?",
                (payment["id"],)
            )
            stats["unmatched"] += 1

    conn.commit()
    return stats

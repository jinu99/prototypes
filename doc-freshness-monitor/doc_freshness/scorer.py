"""Calculate staleness scores for doc-symbol pairs."""

from datetime import datetime, timezone


def calculate_staleness(record: dict) -> int:
    """Calculate staleness score (0-100) for a doc-symbol pair.

    Factors:
    1. Days since code changed after doc was last updated (0-60 points)
       - More days = higher staleness
    2. Number of code commits since doc update (0-40 points)
       - More commits = higher staleness

    Returns 0 if code hasn't changed since doc update.
    """
    doc_modified = record.get("doc_modified")
    code_modified = record.get("code_modified")

    if not doc_modified or not code_modified:
        return 0

    # Ensure both are offset-aware
    if doc_modified.tzinfo is None:
        doc_modified = doc_modified.replace(tzinfo=timezone.utc)
    if code_modified.tzinfo is None:
        code_modified = code_modified.replace(tzinfo=timezone.utc)

    # If doc was updated after code, it's fresh
    if doc_modified >= code_modified:
        return 0

    # Factor 1: Days elapsed since code changed (after doc update)
    days_stale = (code_modified - doc_modified).days
    # Cap at 365 days -> 60 points
    day_score = min(days_stale / 365.0, 1.0) * 60

    # Factor 2: Commit count (proxy for how much the code evolved)
    commit_count = record.get("commit_count", 0)
    # Cap at 50 commits -> 40 points
    commit_score = min(commit_count / 50.0, 1.0) * 40

    total = int(day_score + commit_score)
    return min(total, 100)


def score_records(records: list[dict]) -> list[dict]:
    """Add staleness_score to each record."""
    for rec in records:
        rec["staleness_score"] = calculate_staleness(rec)
    # Sort by staleness descending
    records.sort(key=lambda r: r["staleness_score"], reverse=True)
    return records

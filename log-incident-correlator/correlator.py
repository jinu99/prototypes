"""Correlate first-seen log templates with deploy events using time windows."""

from datetime import datetime, timedelta
from db import (
    get_all_templates, get_all_deploys,
    insert_correlation,
)


def correlate(conn, window_minutes: int = 30) -> list[dict]:
    """Find new log templates that appeared within a time window after each deploy.

    For each deploy event, looks for templates whose first_seen timestamp falls
    within [deploy_time, deploy_time + window_minutes].

    Returns list of correlation records.
    """
    templates = get_all_templates(conn)
    deploys = get_all_deploys(conn)

    if not templates or not deploys:
        return []

    # Clear previous correlations for fresh analysis
    conn.execute("DELETE FROM correlations")

    results = []
    window = timedelta(minutes=window_minutes)

    for deploy in deploys:
        deploy_time = datetime.fromisoformat(deploy["timestamp"])

        for tmpl in templates:
            first_seen = datetime.fromisoformat(tmpl["first_seen"])
            delta = first_seen - deploy_time

            # Template appeared after deploy and within window
            if timedelta(0) <= delta <= window:
                delta_sec = delta.total_seconds()
                insert_correlation(
                    conn, deploy["id"], tmpl["cluster_id"],
                    delta_sec, window_minutes
                )
                results.append({
                    "deploy_id": deploy["id"],
                    "deploy_time": deploy["timestamp"],
                    "commit_hash": deploy["commit_hash"],
                    "deploy_desc": deploy["description"],
                    "cluster_id": tmpl["cluster_id"],
                    "template": tmpl["template"],
                    "first_seen": tmpl["first_seen"],
                    "time_delta_sec": delta_sec,
                })

    conn.commit()
    return results

"""Parse deploy events from JSON or CSV files."""

import csv
import json
from pathlib import Path


def load_deploy_events(filepath: str) -> list[dict]:
    """Load deploy events from a JSON or CSV file.

    Expected fields: timestamp, commit_hash, description (optional)

    JSON format: [{"timestamp": "...", "commit_hash": "...", "description": "..."}]
    CSV format: timestamp,commit_hash,description (header row required)
    """
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_json(path)
    elif suffix == ".csv":
        return _load_csv(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix} (use .json or .csv)")


def _load_json(path: Path) -> list[dict]:
    with open(path, "r") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    events = []
    for item in data:
        events.append({
            "timestamp": item["timestamp"],
            "commit_hash": item.get("commit_hash", ""),
            "description": item.get("description", ""),
        })
    return sorted(events, key=lambda e: e["timestamp"])


def _load_csv(path: Path) -> list[dict]:
    events = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append({
                "timestamp": row["timestamp"],
                "commit_hash": row.get("commit_hash", ""),
                "description": row.get("description", ""),
            })
    return sorted(events, key=lambda e: e["timestamp"])

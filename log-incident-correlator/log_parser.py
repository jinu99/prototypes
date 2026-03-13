"""Drain3-based log parsing: template extraction and first-seen detection."""

import re
from datetime import datetime
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig


# Common log timestamp patterns
TIMESTAMP_PATTERNS = [
    # ISO 8601: 2026-03-12T14:30:00
    (r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", "%Y-%m-%dT%H:%M:%S"),
    # Syslog-style: Mar 12 14:30:00
    (r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", "%b %d %H:%M:%S"),
    # Common log: 12/Mar/2026:14:30:00
    (r"(\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2})", "%d/%b/%Y:%H:%M:%S"),
]


def extract_timestamp(line: str) -> str | None:
    """Try to extract a timestamp from a log line."""
    for pattern, fmt in TIMESTAMP_PATTERNS:
        m = re.search(pattern, line)
        if m:
            ts_str = m.group(1)
            try:
                # Normalize to ISO format
                ts_str_clean = ts_str.replace("T", " ").rstrip("Z")
                # Remove timezone offset for parsing
                ts_str_clean = re.sub(r"[+-]\d{2}:?\d{2}$", "", ts_str_clean)
                dt = datetime.strptime(ts_str_clean.strip(), "%Y-%m-%d %H:%M:%S")
                return dt.isoformat()
            except ValueError:
                try:
                    dt = datetime.strptime(ts_str, fmt)
                    # Add current year for syslog
                    if dt.year == 1900:
                        dt = dt.replace(year=datetime.now().year)
                    return dt.isoformat()
                except ValueError:
                    continue
    return None


def create_miner() -> TemplateMiner:
    """Create a configured Drain3 template miner."""
    config = TemplateMinerConfig()
    config.drain_sim_th = 0.4
    config.drain_depth = 4
    config.drain_max_children = 100
    config.drain_max_clusters = 1024
    return TemplateMiner(config=config)


def parse_log_file(filepath: str, miner: TemplateMiner | None = None):
    """Parse a log file and yield (line_num, timestamp, cluster_id, template, is_new).

    Args:
        filepath: Path to the log file
        miner: Optional pre-existing TemplateMiner instance
    """
    if miner is None:
        miner = create_miner()

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            timestamp = extract_timestamp(line) or datetime.now().isoformat()
            result = miner.add_log_message(line)
            cluster_id = result["cluster_id"]
            template = result["template_mined"]
            is_new = result["change_type"] == "cluster_created"

            yield line_num, timestamp, cluster_id, template, is_new

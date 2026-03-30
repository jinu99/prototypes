"""PII detection engine using regex patterns from policy."""

import re
import yaml
from pathlib import Path


def load_pii_config() -> dict:
    policy_path = Path(__file__).parent / "policy.yaml"
    with open(policy_path) as f:
        policy = yaml.safe_load(f)
    return policy.get("pii", {})


def detect_pii(text: str, config: dict | None = None) -> list[dict]:
    """Scan text for PII patterns. Returns list of {name, match} dicts."""
    if config is None:
        config = load_pii_config()

    if not config.get("enabled", True):
        return []

    findings = []
    for pattern in config.get("patterns", []):
        matches = re.findall(pattern["regex"], text)
        for match in matches:
            findings.append({"name": pattern["name"], "match": match})

    return findings

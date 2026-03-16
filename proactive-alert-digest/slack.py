"""Slack webhook sender for digest delivery."""

from __future__ import annotations

import requests


def send_to_slack(webhook_url: str, markdown_text: str) -> bool:
    """Send digest to Slack via incoming webhook.

    Returns True on success, False on failure.
    """
    # Slack webhooks accept a simple text payload (markdown-ish)
    payload = {"text": markdown_text}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False

"""Heuristic-based email classifier.

Categories:
  - newsletter: periodic digests, List-Unsubscribe present, bulk precedence
  - marketing: promotional, sales-oriented, bulk senders
  - notification: automated alerts from services (GitHub, Slack, etc.)
  - old: personal emails older than 6 months with no recent reply
  - personal: everything else
"""

import re
import time
from datetime import datetime

from src.db import get_connection, get_all_emails, update_category

# Known mass-mailer X-Mailer strings
MASS_MAILERS = {
    "mailchimp", "sendgrid", "amazon ses", "postmark", "mandrill",
    "sparkpost", "campaign monitor", "constant contact", "hubspot",
    "marketo", "brevo", "sendinblue", "mailgun", "activecampaign",
}

# Notification sender patterns
NOTIFICATION_DOMAINS = {
    "github.com", "gitlab.com", "slack.com", "jira.atlassian.com",
    "trello.com", "linear.app", "notion.so", "figma.com",
    "vercel.com", "netlify.com", "circleci.com", "travis-ci.org",
    "sentry.io", "datadog.com", "pagerduty.com",
}

NOTIFICATION_PREFIXES = {"noreply@", "no-reply@", "notifications@", "alert@", "security@"}

# Marketing keywords in subject
MARKETING_KEYWORDS = re.compile(
    r"(sale|discount|off|deal|offer|promo|coupon|free shipping|limited time|"
    r"flash|clearance|save \d+%|exclusive|hurry|don.t miss|last chance|"
    r"특가|할인|세일|무료배송|쿠폰|한정)",
    re.IGNORECASE,
)

NEWSLETTER_KEYWORDS = re.compile(
    r"(digest|weekly|roundup|issue\s*#?\d+|newsletter|top stories|"
    r"this week in|this week's|wrap.up|뉴스레터|주간|다이제스트)",
    re.IGNORECASE,
)

SIX_MONTHS_AGO = int((datetime.now().timestamp())) - (180 * 86400)


def classify_email(row) -> str:
    """Classify a single email row. Returns category string."""
    sender = row["sender"] if isinstance(row, dict) else row["sender"]
    subject = (row["subject"] if isinstance(row, dict) else row["subject"]) or ""
    list_unsub = (row["list_unsubscribe"] if isinstance(row, dict) else row["list_unsubscribe"]) or ""
    x_mailer = (row["x_mailer"] if isinstance(row, dict) else row["x_mailer"]) or ""
    precedence = (row["precedence"] if isinstance(row, dict) else row["precedence"]) or ""
    date_ts = row["date_ts"] if isinstance(row, dict) else row["date_ts"]

    score = {"newsletter": 0, "marketing": 0, "notification": 0, "old": 0, "personal": 0}

    # --- Signal 1: List-Unsubscribe header ---
    if list_unsub:
        score["newsletter"] += 3
        score["marketing"] += 2

    # --- Signal 2: Precedence header ---
    prec = precedence.lower()
    if prec == "bulk":
        score["newsletter"] += 2
        score["marketing"] += 2
    elif prec == "list":
        score["notification"] += 2

    # --- Signal 3: X-Mailer ---
    mailer_lower = x_mailer.lower()
    if any(m in mailer_lower for m in MASS_MAILERS):
        score["marketing"] += 2
        score["newsletter"] += 1

    # --- Signal 4: Sender domain patterns ---
    domain = sender.split("@")[-1] if "@" in sender else ""

    if domain in NOTIFICATION_DOMAINS:
        score["notification"] += 4

    if any(sender.startswith(p) for p in NOTIFICATION_PREFIXES):
        score["notification"] += 2

    # --- Signal 5: Subject line keywords ---
    if MARKETING_KEYWORDS.search(subject):
        score["marketing"] += 3

    if NEWSLETTER_KEYWORDS.search(subject):
        score["newsletter"] += 3

    # --- Signal 6: Age (old personal) ---
    if date_ts and date_ts < SIX_MONTHS_AGO:
        score["old"] += 2

    # --- Decide ---
    # If no strong signals, it's personal
    max_score = max(score.values())
    if max_score <= 1:
        return "personal"

    # Resolve ties: newsletter > marketing > notification > old > personal
    priority = ["newsletter", "marketing", "notification", "old", "personal"]
    for cat in priority:
        if score[cat] == max_score:
            return cat

    return "personal"


def classify_all(db_path=None) -> dict[str, int]:
    """Classify all emails in the database. Returns category counts."""
    conn = get_connection(db_path)
    emails = get_all_emails(conn)

    counts: dict[str, int] = {}
    for row in emails:
        cat = classify_email(row)
        update_category(conn, row["uid"], cat)
        counts[cat] = counts.get(cat, 0) + 1

    conn.commit()
    conn.close()
    return counts

"""RSS/Atom feed collector for external service status pages."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass

import feedparser

from graph import Status

logger = logging.getLogger(__name__)

# Keywords that indicate incidents in status page feeds
OUTAGE_KEYWORDS = re.compile(
    r"(outage|major|unavailable|down|disruption|emergency)", re.I
)
DEGRADED_KEYWORDS = re.compile(
    r"(degraded|partial|minor|delay|slow|intermittent|maintenance|investigating)", re.I
)
RESOLVED_KEYWORDS = re.compile(
    r"(resolved|completed|fixed|restored|operational|monitoring)", re.I
)


@dataclass
class FeedResult:
    service_id: str
    feed_url: str
    status: Status
    latest_title: str | None
    latest_time: datetime | None
    error: str | None = None


def classify_entry(title: str, summary: str = "") -> Status:
    """Classify a feed entry into a status based on keywords."""
    text = f"{title} {summary}"

    # Check resolved first (most recent state matters)
    if RESOLVED_KEYWORDS.search(text):
        return Status.OPERATIONAL

    if OUTAGE_KEYWORDS.search(text):
        return Status.OUTAGE

    if DEGRADED_KEYWORDS.search(text):
        return Status.DEGRADED

    return Status.OPERATIONAL


def fetch_feed(service_id: str, feed_url: str) -> FeedResult:
    """Fetch and parse a single RSS/Atom feed."""
    try:
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            return FeedResult(
                service_id=service_id,
                feed_url=feed_url,
                status=Status.OPERATIONAL,
                latest_title=None,
                latest_time=None,
                error=f"Feed parse error: {feed.bozo_exception}",
            )

        if not feed.entries:
            return FeedResult(
                service_id=service_id,
                feed_url=feed_url,
                status=Status.OPERATIONAL,
                latest_title=None,
                latest_time=None,
            )

        latest = feed.entries[0]
        title = latest.get("title", "")
        summary = latest.get("summary", "")
        status = classify_entry(title, summary)

        pub_time = None
        if hasattr(latest, "published_parsed") and latest.published_parsed:
            pub_time = datetime(*latest.published_parsed[:6], tzinfo=timezone.utc)
        elif hasattr(latest, "updated_parsed") and latest.updated_parsed:
            pub_time = datetime(*latest.updated_parsed[:6], tzinfo=timezone.utc)

        return FeedResult(
            service_id=service_id,
            feed_url=feed_url,
            status=status,
            latest_title=title,
            latest_time=pub_time,
        )

    except Exception as e:
        logger.warning("Feed fetch failed for %s: %s", service_id, e)
        return FeedResult(
            service_id=service_id,
            feed_url=feed_url,
            status=Status.OPERATIONAL,
            latest_title=None,
            latest_time=None,
            error=str(e),
        )


# --- Mock feed data for demo/testing ---

MOCK_FEEDS: dict[str, list[dict]] = {
    "aws-us-east-1": [
        {"title": "Informational message: Increased API Error Rates",
         "summary": "We are investigating increased error rates for EC2 API calls in US-EAST-1.",
         "published": "2026-03-30T10:00:00Z"},
    ],
    "github": [
        {"title": "Incident with GitHub Actions",
         "summary": "We are investigating degraded performance for GitHub Actions.",
         "published": "2026-03-30T09:00:00Z"},
    ],
    "cloudflare": [
        {"title": "Cloudflare Dashboard and API - Re-monitoring",
         "summary": "This incident has been resolved.",
         "published": "2026-03-29T15:00:00Z"},
    ],
    "vercel": [
        {"title": "All Systems Operational",
         "summary": "No incidents reported.",
         "published": "2026-03-30T08:00:00Z"},
    ],
    "stripe": [
        {"title": "Elevated API Errors",
         "summary": "We're investigating elevated error rates on our API.",
         "published": "2026-03-30T11:00:00Z"},
    ],
}


def fetch_feed_mock(service_id: str) -> FeedResult:
    """Return mock feed data for demo purposes."""
    entries = MOCK_FEEDS.get(service_id, [])
    if not entries:
        return FeedResult(
            service_id=service_id,
            feed_url="mock://",
            status=Status.OPERATIONAL,
            latest_title=None,
            latest_time=None,
        )

    entry = entries[0]
    status = classify_entry(entry["title"], entry.get("summary", ""))
    return FeedResult(
        service_id=service_id,
        feed_url="mock://",
        status=status,
        latest_title=entry["title"],
        latest_time=datetime.fromisoformat(entry["published"]),
    )

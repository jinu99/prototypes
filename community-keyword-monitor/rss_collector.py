"""RSS feed keyword collector — real feed parsing."""

from datetime import datetime, timezone
import re

import feedparser

from db import insert_match, get_config


def _parse_date(entry) -> str:
    """Extract and normalize date from RSS entry."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def collect_rss():
    """Collect keyword matches from configured RSS feeds."""
    keywords = get_config("keyword")
    feeds = get_config("rss_feed")

    if not keywords or not feeds:
        return {"collected": 0, "message": "No keywords or RSS feeds configured"}

    total = 0
    errors = []

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.bozo and not parsed.entries:
                errors.append(f"Failed to parse: {feed_url}")
                continue

            for entry in parsed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                search_text = f"{title} {summary}"

                matched = _match_keywords(search_text, keywords)
                if not matched:
                    continue

                score = 0  # RSS doesn't have upvotes; use 0
                created_at = _parse_date(entry)

                for kw in matched:
                    clean = re.sub(r'<[^>]+>', '', summary)
                    snippet = clean[:200].strip() if clean else ""
                    inserted = insert_match(
                        source_type="rss",
                        source_name=feed_url,
                        title=title,
                        url=link,
                        snippet=snippet,
                        keyword=kw,
                        score=score,
                        created_at=created_at,
                    )
                    if inserted:
                        total += 1
        except Exception as e:
            errors.append(f"{feed_url}: {str(e)}")

    result = {"collected": total, "source": "rss"}
    if errors:
        result["errors"] = errors
    return result

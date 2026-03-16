"""OPML import and RSS feed parsing."""

import xml.etree.ElementTree as ET
import feedparser
from database import insert_feed, insert_article, get_conn
from embedder import embed_texts


def parse_opml(opml_content: str) -> list[dict]:
    """Parse OPML XML and return list of {title, url} dicts."""
    root = ET.fromstring(opml_content)
    feeds = []
    for outline in root.iter("outline"):
        url = outline.get("xmlUrl") or outline.get("htmlUrl")
        title = outline.get("title") or outline.get("text") or url
        if url:
            feeds.append({"title": title, "url": url})
    return feeds


def fetch_and_store_feed(feed_url: str, feed_title: str) -> int:
    """Fetch RSS feed and store articles. Returns number of new articles."""
    feed_id_row = get_conn().execute(
        "SELECT id FROM feeds WHERE url = ?", (feed_url,)
    ).fetchone()

    if feed_id_row:
        feed_id = feed_id_row["id"]
    else:
        feed_id = insert_feed(feed_title, feed_url)
        if feed_id is None:
            return 0

    parsed = feedparser.parse(feed_url)
    if not parsed.entries:
        return 0

    # Prepare texts for batch embedding
    new_entries = []
    texts = []
    for entry in parsed.entries:
        title = entry.get("title", "Untitled")
        summary = entry.get("summary", "") or entry.get("description", "")
        link = entry.get("link")
        published = entry.get("published", "")
        # Combine title + summary for embedding
        text = f"{title}. {summary[:500]}" if summary else title
        new_entries.append((feed_id, title, link, summary[:1000], published))
        texts.append(text)

    # Batch embed all texts
    if texts:
        embeddings = embed_texts(texts)
        count = 0
        for (fid, title, link, summary, published), emb in zip(
            new_entries, embeddings
        ):
            result = insert_article(fid, title, link, summary, published, emb)
            if result is not None:
                count += 1
        return count
    return 0


def import_opml_and_fetch(opml_content: str) -> dict:
    """Full pipeline: parse OPML → fetch all feeds → store articles."""
    feeds = parse_opml(opml_content)
    total_articles = 0
    feed_results = []

    for feed_info in feeds:
        try:
            count = fetch_and_store_feed(feed_info["url"], feed_info["title"])
            feed_results.append({
                "title": feed_info["title"],
                "url": feed_info["url"],
                "articles": count,
                "status": "ok",
            })
            total_articles += count
        except Exception as e:
            feed_results.append({
                "title": feed_info["title"],
                "url": feed_info["url"],
                "articles": 0,
                "status": f"error: {str(e)[:100]}",
            })

    return {
        "feeds_processed": len(feeds),
        "total_new_articles": total_articles,
        "details": feed_results,
    }

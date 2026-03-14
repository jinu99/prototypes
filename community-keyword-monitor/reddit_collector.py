"""Reddit keyword collector — mock/stub implementation.

Since Reddit API requires OAuth credentials, this provides realistic
mock data that mirrors the actual Reddit JSON API structure.
"""

import random
from datetime import datetime, timedelta, timezone

from db import insert_match, get_config

MOCK_TITLES = [
    "Just released my first Python package — feedback welcome!",
    "FastAPI vs Flask: which one for production in 2026?",
    "Machine learning on edge devices — practical tips",
    "How I automated my entire workflow with Python scripts",
    "New to programming — where should I start?",
    "Deep dive into Python's new pattern matching",
    "Building a real-time dashboard with FastAPI and WebSockets",
    "Machine learning model deployment best practices",
    "Python 3.14 release notes — what's new",
    "Is FastAPI replacing Django for API development?",
    "Open source machine learning tools comparison 2026",
    "Tips for writing clean Python code",
    "FastAPI middleware for authentication — tutorial",
    "Machine learning pipeline with Python end-to-end",
    "Why I switched from Node.js to Python",
    "Async programming in Python — common pitfalls",
    "Building REST APIs the right way with FastAPI",
    "Machine learning for beginners — free resources",
    "Python packaging has gotten so much better",
    "Performance comparison: FastAPI vs Starlette vs Django",
]


def _generate_mock_posts(subreddit: str, keywords: list[str]) -> list[dict]:
    """Generate mock Reddit posts that match keywords."""
    posts = []
    now = datetime.now(timezone.utc)

    for title in MOCK_TITLES:
        title_lower = title.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in title_lower]
        if not matched_keywords:
            continue

        hours_ago = random.randint(1, 72)
        score = random.randint(0, 500)

        for kw in matched_keywords:
            posts.append({
                "source_type": "reddit",
                "source_name": f"r/{subreddit}",
                "title": title,
                "url": f"https://reddit.com/r/{subreddit}/comments/{random.randint(100000, 999999)}",
                "snippet": f"Posted in r/{subreddit} — matched keyword '{kw}'",
                "keyword": kw,
                "score": score,
                "created_at": (now - timedelta(hours=hours_ago)).isoformat(),
            })

    return posts


def collect_reddit():
    """Collect keyword matches from mock Reddit data."""
    keywords = get_config("keyword")
    subreddits = get_config("subreddit")

    if not keywords or not subreddits:
        return {"collected": 0, "message": "No keywords or subreddits configured"}

    total = 0
    for sub in subreddits:
        posts = _generate_mock_posts(sub, keywords)
        for post in posts:
            inserted = insert_match(**post)
            if inserted:
                total += 1

    return {"collected": total, "source": "reddit (mock)"}

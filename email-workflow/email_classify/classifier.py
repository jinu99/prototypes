"""Ollama LLM classifier with keyword-based fallback."""
import json
import re
from typing import Optional

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

CATEGORIES = [
    "work", "finance", "social", "newsletter", "marketing",
    "notification", "security", "travel", "shopping", "personal",
]

PROMPT_TEMPLATE = """Classify this email into exactly one category and rate importance 1-5.

Categories: {categories}
Importance: 1=spam/irrelevant, 2=low, 3=medium, 4=important, 5=urgent

Email:
From: {sender}
Subject: {subject}
Body: {body}

Respond ONLY with valid JSON: {{"category": "...", "importance": N, "summary": "one-line summary"}}"""


def classify_email(sender: str, subject: str, body: str) -> dict:
    """Classify email using Ollama, falling back to keyword rules."""
    result = _try_ollama(sender, subject, body)
    if result:
        return result
    return _keyword_classify(sender, subject, body)


def _try_ollama(sender: str, subject: str, body: str) -> Optional[dict]:
    """Try Ollama API for classification."""
    prompt = PROMPT_TEMPLATE.format(
        categories=", ".join(CATEGORIES),
        sender=sender, subject=subject,
        body=body[:1500],
    )
    try:
        resp = httpx.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 100},
        }, timeout=30.0)
        resp.raise_for_status()
        text = resp.json().get("response", "")
        return _parse_llm_response(text)
    except (httpx.HTTPError, httpx.ConnectError, KeyError):
        return None


def _parse_llm_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    # Find JSON in response
    match = re.search(r"\{[^}]+\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        cat = data.get("category", "").lower()
        imp = int(data.get("importance", 3))
        summary = data.get("summary", "")
        if cat not in CATEGORIES:
            cat = "personal"
        imp = max(1, min(5, imp))
        return {"category": cat, "importance": imp, "summary": summary}
    except (json.JSONDecodeError, ValueError):
        return None


# --- Keyword fallback ---

_KEYWORD_RULES = {
    "security": {
        "keywords": ["password", "login", "2fa", "verification", "security", "suspicious", "unauthorized"],
        "importance": 5,
    },
    "finance": {
        "keywords": ["invoice", "payment", "receipt", "billing", "transaction", "bank", "card"],
        "importance": 4,
    },
    "work": {
        "keywords": ["meeting", "deadline", "project", "review", "sprint", "standup",
                     "deploy", "PR", "merge", "미팅", "안건", "jira", "assigned",
                     "pull request", "approved", "failed", "run #", "migration"],
        "importance": 4,
    },
    "travel": {
        "keywords": ["flight", "booking", "hotel", "itinerary", "reservation", "boarding"],
        "importance": 3,
    },
    "shopping": {
        "keywords": ["order", "shipping", "delivered", "tracking", "purchase", "return",
                     "배송", "도착", "주문번호", "수령"],
        "importance": 2,
    },
    "newsletter": {
        "keywords": ["unsubscribe", "newsletter", "digest", "roundup", "edition",
                     "new post from", "read the full post", "pragmatic engineer"],
        "importance": 1,
    },
    "marketing": {
        "keywords": ["sale", "discount", "offer", "promo", "limited time", "deal",
                     "% off", "upgrade now", "netflix", "new on", "you might like"],
        "importance": 1,
    },
    "notification": {
        "keywords": ["notification", "alert", "update", "reminder", "automated"],
        "importance": 2,
    },
    "social": {
        "keywords": ["liked", "commented", "followed", "shared", "tagged", "friend request", "mentioned"],
        "importance": 2,
    },
}


_SENDER_RULES = {
    "work": ["github.com", "atlassian", "jira", "letsur.com", "calendar-notification@google.com"],
    "finance": ["stripe.com", "paypal.com", "billing", "aws.amazon"],
    "social": ["linkedin.com", "facebook.com", "twitter.com", "instagram.com", "viewed your profile"],
    "marketing": ["netflix.com", "spotify.com"],
    "shopping": ["amazon.", "coupang.com", "ship-confirm"],
    "travel": ["koreanair.com", "booking.com", "airbnb.com"],
    "security": ["accounts.google.com", "security@"],
    "notification": ["calendar-notification@", "noreply@"],
}


def _keyword_classify(sender: str, subject: str, body: str) -> dict:
    """Rule-based classification using keyword + sender matching."""
    text = f"{subject} {body}".lower()
    sender_lower = sender.lower()
    scores: dict[str, float] = {}

    # Keyword scoring
    for cat, rule in _KEYWORD_RULES.items():
        score = sum(1 for kw in rule["keywords"] if kw.lower() in text)
        scores[cat] = score

    # Sender domain scoring (weighted higher — sender is strong signal)
    for cat, domains in _SENDER_RULES.items():
        for domain in domains:
            if domain.lower() in sender_lower:
                scores[cat] = scores.get(cat, 0) + 5
                break

    best_cat = max(scores, key=scores.get) if scores else "personal"
    best_score = scores.get(best_cat, 0)

    if best_score == 0:
        best_cat = "personal"

    best_imp = _KEYWORD_RULES.get(best_cat, {}).get("importance", 3)

    # Generate simple summary
    summary = subject if len(subject) < 80 else subject[:77] + "..."

    return {"category": best_cat, "importance": best_imp, "summary": summary}

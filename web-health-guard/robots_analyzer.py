"""robots.txt analyzer — checks AI crawler blocking status."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


AI_CRAWLERS = [
    {"name": "GPTBot", "ua": "GPTBot", "org": "OpenAI"},
    {"name": "ChatGPT-User", "ua": "ChatGPT-User", "org": "OpenAI"},
    {"name": "ClaudeBot", "ua": "ClaudeBot", "org": "Anthropic"},
    {"name": "Claude-Web", "ua": "Claude-Web", "org": "Anthropic"},
    {"name": "Bytespider", "ua": "Bytespider", "org": "ByteDance"},
    {"name": "CCBot", "ua": "CCBot", "org": "Common Crawl"},
    {"name": "Google-Extended", "ua": "Google-Extended", "org": "Google"},
    {"name": "FacebookBot", "ua": "FacebookBot", "org": "Meta"},
    {"name": "PerplexityBot", "ua": "PerplexityBot", "org": "Perplexity"},
    {"name": "Amazonbot", "ua": "Amazonbot", "org": "Amazon"},
]


@dataclass
class RobotsRule:
    user_agent: str
    disallow: list[str]
    allow: list[str]


def parse_robots_txt(text: str) -> list[RobotsRule]:
    """Parse robots.txt into a list of rules per user-agent."""
    rules: list[RobotsRule] = []
    current_ua: str | None = None
    current_disallow: list[str] = []
    current_allow: list[str] = []

    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue

        if line.lower().startswith("user-agent:"):
            if current_ua is not None:
                rules.append(RobotsRule(current_ua, current_disallow, current_allow))
            current_ua = line.split(":", 1)[1].strip()
            current_disallow = []
            current_allow = []
        elif line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                current_disallow.append(path)
        elif line.lower().startswith("allow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                current_allow.append(path)

    if current_ua is not None:
        rules.append(RobotsRule(current_ua, current_disallow, current_allow))

    return rules


def analyze_ai_crawlers(robots_text: str | None) -> dict:
    """Analyze which AI crawlers are blocked in robots.txt."""
    if robots_text is None:
        return {
            "found": False,
            "crawlers": [
                {**c, "blocked": False, "rule": "No robots.txt found"}
                for c in AI_CRAWLERS
            ],
            "block_snippet": generate_block_snippet(AI_CRAWLERS),
        }

    rules = parse_robots_txt(robots_text)

    # Build lookup: user-agent (lowercase) -> list of disallow paths
    ua_rules: dict[str, RobotsRule] = {}
    for rule in rules:
        ua_rules[rule.user_agent.lower()] = rule

    wildcard = ua_rules.get("*")
    results = []
    unblocked = []

    for crawler in AI_CRAWLERS:
        ua_lower = crawler["ua"].lower()
        rule = ua_rules.get(ua_lower)
        if rule and "/" in rule.disallow:
            results.append({
                **crawler,
                "blocked": True,
                "rule": f"User-agent: {crawler['ua']}\\nDisallow: /",
            })
        elif wildcard and "/" in wildcard.disallow:
            # Check if there's a specific allow for this crawler
            results.append({
                **crawler,
                "blocked": True,
                "rule": "Blocked by wildcard User-agent: *\\nDisallow: /",
            })
        else:
            results.append({
                **crawler,
                "blocked": False,
                "rule": "Not blocked — crawler can access the site",
            })
            unblocked.append(crawler)

    return {
        "found": True,
        "raw": robots_text[:2000],
        "crawlers": results,
        "block_snippet": generate_block_snippet(unblocked) if unblocked else None,
    }


def generate_block_snippet(crawlers: list[dict]) -> str | None:
    """Generate robots.txt rules to block the given crawlers."""
    if not crawlers:
        return None
    lines = ["# AI Crawler blocking rules", "# Add these to your robots.txt", ""]
    for c in crawlers:
        lines.append(f"User-agent: {c['ua']}")
        lines.append("Disallow: /")
        lines.append("")
    return "\n".join(lines)

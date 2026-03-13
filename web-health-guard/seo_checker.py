"""Technical SEO checker — analyzes a page for 10+ technical SEO items."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    category: str  # meta | og | structured | mobile | link


def check_title(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("title")
    if not tag or not tag.string:
        return CheckResult("title", False, "No <title> tag found", "meta")
    text = tag.string.strip()
    if len(text) < 10:
        return CheckResult("title", False, f"Title too short ({len(text)} chars) — aim for 30-60", "meta")
    if len(text) > 70:
        return CheckResult("title", False, f"Title too long ({len(text)} chars) — may be truncated in SERPs", "meta")
    return CheckResult("title", True, f'"{text}" ({len(text)} chars)', "meta")


def check_meta_description(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"name": "description"})
    if not tag or not tag.get("content"):
        return CheckResult("meta-description", False, "No meta description found — search engines will auto-generate one", "meta")
    text = tag["content"].strip()
    if len(text) < 50:
        return CheckResult("meta-description", False, f"Description too short ({len(text)} chars)", "meta")
    if len(text) > 160:
        return CheckResult("meta-description", False, f"Description too long ({len(text)} chars) — may be truncated", "meta")
    return CheckResult("meta-description", True, f"{len(text)} chars — looks good", "meta")


def check_canonical(soup: BeautifulSoup, url: str) -> CheckResult:
    tag = soup.find("link", attrs={"rel": "canonical"})
    if not tag or not tag.get("href"):
        return CheckResult("canonical", False, "No canonical link — risk of duplicate content issues", "link")
    href = tag["href"].strip()
    return CheckResult("canonical", True, f"Canonical URL: {href}", "link")


def check_viewport(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"name": "viewport"})
    if not tag or not tag.get("content"):
        return CheckResult("viewport", False, "No viewport meta — page may not be mobile-friendly", "mobile")
    content = tag["content"]
    if "width=device-width" not in content:
        return CheckResult("viewport", False, f"Viewport set but missing width=device-width: {content}", "mobile")
    return CheckResult("viewport", True, f"Viewport: {content}", "mobile")


def check_og_title(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"property": "og:title"})
    if not tag or not tag.get("content"):
        return CheckResult("og:title", False, "No og:title — social shares will lack a proper title", "og")
    return CheckResult("og:title", True, f'"{tag["content"]}"', "og")


def check_og_description(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"property": "og:description"})
    if not tag or not tag.get("content"):
        return CheckResult("og:description", False, "No og:description — social shares will lack a description", "og")
    return CheckResult("og:description", True, f'"{tag["content"][:80]}..."', "og")


def check_og_image(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"property": "og:image"})
    if not tag or not tag.get("content"):
        return CheckResult("og:image", False, "No og:image — social shares will have no preview image", "og")
    return CheckResult("og:image", True, f"Image URL: {tag['content'][:100]}", "og")


def check_og_url(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"property": "og:url"})
    if not tag or not tag.get("content"):
        return CheckResult("og:url", False, "No og:url — social platforms may use the wrong URL", "og")
    return CheckResult("og:url", True, f"URL: {tag['content']}", "og")


def check_structured_data(soup: BeautifulSoup) -> CheckResult:
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return CheckResult("structured-data", False, "No JSON-LD structured data found — rich snippets won't appear", "structured")
    types_found = []
    for s in scripts:
        try:
            data = json.loads(s.string or "")
            if isinstance(data, dict):
                types_found.append(data.get("@type", "unknown"))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        types_found.append(item.get("@type", "unknown"))
        except (json.JSONDecodeError, TypeError):
            pass
    if types_found:
        return CheckResult("structured-data", True, f"Found JSON-LD: {', '.join(types_found)}", "structured")
    return CheckResult("structured-data", True, "JSON-LD script tags found but no @type detected", "structured")


def check_h1(soup: BeautifulSoup) -> CheckResult:
    h1s = soup.find_all("h1")
    if not h1s:
        return CheckResult("h1", False, "No <h1> tag — every page should have exactly one", "meta")
    if len(h1s) > 1:
        return CheckResult("h1", False, f"Multiple <h1> tags ({len(h1s)}) — use only one per page", "meta")
    text = h1s[0].get_text(strip=True)
    return CheckResult("h1", True, f'"{text[:80]}"', "meta")


def check_lang(soup: BeautifulSoup) -> CheckResult:
    html_tag = soup.find("html")
    if not html_tag or not html_tag.get("lang"):
        return CheckResult("lang", False, "No lang attribute on <html> — accessibility and SEO issue", "meta")
    return CheckResult("lang", True, f'Language: {html_tag["lang"]}', "meta")


def check_charset(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"charset": True})
    if tag:
        return CheckResult("charset", True, f'Charset: {tag["charset"]}', "meta")
    tag = soup.find("meta", attrs={"http-equiv": re.compile(r"content-type", re.I)})
    if tag and tag.get("content"):
        return CheckResult("charset", True, f"Charset via http-equiv: {tag['content']}", "meta")
    return CheckResult("charset", False, "No charset declaration — browser may misinterpret characters", "meta")


def check_images_alt(soup: BeautifulSoup) -> CheckResult:
    imgs = soup.find_all("img")
    if not imgs:
        return CheckResult("img-alt", True, "No images found on page", "meta")
    missing = [img.get("src", "?")[:60] for img in imgs if not img.get("alt")]
    if missing:
        return CheckResult(
            "img-alt", False,
            f"{len(missing)}/{len(imgs)} images missing alt text",
            "meta",
        )
    return CheckResult("img-alt", True, f"All {len(imgs)} images have alt text", "meta")


def check_robots_meta(soup: BeautifulSoup) -> CheckResult:
    tag = soup.find("meta", attrs={"name": "robots"})
    if not tag or not tag.get("content"):
        return CheckResult("robots-meta", True, "No robots meta tag — page is indexable by default", "meta")
    content = tag["content"].lower()
    if "noindex" in content:
        return CheckResult("robots-meta", False, f"Page set to noindex: {tag['content']}", "meta")
    return CheckResult("robots-meta", True, f"Robots: {tag['content']}", "meta")


ALL_CHECKS = [
    check_title,
    check_meta_description,
    check_canonical,
    check_viewport,
    check_h1,
    check_lang,
    check_charset,
    check_images_alt,
    check_robots_meta,
    check_og_title,
    check_og_description,
    check_og_image,
    check_og_url,
    check_structured_data,
]

# Functions that need the url argument in addition to soup
_URL_CHECKS = {check_canonical}


def run_seo_checks(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    for fn in ALL_CHECKS:
        result = fn(soup, url) if fn in _URL_CHECKS else fn(soup)
        results.append({
            "name": result.name,
            "passed": result.passed,
            "detail": result.detail,
            "category": result.category,
        })
    return results

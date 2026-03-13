"""Phantom URL detector — finds path-like text that isn't in the sitemap."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup


def parse_sitemap(xml_text: str, base_url: str) -> set[str]:
    """Extract URLs from a sitemap XML."""
    urls: set[str] = set()
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return urls

    # Handle both sitemap index and urlset
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    # Direct <url><loc> entries
    for loc in root.findall(".//sm:loc", ns):
        if loc.text:
            urls.add(loc.text.strip())

    # Fallback: no namespace
    for loc in root.findall(".//loc"):
        if loc.text:
            urls.add(loc.text.strip())

    return urls


def extract_path_patterns(html: str, base_url: str) -> set[str]:
    """Extract path-like patterns from page text (not from href/src attributes).

    Looks for text content that resembles URL paths but isn't an actual link.
    These are 'phantom' candidates — referenced in text but not linked.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove script/style tags to focus on visible text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    # Pattern: anything that looks like a path (/something/else or /something)
    path_pattern = re.compile(r'(?<!\w)(\/[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*\/?)', re.ASCII)
    raw_paths = set(path_pattern.findall(text))

    # Filter out common false positives
    ignore = {"/", "/etc", "/usr", "/bin", "/var", "/tmp", "/dev", "/opt",
              "/home", "/root", "/proc", "/sys", "/lib", "/sbin"}
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    candidates: set[str] = set()
    for path in raw_paths:
        path = path.rstrip("/")
        if path in ignore or len(path) < 3:
            continue
        # Skip very short or very generic paths
        if path.count("/") < 1:
            continue
        candidates.add(urljoin(base, path))

    return candidates


def extract_linked_urls(html: str, base_url: str) -> set[str]:
    """Extract all URLs that are actually linked (href, src)."""
    soup = BeautifulSoup(html, "lxml")
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    linked: set[str] = set()

    for tag in soup.find_all(href=True):
        url = urljoin(base_url, tag["href"])
        if urlparse(url).netloc == parsed.netloc:
            linked.add(url.rstrip("/"))

    for tag in soup.find_all(src=True):
        url = urljoin(base_url, tag["src"])
        if urlparse(url).netloc == parsed.netloc:
            linked.add(url.rstrip("/"))

    return linked


REMEDIATION_GUIDE = {
    "410_gone": {
        "title": "Return 410 Gone",
        "desc": "If the page was intentionally removed, configure your server to return HTTP 410. "
                "This tells search engines the page is permanently gone and should be de-indexed.",
        "example": "# Nginx\nlocation /old-page {\n    return 410;\n}",
    },
    "noindex": {
        "title": "Add noindex meta tag",
        "desc": "If the page exists but shouldn't be indexed, add a noindex tag. "
                "Useful for staging pages or internal tools accidentally exposed.",
        "example": '<meta name="robots" content="noindex, nofollow">',
    },
    "redirect": {
        "title": "301 Redirect",
        "desc": "If the content moved to a new URL, set up a 301 redirect. "
                "This transfers SEO value to the new location.",
        "example": "# Nginx\nlocation /old-path {\n    return 301 /new-path;\n}",
    },
    "sitemap_cleanup": {
        "title": "Remove from sitemap",
        "desc": "If the URL shouldn't exist, remove it from your sitemap.xml. "
                "Orphaned sitemap entries waste crawl budget.",
    },
}


def detect_phantom_urls(
    page_html: str,
    sitemap_xml: str | None,
    base_url: str,
) -> dict:
    """Compare sitemap URLs, linked URLs, and text-mentioned paths."""
    sitemap_urls = parse_sitemap(sitemap_xml, base_url) if sitemap_xml else set()
    text_paths = extract_path_patterns(page_html, base_url)
    linked_urls = extract_linked_urls(page_html, base_url)

    # Normalize for comparison
    norm_sitemap = {u.rstrip("/") for u in sitemap_urls}
    norm_linked = {u.rstrip("/") for u in linked_urls}

    # Phantom = mentioned in text but NOT linked and NOT in sitemap
    phantoms = text_paths - norm_linked - norm_sitemap

    # Also check: in sitemap but not linked (potential orphan pages)
    orphan_sitemap = norm_sitemap - norm_linked
    # Filter to same domain only
    parsed = urlparse(base_url)
    orphan_sitemap = {u for u in orphan_sitemap if urlparse(u).netloc == parsed.netloc}

    phantom_list = [
        {
            "url": url,
            "source": "text_pattern",
            "risk": "Path mentioned in page text but not linked — may be a leaked internal URL",
        }
        for url in sorted(phantoms)[:50]  # Cap at 50
    ]

    orphan_list = [
        {
            "url": url,
            "source": "sitemap_only",
            "risk": "In sitemap but not linked from this page — potential orphan page",
        }
        for url in sorted(orphan_sitemap)[:50]
    ]

    return {
        "phantoms": phantom_list,
        "orphan_sitemap_urls": orphan_list,
        "sitemap_url_count": len(sitemap_urls),
        "linked_url_count": len(linked_urls),
        "text_path_count": len(text_paths),
        "remediation": REMEDIATION_GUIDE,
    }

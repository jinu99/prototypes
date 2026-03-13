"""Analyze search results for suspicious domains."""

import difflib
import re
from urllib.parse import urlparse


# Known suspicious patterns
SUSPICIOUS_TLDS = {
    ".download", ".click", ".xyz", ".top", ".buzz", ".icu",
    ".club", ".site", ".online", ".store", ".fun", ".win",
    ".bid", ".loan", ".racing", ".review", ".stream",
}

CLONE_INDICATORS = [
    "free download", "crack", "serial", "keygen", "patch",
    "full version", "portable", "setup", "installer",
    "softonic", "filehippo", "cnet download", "soft112",
    "download for windows", "download for mac",
]

DOWNLOAD_AGGREGATORS = {
    "uptodown.com", "softonic.com", "filehippo.com",
    "cnet.com", "download.cnet.com", "softpedia.com",
    "majorgeeks.com", "sourceforge.net", "fosshub.com",
    "alternativeto.net", "snapcraft.io", "flathub.org",
}

TRUSTED_DOMAINS = {
    "github.com", "gitlab.com", "bitbucket.org",
    "stackoverflow.com", "stackexchange.com",
    "reddit.com", "news.ycombinator.com",
    "wikipedia.org", "en.wikipedia.org",
    "medium.com", "dev.to",
    "pypi.org", "npmjs.com", "crates.io",
    "readthedocs.io", "readthedocs.org",
    "archlinux.org", "debian.org", "ubuntu.com",
    "fedoraproject.org", "brew.sh", "formulae.brew.sh",
    "docs.rs", "pkg.go.dev",
    "youtube.com", "twitter.com", "x.com",
    "linkedin.com", "facebook.com",
}


def analyze_result(result: dict, project_info: dict, official_domains: set) -> dict:
    """Analyze a single search result for suspiciousness.

    Returns dict with: url, domain, is_official, risk_level, risk_score, reasons
    """
    url = result["href"]
    title = result.get("title", "").lower()
    body = result.get("body", "").lower()
    parsed = urlparse(url)
    domain = parsed.hostname.lower() if parsed.hostname else ""

    reasons = []
    risk_score = 0

    # Check if official
    is_official = _is_official_domain(domain, official_domains)
    if is_official:
        return {
            "url": url,
            "domain": domain,
            "is_official": True,
            "risk_level": "safe",
            "risk_score": 0,
            "reasons": ["Official/trusted domain"],
            "title": result.get("title", ""),
        }

    # Check if trusted third-party
    is_trusted = _is_trusted_domain(domain)
    if is_trusted:
        return {
            "url": url,
            "domain": domain,
            "is_official": False,
            "risk_level": "safe",
            "risk_score": 0,
            "reasons": ["Trusted third-party domain"],
            "title": result.get("title", ""),
        }

    project_name = project_info["project_name"].lower()

    # Check if this is a known download aggregator
    is_aggregator = _is_download_aggregator(domain)

    # Extract base domain (part before TLD)
    parts = domain.split(".")
    base_domain_name = parts[0]
    if base_domain_name == "www" and len(parts) > 1:
        base_domain_name = parts[1]

    name_no_hyphen = project_name.replace("-", "")

    # 1. Project name as subdomain of known download aggregator (low risk)
    if is_aggregator and (project_name in domain or name_no_hyphen in domain):
        reasons.append(f"Download aggregator ({domain}) — verify legitimacy")
        risk_score += 10

    # 2. Exact project name as standalone domain (strongest impersonation signal)
    elif (base_domain_name == project_name or base_domain_name == name_no_hyphen):
        reasons.append(f"Domain exactly matches project name '{project_name}' — likely impersonation")
        risk_score += 50

    # 3. Project name in domain (general)
    elif project_name in domain or name_no_hyphen in domain:
        reasons.append(f"Domain contains project name '{project_name}'")
        risk_score += 25

    # 4. Domain similarity to project name (typosquatting)
    similarity = _domain_similarity(domain, project_name)
    if similarity > 0.6 and similarity < 1.0 and project_name not in domain:
        reasons.append(f"Domain '{domain}' is similar to project name (similarity: {similarity:.2f})")
        risk_score += 30

    # 3. Suspicious TLD
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            reasons.append(f"Suspicious TLD: {tld}")
            risk_score += 20
            break

    # 4. Clone/download indicators in content
    found_indicators = []
    for indicator in CLONE_INDICATORS:
        if indicator in title or indicator in body:
            found_indicators.append(indicator)
    if found_indicators:
        reasons.append(f"Suspicious keywords: {', '.join(found_indicators[:3])}")
        risk_score += 15 * min(len(found_indicators), 3)

    # 5. Domain has many hyphens or numbers (common in fake sites)
    base_domain = domain.split(".")[0]
    hyphen_count = base_domain.count("-")
    digit_count = sum(1 for c in base_domain if c.isdigit())
    if hyphen_count >= 2:
        reasons.append(f"Domain has {hyphen_count} hyphens")
        risk_score += 10
    if digit_count >= 3:
        reasons.append(f"Domain has {digit_count} digits")
        risk_score += 10

    # 6. Very long domain name
    if len(base_domain) > 20:
        reasons.append(f"Unusually long domain ({len(base_domain)} chars)")
        risk_score += 5

    # Determine risk level
    if risk_score >= 50:
        risk_level = "danger"
    elif risk_score >= 20:
        risk_level = "warning"
    else:
        risk_level = "safe"

    if not reasons:
        reasons.append("No suspicious indicators found")

    return {
        "url": url,
        "domain": domain,
        "is_official": False,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reasons": reasons,
        "title": result.get("title", ""),
    }


def _is_official_domain(domain: str, official_domains: set) -> bool:
    """Check if domain matches any official domain."""
    for od in official_domains:
        if domain == od or domain.endswith("." + od):
            return True
    return False


def _is_download_aggregator(domain: str) -> bool:
    """Check if domain is a known download aggregator."""
    for ad in DOWNLOAD_AGGREGATORS:
        if domain == ad or domain.endswith("." + ad):
            return True
    return False


def _is_trusted_domain(domain: str) -> bool:
    """Check if domain is a known trusted third-party."""
    for td in TRUSTED_DOMAINS:
        if domain == td or domain.endswith("." + td):
            return True
    return False


def _domain_similarity(domain: str, project_name: str) -> float:
    """Calculate similarity between domain and project name."""
    # Extract base domain (without TLD)
    parts = domain.split(".")
    if len(parts) >= 2:
        base = parts[0] if parts[0] != "www" else parts[1] if len(parts) > 1 else parts[0]
    else:
        base = domain

    # Use SequenceMatcher for fuzzy matching
    return difflib.SequenceMatcher(None, base.lower(), project_name.lower()).ratio()


def analyze_all(results: list[dict], project_info: dict, official_domains: set) -> list[dict]:
    """Analyze all search results, return sorted by risk score descending."""
    analyses = []
    for r in results:
        analysis = analyze_result(r, project_info, official_domains)
        analyses.append(analysis)

    analyses.sort(key=lambda x: x["risk_score"], reverse=True)
    return analyses

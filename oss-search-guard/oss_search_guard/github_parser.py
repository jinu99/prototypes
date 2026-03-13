"""Parse GitHub repo URL to extract project name and official URLs."""

import re
from urllib.parse import urlparse

import httpx


def parse_github_url(url: str) -> dict:
    """Extract project metadata from a GitHub repo URL.

    Returns dict with keys: owner, repo, project_name, official_urls, homepage
    """
    url = url.strip().rstrip("/")

    # Handle various GitHub URL formats
    patterns = [
        r"github\.com/([^/]+)/([^/]+)",
        r"^([^/]+)/([^/]+)$",  # owner/repo shorthand
    ]

    owner, repo = None, None
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            owner, repo = m.group(1), m.group(2)
            break

    if not owner or not repo:
        raise ValueError(f"Cannot parse GitHub URL: {url}")

    repo = repo.replace(".git", "")

    github_url = f"https://github.com/{owner}/{repo}"
    official_urls = [github_url]

    # Try to fetch repo metadata from GitHub API (no auth needed for public repos)
    homepage = None
    description = None
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            homepage = data.get("homepage")
            description = data.get("description", "")
            if homepage:
                homepage = homepage.strip().rstrip("/")
                official_urls.append(homepage)
                # Also add www variant
                parsed = urlparse(homepage)
                if parsed.hostname and not parsed.hostname.startswith("www."):
                    www_variant = homepage.replace(
                        f"{parsed.scheme}://{parsed.hostname}",
                        f"{parsed.scheme}://www.{parsed.hostname}",
                    )
                    official_urls.append(www_variant)
                elif parsed.hostname and parsed.hostname.startswith("www."):
                    no_www = homepage.replace("://www.", "://")
                    official_urls.append(no_www)
    except Exception:
        pass

    # Common official URL patterns
    official_urls.extend([
        f"https://{owner}.github.io/{repo}",
        f"https://{owner}.github.io",
    ])

    # Docs sites
    official_urls.extend([
        f"https://{repo}.readthedocs.io",
        f"https://{repo}.readthedocs.org",
    ])

    # PyPI / npm / crates etc.
    official_urls.extend([
        f"https://pypi.org/project/{repo}",
        f"https://www.npmjs.com/package/{repo}",
        f"https://crates.io/crates/{repo}",
    ])

    return {
        "owner": owner,
        "repo": repo,
        "project_name": repo,
        "description": description or "",
        "homepage": homepage,
        "official_urls": official_urls,
        "github_url": github_url,
    }


def get_official_domains(project_info: dict) -> set:
    """Extract the set of official domains from project info."""
    domains = set()
    for url in project_info["official_urls"]:
        parsed = urlparse(url)
        if parsed.hostname:
            domains.add(parsed.hostname.lower())
    # Always trust these
    domains.update([
        "github.com",
        "gitlab.com",
        "stackoverflow.com",
        "wikipedia.org",
        "en.wikipedia.org",
    ])
    return domains

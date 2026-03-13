"""Web Health Guard — FastAPI server."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse, urljoin

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from seo_checker import run_seo_checks
from robots_analyzer import analyze_ai_crawlers
from phantom_detector import detect_phantom_urls

app = FastAPI(title="Web Health Guard")
app.mount("/static", StaticFiles(directory="static"), name="static")

TIMEOUT = httpx.Timeout(15.0, connect=10.0)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WebHealthGuard/1.0; +https://github.com/example)"
}


async def fetch_url(client: httpx.AsyncClient, url: str) -> tuple[int, str] | None:
    """Fetch a URL, return (status_code, text) or None on failure."""
    try:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True)
        return resp.status_code, resp.text
    except (httpx.RequestError, httpx.HTTPStatusError):
        return None


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/scan")
async def scan(url: str = Query(..., description="URL to scan")):
    """Run all three analyses on the given URL."""
    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")
    sitemap_url = urljoin(base_url, "/sitemap.xml")

    async with httpx.AsyncClient(timeout=TIMEOUT, verify=False) as client:
        # Fetch all three resources concurrently
        page_task = fetch_url(client, url)
        robots_task = fetch_url(client, robots_url)
        sitemap_task = fetch_url(client, sitemap_url)

        page_result, robots_result, sitemap_result = await asyncio.gather(
            page_task, robots_task, sitemap_task
        )

    if page_result is None:
        return JSONResponse(
            {"error": f"Failed to fetch {url} — check that the URL is reachable"},
            status_code=400,
        )

    page_status, page_html = page_result

    # SEO checks
    seo_results = run_seo_checks(page_html, url)

    # robots.txt analysis
    robots_text = robots_result[1] if robots_result and robots_result[0] == 200 else None
    robots_analysis = analyze_ai_crawlers(robots_text)

    # Phantom URL detection
    sitemap_xml = sitemap_result[1] if sitemap_result and sitemap_result[0] == 200 else None
    phantom_analysis = detect_phantom_urls(page_html, sitemap_xml, base_url)

    return {
        "url": url,
        "page_status": page_status,
        "seo": seo_results,
        "robots": robots_analysis,
        "phantom": phantom_analysis,
    }

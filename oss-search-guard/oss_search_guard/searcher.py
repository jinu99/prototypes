"""Search DuckDuckGo for project name and collect results."""

from ddgs import DDGS


def search_project(project_name: str, max_results: int = 20) -> list[dict]:
    """Search DuckDuckGo for project name, return top results.

    Each result has: title, href, body
    """
    queries = [
        f"{project_name} download",
        f"{project_name} official site",
        project_name,
    ]

    seen_urls = set()
    all_results = []

    for query in queries:
        try:
            results = DDGS().text(query, max_results=max_results)
            for r in results:
                url = r.get("href", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append({
                        "title": r.get("title", ""),
                        "href": url,
                        "body": r.get("body", ""),
                        "query": query,
                    })
        except Exception as e:
            print(f"  [!] Search query '{query}' failed: {e}")

    return all_results


def filter_relevant(results: list[dict], project_name: str) -> list[dict]:
    """Filter results to only those mentioning the project name."""
    name_lower = project_name.lower()
    # Also check common variations (hyphens vs underscores, etc.)
    variations = {name_lower, name_lower.replace("-", ""), name_lower.replace("_", "")}

    relevant = []
    for r in results:
        text = (r["title"] + " " + r["body"] + " " + r["href"]).lower()
        if any(v in text for v in variations):
            relevant.append(r)

    return relevant

"""CLI entry point for OSS Search Guard."""

import sys

from .github_parser import get_official_domains, parse_github_url
from .searcher import search_project, filter_relevant
from .analyzer import analyze_all
from .reporter import print_report, BOLD, RESET, DIM


def main():
    if len(sys.argv) < 2:
        print(f"\n{BOLD}OSS Search Guard{RESET}")
        print(f"Detect impersonation sites in search results for open-source projects.\n")
        print(f"Usage: oss-search-guard <github-repo-url>\n")
        print(f"Examples:")
        print(f"  oss-search-guard https://github.com/lh3/minimap2")
        print(f"  oss-search-guard https://github.com/nicotine-plus/nicotine-plus")
        print(f"  oss-search-guard qarmin/czkawka")
        sys.exit(1)

    url = sys.argv[1]

    # Step 1: Parse GitHub URL
    print(f"\n{BOLD}[1/3]{RESET} Parsing GitHub repository...")
    try:
        project_info = parse_github_url(url)
    except ValueError as e:
        print(f"  Error: {e}")
        sys.exit(1)

    print(f"  Project: {BOLD}{project_info['project_name']}{RESET}")
    print(f"  Owner:   {project_info['owner']}")
    if project_info.get("homepage"):
        print(f"  Homepage: {project_info['homepage']}")
    print(f"  Official domains: {', '.join(get_official_domains(project_info))}")

    # Step 2: Search DuckDuckGo
    print(f"\n{BOLD}[2/3]{RESET} Searching DuckDuckGo...")
    results = search_project(project_info["project_name"], max_results=20)
    print(f"  Collected {len(results)} unique results")

    # Filter to relevant results
    results = filter_relevant(results, project_info["project_name"])
    print(f"  Relevant results: {len(results)}")

    if not results:
        print("  No relevant search results found. Try again later.")
        sys.exit(1)

    # Step 3: Analyze results
    print(f"\n{BOLD}[3/3]{RESET} Analyzing search results...")
    official_domains = get_official_domains(project_info)
    analyses = analyze_all(results, project_info, official_domains)

    # Print report
    print_report(project_info, analyses)


if __name__ == "__main__":
    main()

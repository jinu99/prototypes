"""CLI report output for search guard results."""


# ANSI color codes
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[96m"


def print_report(project_info: dict, analyses: list[dict]):
    """Print a formatted threat report to the CLI."""
    danger_count = sum(1 for a in analyses if a["risk_level"] == "danger")
    warning_count = sum(1 for a in analyses if a["risk_level"] == "warning")
    safe_count = sum(1 for a in analyses if a["risk_level"] == "safe")
    total = len(analyses)

    # Header
    print()
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  OSS Search Guard — Threat Report{RESET}")
    print(f"{'=' * 70}")
    print()
    print(f"  {BOLD}Project:{RESET}  {project_info['project_name']}")
    print(f"  {BOLD}GitHub:{RESET}   {project_info['github_url']}")
    if project_info.get("homepage"):
        print(f"  {BOLD}Homepage:{RESET} {project_info['homepage']}")
    if project_info.get("description"):
        print(f"  {BOLD}Desc:{RESET}     {project_info['description'][:80]}")
    print()

    # Overall threat level
    if danger_count > 0:
        overall = f"{RED}{BOLD}DANGER{RESET}"
        overall_msg = f"Found {danger_count} dangerous result(s) in search results!"
    elif warning_count > 0:
        overall = f"{YELLOW}{BOLD}WARNING{RESET}"
        overall_msg = f"Found {warning_count} suspicious result(s) in search results."
    else:
        overall = f"{GREEN}{BOLD}SAFE{RESET}"
        overall_msg = "No suspicious results detected."

    print(f"  {BOLD}Overall Threat Level:{RESET} {overall}")
    print(f"  {overall_msg}")
    print()
    print(f"  {BOLD}Summary:{RESET} {GREEN}{safe_count} safe{RESET} / "
          f"{YELLOW}{warning_count} warning{RESET} / "
          f"{RED}{danger_count} danger{RESET} "
          f"(out of {total} results)")
    print()

    # Dangerous results
    if danger_count > 0:
        print(f"{RED}{BOLD}  --- DANGEROUS RESULTS ---{RESET}")
        print()
        for a in analyses:
            if a["risk_level"] == "danger":
                _print_result(a, RED)

    # Warning results
    if warning_count > 0:
        print(f"{YELLOW}{BOLD}  --- SUSPICIOUS RESULTS ---{RESET}")
        print()
        for a in analyses:
            if a["risk_level"] == "warning":
                _print_result(a, YELLOW)

    # Safe results (condensed)
    if safe_count > 0:
        print(f"{GREEN}{BOLD}  --- SAFE RESULTS ---{RESET}")
        print()
        for a in analyses:
            if a["risk_level"] == "safe":
                label = "OFFICIAL" if a["is_official"] else "OK"
                print(f"    {GREEN}[{label}]{RESET} {DIM}{a['domain']}{RESET}")
                print(f"             {DIM}{a['url'][:70]}{RESET}")

    print()
    print(f"{BOLD}{'=' * 70}{RESET}")
    print()


def _print_result(analysis: dict, color: str):
    """Print a single suspicious result with details."""
    level = analysis["risk_level"].upper()
    print(f"    {color}[{level}]{RESET} {BOLD}{analysis['domain']}{RESET} "
          f"(score: {analysis['risk_score']})")
    print(f"      URL:   {analysis['url'][:80]}")
    if analysis.get("title"):
        print(f"      Title: {analysis['title'][:80]}")
    for reason in analysis["reasons"]:
        print(f"      {color}> {reason}{RESET}")
    print()


def get_threat_summary(analyses: list[dict]) -> str:
    """Return a one-line threat summary."""
    danger = sum(1 for a in analyses if a["risk_level"] == "danger")
    warning = sum(1 for a in analyses if a["risk_level"] == "warning")
    if danger > 0:
        return f"DANGER: {danger} dangerous result(s) found"
    elif warning > 0:
        return f"WARNING: {warning} suspicious result(s) found"
    return "SAFE: No threats detected"

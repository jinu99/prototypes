"""터미널 리포트 출력 — severity별 색상 구분"""

from analyzer import Finding

# ANSI colors
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"

SEVERITY_STYLE = {
    "CRITICAL": (RED, "🔴"),
    "WARNING": (YELLOW, "🟡"),
    "INFO": (CYAN, "🔵"),
}


def print_report(findings: list[Finding], compose_file: str, live: bool = False):
    """findings를 터미널에 severity별로 출력한다."""
    print()
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  Docker Security Audit Report{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"  Compose: {compose_file}")
    print(f"  Mode:    {'Live (iptables/ufw)' if live else 'Compose-only (no firewall data)'}")
    print(f"{'=' * 70}")
    print()

    if not findings:
        print(f"  {GREEN}✓ 발견된 보안 문제가 없습니다.{RESET}")
        print()
        return

    # Group by severity
    by_severity = {"CRITICAL": [], "WARNING": [], "INFO": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)

    # Summary counts
    counts = {k: len(v) for k, v in by_severity.items()}
    summary_parts = []
    for sev in ["CRITICAL", "WARNING", "INFO"]:
        if counts.get(sev, 0) > 0:
            color, icon = SEVERITY_STYLE[sev]
            summary_parts.append(f"{color}{icon} {sev}: {counts[sev]}{RESET}")
    print(f"  Summary: {' │ '.join(summary_parts)}")
    print()

    # Print each severity group
    for sev in ["CRITICAL", "WARNING", "INFO"]:
        items = by_severity.get(sev, [])
        if not items:
            continue

        color, icon = SEVERITY_STYLE[sev]
        print(f"{color}{BOLD}  ── {sev} ({len(items)}) ──{RESET}")
        print()

        for i, f in enumerate(items, 1):
            print(f"  {color}{icon} [{f.category}] {f.message}{RESET}")
            if f.detail:
                # Wrap detail text
                lines = _wrap(f.detail, 64)
                for line in lines:
                    print(f"     {DIM}{line}{RESET}")
            if f.service != "(system)":
                print(f"     {DIM}서비스: {f.service}{RESET}")
            print()

    print(f"{'=' * 70}")
    total = sum(counts.values())
    critical = counts.get("CRITICAL", 0)
    if critical > 0:
        print(f"  {RED}{BOLD}⚠ {critical}개의 CRITICAL 이슈가 발견되었습니다. 즉시 조치가 필요합니다.{RESET}")
    else:
        print(f"  {GREEN}✓ CRITICAL 이슈 없음. 총 {total}개 발견.{RESET}")
    print(f"{'=' * 70}")
    print()


def _wrap(text: str, width: int) -> list[str]:
    """간단한 줄바꿈."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines

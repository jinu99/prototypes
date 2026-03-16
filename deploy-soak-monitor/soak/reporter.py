"""Terminal output formatting for soak monitor."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

from .models import Event, Pod, PodCondition, PodPhase
from .patterns import PatternMatch

# ANSI colors
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _ts() -> str:
    return time.strftime("%H:%M:%S")


class Reporter:
    """Handles all terminal output for the soak monitor."""

    def __init__(self) -> None:
        self.anomalies: list[str] = []
        self.events_seen: int = 0
        self.pods_monitored: set[str] = set()

    def banner(self, namespace: str, duration: int) -> None:
        print(f"\n{BOLD}{'═' * 60}{RESET}")
        print(f"{BOLD}{CYAN}  ☸ Soak Monitor{RESET}")
        print(f"{DIM}  Namespace: {namespace} | Window: {duration}s{RESET}")
        print(f"{BOLD}{'═' * 60}{RESET}\n")

    def event(self, evt: Event) -> None:
        self.events_seen += 1
        color = CYAN
        icon = "•"

        if evt.reason in ("PodOOMKilled",):
            color = RED
            icon = "✖"
        elif evt.reason in ("BackOff", "LogError"):
            color = RED
            icon = "✖"
        elif evt.reason == "DeploymentUpdated":
            color = YELLOW
            icon = "↻"
        elif evt.reason == "PodStarted":
            color = GREEN
            icon = "✓"
        elif evt.reason == "PodTerminated":
            color = DIM
            icon = "⊘"

        print(f"  {DIM}[{_ts()}]{RESET} {color}{icon} {evt.message}{RESET}")

    def anomaly(
        self,
        pod_name: str,
        anomaly_type: str,
        detail: str,
        deployment: str,
        namespace: str,
    ) -> None:
        msg = f"{anomaly_type}: {detail}"
        self.anomalies.append(msg)
        print()
        print(f"  {RED}{BOLD}{'─' * 56}{RESET}")
        print(f"  {RED}{BOLD}⚠  ANOMALY DETECTED{RESET}")
        print(f"  {RED}   Pod: {pod_name}{RESET}")
        print(f"  {RED}   Type: {anomaly_type}{RESET}")
        print(f"  {RED}   Detail: {detail}{RESET}")
        print()
        print(f"  {YELLOW}{BOLD}   💡 Suggested rollback:{RESET}")
        print(
            f"  {YELLOW}   $ kubectl rollout undo deployment/{deployment}"
            f" -n {namespace}{RESET}"
        )
        print(f"  {RED}{BOLD}{'─' * 56}{RESET}")
        print()

    def pattern_alert(self, pod_name: str, match: PatternMatch) -> None:
        color = RED if match.severity == "critical" else YELLOW
        icon = "✖" if match.severity == "critical" else "⚡"
        print(
            f"  {DIM}[{_ts()}]{RESET} {color}{icon} [{match.pattern_name}] "
            f"{pod_name}: {match.line.strip()}{RESET}"
        )

    def log_line(self, pod_name: str, line: str) -> None:
        print(f"  {DIM}[{_ts()}] 📋 {pod_name}: {line.strip()}{RESET}")

    def soak_progress(self, elapsed: int, total: int) -> None:
        pct = min(100, int(elapsed / total * 100))
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(
            f"\r  {DIM}Soak progress: [{bar}] {pct}% "
            f"({elapsed}s / {total}s){RESET}",
            end="",
            flush=True,
        )

    def all_clear(self, namespace: str, duration: int) -> None:
        print(f"\n\n{GREEN}{BOLD}{'═' * 60}{RESET}")
        print(f"{GREEN}{BOLD}  ✅ ALL CLEAR — Soak window completed{RESET}")
        print(f"{GREEN}  Namespace: {namespace}{RESET}")
        print(f"{GREEN}  Duration: {duration}s{RESET}")
        print(f"{GREEN}  Events observed: {self.events_seen}{RESET}")
        print(f"{GREEN}  Pods monitored: {len(self.pods_monitored)}{RESET}")
        print(f"{GREEN}  Anomalies: 0{RESET}")
        print(f"{GREEN}{BOLD}{'═' * 60}{RESET}\n")

    def summary_with_issues(self, namespace: str, duration: int) -> None:
        print(f"\n\n{RED}{BOLD}{'═' * 60}{RESET}")
        print(f"{RED}{BOLD}  ❌ SOAK FAILED — Issues detected{RESET}")
        print(f"{RED}  Namespace: {namespace}{RESET}")
        print(f"{RED}  Duration: {duration}s{RESET}")
        print(f"{RED}  Events observed: {self.events_seen}{RESET}")
        print(f"{RED}  Pods monitored: {len(self.pods_monitored)}{RESET}")
        print(f"{RED}  Anomalies: {len(self.anomalies)}{RESET}")
        for i, a in enumerate(self.anomalies, 1):
            print(f"{RED}    {i}. {a}{RESET}")
        print(f"{RED}{BOLD}{'═' * 60}{RESET}\n")

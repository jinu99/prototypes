"""Log file pattern matching plugin — scans log files for patterns."""

from __future__ import annotations

import re
from pathlib import Path
from models import Alert, Severity


class LogPatternPlugin:
    """Scans log files for regex patterns and generates alerts."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.path = Path(config["path"])
        self.patterns: list[dict] = config.get("patterns", [])
        self.tail_lines: int = config.get("tail_lines", 100)

    def poll(self) -> list[Alert]:
        if not self.path.exists():
            return [Alert(
                source=self.name,
                title=f"{self.name}: File not found",
                severity=Severity.WARNING,
                message=f"Log file {self.path} does not exist",
            )]

        try:
            lines = self.path.read_text().splitlines()[-self.tail_lines:]
        except PermissionError:
            return [Alert(
                source=self.name,
                title=f"{self.name}: Permission denied",
                severity=Severity.WARNING,
                message=f"Cannot read {self.path}",
            )]

        alerts: list[Alert] = []
        for pat_cfg in self.patterns:
            regex = re.compile(pat_cfg["regex"])
            sev = Severity.from_str(pat_cfg.get("severity", "warning"))
            matches = [line for line in lines if regex.search(line)]
            if matches:
                alerts.append(Alert(
                    source=self.name,
                    title=f"{self.name}: {len(matches)} match(es) for '{pat_cfg['regex']}'",
                    severity=sev,
                    message=f"Last match: {matches[-1][:200]}",
                    metadata={"pattern": pat_cfg["regex"], "count": len(matches)},
                ))

        if not alerts:
            alerts.append(Alert(
                source=self.name,
                title=f"{self.name}: No issues found",
                severity=Severity.OK,
                message=f"Scanned last {min(len(lines), self.tail_lines)} lines of {self.path}",
            ))
        return alerts

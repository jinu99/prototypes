"""Error pattern matching for log analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PatternMatch:
    pattern_name: str
    severity: str  # "warning", "error", "critical"
    matched_text: str
    line: str


# Default error patterns — regex-based
DEFAULT_PATTERNS: list[tuple[str, str, str]] = [
    # (name, severity, regex)
    ("panic", "critical", r"(?i)panic:"),
    ("fatal", "critical", r"(?i)\bFATAL\b"),
    ("oom", "critical", r"(?i)out of memory|OOMKilled"),
    ("null_pointer", "error", r"(?i)NullPointer|nil pointer"),
    ("connection_refused", "error", r"(?i)connection refused"),
    ("timeout", "error", r"(?i)timeout|timed?\s*out"),
    ("exception", "error", r"(?i)exception:|traceback"),
    ("error_generic", "warning", r"(?i)\bERROR\b"),
    ("exit_nonzero", "warning", r"exit code [1-9]"),
]


class PatternMatcher:
    def __init__(
        self, extra_patterns: list[tuple[str, str, str]] | None = None
    ) -> None:
        patterns = DEFAULT_PATTERNS + (extra_patterns or [])
        self._compiled = [
            (name, severity, re.compile(regex))
            for name, severity, regex in patterns
        ]

    def match(self, line: str) -> list[PatternMatch]:
        matches = []
        for name, severity, regex in self._compiled:
            m = regex.search(line)
            if m:
                matches.append(PatternMatch(
                    pattern_name=name,
                    severity=severity,
                    matched_text=m.group(),
                    line=line,
                ))
        return matches

    def match_severity(self, line: str) -> str | None:
        """Return highest severity found, or None."""
        matches = self.match(line)
        if not matches:
            return None
        priority = {"critical": 3, "error": 2, "warning": 1}
        return max(matches, key=lambda m: priority.get(m.severity, 0)).severity

"""Entropy-based and regex-based secret detection in text streams."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


# Common secret patterns (regex)
SECRET_PATTERNS = [
    re.compile(r'\b(sk-[A-Za-z0-9]{20,})\b'),                    # OpenAI-style
    re.compile(r'\b(pk-[A-Za-z0-9]{20,})\b'),                    # Public keys
    re.compile(r'\b(ghp_[A-Za-z0-9]{36,})\b'),                   # GitHub PAT
    re.compile(r'\b(gho_[A-Za-z0-9]{36,})\b'),                   # GitHub OAuth
    re.compile(r'\b(xoxb-[A-Za-z0-9\-]{20,})\b'),                # Slack bot
    re.compile(r'\b(xoxp-[A-Za-z0-9\-]{20,})\b'),                # Slack user
    re.compile(r'\b(AKIA[0-9A-Z]{16})\b'),                       # AWS access key
    re.compile(r'\b([A-Za-z0-9+/]{40,}={0,2})\b'),               # Base64 long strings
    re.compile(r'\b(eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+)\b'), # JWT tokens
    re.compile(r'://[^:]+:([^@\s]{8,})@'),                       # Connection URL passwords
]

# Minimum entropy threshold for Shannon entropy detection
ENTROPY_THRESHOLD = 3.5
# Minimum length for entropy-based detection
MIN_ENTROPY_LENGTH = 16
# Token split pattern — look at words/tokens in the text
TOKEN_PATTERN = re.compile(r'[A-Za-z0-9+/_\-]{12,}')


def shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


@dataclass
class Detection:
    """A detected secret occurrence."""
    original: str
    source: str  # "registry", "pattern", "entropy"
    key: str | None = None  # registry key if from registry


@dataclass
class SecretDetector:
    """Detects secrets in text using registry lookup, regex patterns, and entropy."""

    registry_values: list[str] = field(default_factory=list)
    enable_entropy: bool = True
    enable_patterns: bool = True
    _stats: dict[str, int] = field(default_factory=lambda: {
        "registry_hits": 0,
        "pattern_hits": 0,
        "entropy_hits": 0,
    })

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def detect_in_line(self, line: str) -> list[Detection]:
        """Find all secret occurrences in a single line of text."""
        detections: list[Detection] = []
        seen: set[str] = set()

        # 1. Registry-based: exact match of known secret values
        for value in self.registry_values:
            if value in line and value not in seen:
                detections.append(Detection(original=value, source="registry"))
                seen.add(value)
                self._stats["registry_hits"] += 1

        # 2. Pattern-based: regex matches
        if self.enable_patterns:
            for pattern in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    value = match.group(1)
                    if value not in seen:
                        detections.append(Detection(original=value, source="pattern"))
                        seen.add(value)
                        self._stats["pattern_hits"] += 1

        # 3. Entropy-based: high-entropy tokens
        if self.enable_entropy:
            for match in TOKEN_PATTERN.finditer(line):
                token = match.group(0)
                if token in seen or len(token) < MIN_ENTROPY_LENGTH:
                    continue
                entropy = shannon_entropy(token)
                if entropy >= ENTROPY_THRESHOLD:
                    # Avoid false positives on common words/paths
                    if not self._is_likely_false_positive(token):
                        detections.append(Detection(original=token, source="entropy"))
                        seen.add(token)
                        self._stats["entropy_hits"] += 1

        return detections

    @staticmethod
    def _is_likely_false_positive(token: str) -> bool:
        """Filter out tokens that are unlikely to be secrets."""
        lower = token.lower()
        # Common non-secret patterns
        if lower in ("node_modules", "package-lock", "requirements"):
            return True
        # Paths with slashes
        if "/" in token or "\\" in token:
            return True
        # All same case with no digits — likely a regular word
        if token.isalpha() and (token.islower() or token.isupper()):
            return True
        # ENV_VAR_NAME pattern (ALL_CAPS_WITH_UNDERSCORES) — not a secret value
        if re.match(r'^[A-Z][A-Z0-9_]{3,}$', token):
            return True
        return False

    def stats_summary(self) -> str:
        return (
            f"Detection stats: "
            f"registry={self._stats['registry_hits']}, "
            f"pattern={self._stats['pattern_hits']}, "
            f"entropy={self._stats['entropy_hits']}"
        )

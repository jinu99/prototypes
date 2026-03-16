"""Core data models for the alert digest system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Protocol, runtime_checkable


class Severity(IntEnum):
    """Alert severity levels, ordered by urgency (higher = more severe)."""
    OK = 0
    INFO = 1
    WARNING = 2
    CRITICAL = 3

    @classmethod
    def from_str(cls, s: str) -> "Severity":
        return cls[s.upper()]


@dataclass
class Alert:
    """A single alert from a monitoring source."""
    source: str
    title: str
    severity: Severity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class SourcePlugin(Protocol):
    """Protocol that all source plugins must satisfy."""
    name: str

    def poll(self) -> list[Alert]:
        """Poll the source and return alerts."""
        ...

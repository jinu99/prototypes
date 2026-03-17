"""Data models for oncall gap predetector."""

from dataclasses import dataclass, field
from enum import Enum


class ServiceType(Enum):
    HTTP = "http"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    MONITORING = "monitoring"
    UNKNOWN = "unknown"


@dataclass
class Service:
    name: str
    image: str
    ports: list[int] = field(default_factory=list)
    service_type: ServiceType = ServiceType.UNKNOWN


@dataclass
class MonitoringTarget:
    job_name: str
    targets: list[str] = field(default_factory=list)
    metrics_path: str = "/metrics"
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    alert_name: str
    expr: str
    labels: dict[str, str] = field(default_factory=dict)
    service: str = ""


@dataclass
class GapReport:
    service_name: str
    service_type: ServiceType
    is_monitored: bool
    existing_alerts: list[str] = field(default_factory=list)
    missing_metrics: list[str] = field(default_factory=list)
    required_metrics: list[str] = field(default_factory=list)
    coverage_pct: float = 0.0

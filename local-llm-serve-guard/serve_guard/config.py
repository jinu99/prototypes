"""Configuration loader from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class VramConfig:
    poll_interval_seconds: float = 2.0
    threshold_percent: float = 85.0
    critical_percent: float = 95.0


@dataclass
class AdmissionConfig:
    max_queue_size: int = 50
    queue_timeout_seconds: float = 30.0


@dataclass
class BackendConfig:
    name: str = "local-ollama"
    url: str = "http://localhost:11434"
    priority: int = 1
    healthcheck_path: str = "/api/tags"
    healthcheck_interval_seconds: float = 10.0


@dataclass
class ProxyConfig:
    host: str = "0.0.0.0"
    port: int = 8780


@dataclass
class MetricsConfig:
    db_path: str = "metrics.db"
    retention_hours: int = 24


@dataclass
class AppConfig:
    vram: VramConfig = field(default_factory=VramConfig)
    admission: AdmissionConfig = field(default_factory=AdmissionConfig)
    backends: list[BackendConfig] = field(default_factory=list)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    path = Path(path)
    if not path.exists():
        return AppConfig()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    cfg = AppConfig()
    if "vram" in raw:
        cfg.vram = VramConfig(**raw["vram"])
    if "admission" in raw:
        cfg.admission = AdmissionConfig(**raw["admission"])
    if "backends" in raw:
        cfg.backends = [BackendConfig(**b) for b in raw["backends"]]
    if "proxy" in raw:
        cfg.proxy = ProxyConfig(**raw["proxy"])
    if "metrics" in raw:
        cfg.metrics = MetricsConfig(**raw["metrics"])

    if not cfg.backends:
        cfg.backends = [BackendConfig()]

    return cfg

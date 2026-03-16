"""Polling engine — loads config, instantiates plugins, collects alerts."""

from __future__ import annotations

from pathlib import Path
import yaml

from models import Alert
from plugins import PLUGIN_REGISTRY


def load_config(config_path: Path) -> dict:
    """Load and validate YAML configuration."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not config or "sources" not in config:
        raise ValueError("Config must contain a 'sources' section")
    return config


def poll_all(config: dict) -> list[Alert]:
    """Instantiate all configured source plugins and poll them."""
    alerts: list[Alert] = []
    for source_cfg in config["sources"]:
        source_type = source_cfg["type"]
        source_name = source_cfg["name"]

        plugin_cls = PLUGIN_REGISTRY.get(source_type)
        if plugin_cls is None:
            raise ValueError(
                f"Unknown source type '{source_type}'. "
                f"Available: {', '.join(PLUGIN_REGISTRY.keys())}"
            )

        plugin = plugin_cls(name=source_name, config=source_cfg.get("config", {}))
        try:
            source_alerts = plugin.poll()
            alerts.extend(source_alerts)
        except Exception as e:
            from models import Severity
            alerts.append(Alert(
                source=source_name,
                title=f"{source_name}: Plugin error",
                severity=Severity.WARNING,
                message=f"Error polling {source_name}: {e}",
            ))
    return alerts

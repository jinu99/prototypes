"""Prometheus mock plugin — demonstrates plugin extensibility.

This plugin simulates Prometheus API responses with mock data,
showing how a new source can be added with just one Python file
and a YAML config entry.
"""

from __future__ import annotations

import random
from models import Alert, Severity


class PrometheusMockPlugin:
    """Mock Prometheus plugin that generates simulated metric alerts."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.alerts_config: list[dict] = config.get("mock_alerts", [])

    def poll(self) -> list[Alert]:
        if not self.alerts_config:
            # Generate random demo alerts
            return self._generate_demo_alerts()

        alerts = []
        for acfg in self.alerts_config:
            alerts.append(Alert(
                source=self.name,
                title=acfg.get("title", f"{self.name}: Alert"),
                severity=Severity.from_str(acfg.get("severity", "warning")),
                message=acfg.get("message", "Mock Prometheus alert"),
                metadata={"metric": acfg.get("metric", "unknown")},
            ))
        return alerts

    def _generate_demo_alerts(self) -> list[Alert]:
        """Generate random demo alerts to simulate Prometheus."""
        demos = [
            ("CPU usage > 90%", Severity.CRITICAL, "node_cpu_usage", "Host server-01 CPU at 94%"),
            ("Memory usage > 80%", Severity.WARNING, "node_memory_usage", "Host server-02 memory at 83%"),
            ("Disk space OK", Severity.OK, "node_disk_usage", "All hosts below 60% disk usage"),
        ]
        alerts = []
        for title, sev, metric, msg in demos:
            alerts.append(Alert(
                source=self.name,
                title=f"{self.name}: {title}",
                severity=sev,
                message=msg,
                metadata={"metric": metric},
            ))
        return alerts

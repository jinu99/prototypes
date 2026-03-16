"""Jinja2 markdown digest renderer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from models import Alert, Severity

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_digest(alerts: list[Alert], template_name: str = "digest.md.j2") -> str:
    """Render alerts into a markdown digest using Jinja2."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["severity_icon"] = _severity_icon
    env.filters["severity_label"] = _severity_label

    # Sort by severity descending (critical first)
    sorted_alerts = sorted(alerts, key=lambda a: a.severity, reverse=True)

    # Group by severity
    groups: dict[Severity, list[Alert]] = {}
    for alert in sorted_alerts:
        groups.setdefault(alert.severity, []).append(alert)

    # Count stats
    stats = {
        "total": len(alerts),
        "critical": len(groups.get(Severity.CRITICAL, [])),
        "warning": len(groups.get(Severity.WARNING, [])),
        "ok": len(groups.get(Severity.OK, [])),
        "info": len(groups.get(Severity.INFO, [])),
    }

    template = env.get_template(template_name)
    return template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        groups=groups,
        stats=stats,
        Severity=Severity,
    )


def _severity_icon(severity: Severity) -> str:
    return {
        Severity.CRITICAL: "🔴",
        Severity.WARNING: "🟡",
        Severity.INFO: "🔵",
        Severity.OK: "🟢",
    }.get(severity, "⚪")


def _severity_label(severity: Severity) -> str:
    return severity.name

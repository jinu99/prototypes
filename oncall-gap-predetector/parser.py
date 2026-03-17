"""Parse Docker Compose, Prometheus, and alert rule YAML files."""

from pathlib import Path

import yaml

from models import AlertRule, MonitoringTarget, Service


def parse_docker_compose(path: Path) -> list[Service]:
    """Extract services from a Docker Compose file."""
    data = yaml.safe_load(path.read_text())
    services = []

    for name, config in (data.get("services") or {}).items():
        image = config.get("image", "")
        ports = _extract_ports(config.get("ports", []))
        services.append(Service(name=name, image=image, ports=ports))

    return services


def _extract_ports(ports_config: list) -> list[int]:
    """Extract container ports from various Docker Compose port formats."""
    result = []
    for entry in ports_config:
        if isinstance(entry, str):
            # "8080:8080" or "8080"
            parts = entry.split(":")
            container_port = parts[-1].split("/")[0]  # strip /tcp /udp
            try:
                result.append(int(container_port))
            except ValueError:
                pass
        elif isinstance(entry, dict):
            # {target: 8080, published: 8080}
            target = entry.get("target")
            if target is not None:
                result.append(int(target))
        elif isinstance(entry, int):
            result.append(entry)
    return result


def parse_prometheus_config(path: Path) -> list[MonitoringTarget]:
    """Extract scrape targets from a Prometheus config file."""
    data = yaml.safe_load(path.read_text())
    targets = []

    for scrape in data.get("scrape_configs", []):
        job_name = scrape.get("job_name", "")
        metrics_path = scrape.get("metrics_path", "/metrics")
        all_targets = []
        all_labels = {}

        for static in scrape.get("static_configs", []):
            all_targets.extend(static.get("targets", []))
            all_labels.update(static.get("labels", {}))

        targets.append(MonitoringTarget(
            job_name=job_name,
            targets=all_targets,
            metrics_path=metrics_path,
            labels=all_labels,
        ))

    return targets


def parse_alert_rules(path: Path) -> list[AlertRule]:
    """Extract alert rules from a Prometheus alert rules file."""
    data = yaml.safe_load(path.read_text())
    rules = []

    for group in data.get("groups", []):
        for rule in group.get("rules", []):
            if "alert" not in rule:
                continue
            labels = rule.get("labels", {})
            rules.append(AlertRule(
                alert_name=rule["alert"],
                expr=rule.get("expr", ""),
                labels=labels,
                service=labels.get("service", ""),
            ))

    return rules

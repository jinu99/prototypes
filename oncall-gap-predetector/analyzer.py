"""Service type inference and monitoring gap analysis."""

from models import (
    AlertRule,
    GapReport,
    MonitoringTarget,
    Service,
    ServiceType,
)

# --- Service Type Inference ---

IMAGE_TYPE_MAP: dict[str, ServiceType] = {
    "postgres": ServiceType.DATABASE,
    "mysql": ServiceType.DATABASE,
    "mariadb": ServiceType.DATABASE,
    "mongo": ServiceType.DATABASE,
    "redis": ServiceType.CACHE,
    "memcached": ServiceType.CACHE,
    "rabbitmq": ServiceType.QUEUE,
    "kafka": ServiceType.QUEUE,
    "nats": ServiceType.QUEUE,
    "nginx": ServiceType.HTTP,
    "traefik": ServiceType.HTTP,
    "caddy": ServiceType.HTTP,
    "haproxy": ServiceType.HTTP,
    "prometheus": ServiceType.MONITORING,
    "grafana": ServiceType.MONITORING,
    "alertmanager": ServiceType.MONITORING,
}

PORT_TYPE_MAP: dict[int, ServiceType] = {
    80: ServiceType.HTTP,
    443: ServiceType.HTTP,
    8080: ServiceType.HTTP,
    3000: ServiceType.HTTP,
    5432: ServiceType.DATABASE,
    3306: ServiceType.DATABASE,
    27017: ServiceType.DATABASE,
    6379: ServiceType.CACHE,
    11211: ServiceType.CACHE,
    5672: ServiceType.QUEUE,
    9092: ServiceType.QUEUE,
    9090: ServiceType.MONITORING,
}

# --- Required Metrics per Service Type ---

REQUIRED_METRICS: dict[ServiceType, list[str]] = {
    ServiceType.HTTP: [
        "up",
        "http_requests_total",
        "http_request_duration_seconds",
        "http_errors_total",
    ],
    ServiceType.DATABASE: [
        "up",
        "db_connections_active",
        "replication_lag",
        "slow_queries",
        "db_size_bytes",
    ],
    ServiceType.CACHE: [
        "up",
        "memory_usage_bytes",
        "hit_rate",
        "evictions_total",
        "connected_clients",
    ],
    ServiceType.QUEUE: [
        "up",
        "queue_depth",
        "consumer_lag",
        "message_publish_rate",
        "message_consume_rate",
    ],
    ServiceType.MONITORING: [
        "up",
    ],
}


def infer_service_type(image: str, ports: list[int]) -> ServiceType:
    """Infer service type from Docker image name and exposed ports."""
    image_lower = image.lower()
    for keyword, stype in IMAGE_TYPE_MAP.items():
        if keyword in image_lower:
            return stype

    for port in ports:
        if port in PORT_TYPE_MAP:
            return PORT_TYPE_MAP[port]

    return ServiceType.UNKNOWN


def _match_service_to_targets(
    service: Service, targets: list[MonitoringTarget]
) -> bool:
    """Check if a service is covered by any Prometheus scrape target."""
    name = service.name.lower()

    for target in targets:
        # Match by job name
        if name in target.job_name.lower():
            return True
        # Match by label
        if target.labels.get("service", "").lower() == name:
            return True
        # Match by target hostname
        for t in target.targets:
            host = t.split(":")[0].lower()
            if name in host:
                return True

    return False


def _find_alerts_for_service(
    service: Service, rules: list[AlertRule]
) -> list[str]:
    """Find alert rules that reference a given service."""
    matched = []
    name = service.name.lower()

    for rule in rules:
        # Match by explicit service label
        if rule.service.lower() == name:
            matched.append(rule.alert_name)
            continue
        # Match by service name appearing in the expression
        if name in rule.expr.lower():
            matched.append(rule.alert_name)
            continue
        # Match by job name reference in expression
        if f'job="{name}"' in rule.expr.lower():
            matched.append(rule.alert_name)

    return matched


def _metric_covered_by_alert(metric: str, alerts: list[str], rules: list[AlertRule]) -> bool:
    """Check if a required metric is covered by any of the matched alerts."""
    metric_lower = metric.lower()
    # Map generic metric names to common PromQL patterns
    metric_patterns = {
        "up": ["up"],
        "http_requests_total": ["http_requests_total", "request_total", "requests_total"],
        "http_request_duration_seconds": ["duration", "latency", "response_time"],
        "http_errors_total": ["error", "5xx", "status=~\"5"],
        "db_connections_active": ["connection", "conn"],
        "replication_lag": ["replication", "lag"],
        "slow_queries": ["slow_quer"],
        "db_size_bytes": ["db_size", "database_size"],
        "memory_usage_bytes": ["memory"],
        "hit_rate": ["hit_rate", "hit_ratio"],
        "evictions_total": ["evict"],
        "connected_clients": ["connected_client", "client_count"],
        "queue_depth": ["queue_depth", "queue_length", "queue_size"],
        "consumer_lag": ["consumer_lag", "consumer_offset"],
        "message_publish_rate": ["publish", "produced"],
        "message_consume_rate": ["consume", "delivered"],
    }

    patterns = metric_patterns.get(metric_lower, [metric_lower])

    for alert_name in alerts:
        # Find the full rule to check its expression
        for rule in rules:
            if rule.alert_name == alert_name:
                expr_lower = rule.expr.lower()
                alert_lower = alert_name.lower()
                for pattern in patterns:
                    if pattern in expr_lower or pattern in alert_lower:
                        return True
    return False


def analyze_gaps(
    services: list[Service],
    targets: list[MonitoringTarget],
    rules: list[AlertRule],
) -> list[GapReport]:
    """Analyze monitoring gaps for all services."""
    reports = []

    for svc in services:
        svc.service_type = infer_service_type(svc.image, svc.ports)
        is_monitored = _match_service_to_targets(svc, targets)
        existing_alerts = _find_alerts_for_service(svc, rules)
        required = REQUIRED_METRICS.get(svc.service_type, ["up"])

        missing = []
        for metric in required:
            if not _metric_covered_by_alert(metric, existing_alerts, rules):
                missing.append(metric)

        coverage = (
            (len(required) - len(missing)) / len(required) * 100
            if required
            else 100.0
        )

        reports.append(GapReport(
            service_name=svc.name,
            service_type=svc.service_type,
            is_monitored=is_monitored,
            existing_alerts=existing_alerts,
            missing_metrics=missing,
            required_metrics=required,
            coverage_pct=round(coverage, 1),
        ))

    return reports

"""Source plugins for alert polling."""

from plugins.http_check import HttpCheckPlugin
from plugins.log_pattern import LogPatternPlugin
from plugins.docker_status import DockerStatusPlugin
from plugins.prometheus_mock import PrometheusMockPlugin

PLUGIN_REGISTRY: dict[str, type] = {
    "http_check": HttpCheckPlugin,
    "log_pattern": LogPatternPlugin,
    "docker_status": DockerStatusPlugin,
    "prometheus_mock": PrometheusMockPlugin,
}

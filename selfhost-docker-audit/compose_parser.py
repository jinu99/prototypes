"""Docker Compose YAML 파서 — 보안 관련 설정 추출"""

import re
from pathlib import Path
from typing import Any

import yaml


def parse_compose_file(path: str) -> dict:
    """docker-compose.yml을 파싱하여 보안 관련 정보를 추출한다."""
    compose_path = Path(path)
    if not compose_path.exists():
        raise FileNotFoundError(f"Compose file not found: {path}")

    with open(compose_path) as f:
        data = yaml.safe_load(f)

    if not data or "services" not in data:
        raise ValueError(f"Invalid compose file (no services): {path}")

    services = {}
    for name, svc in data["services"].items():
        services[name] = parse_service(name, svc)

    return {"file": str(compose_path.resolve()), "services": services}


def parse_service(name: str, svc: dict) -> dict:
    """개별 서비스의 보안 관련 설정을 추출한다."""
    return {
        "ports": parse_ports(svc.get("ports", [])),
        "network_mode": svc.get("network_mode"),
        "privileged": svc.get("privileged", False),
        "cap_add": svc.get("cap_add", []),
        "environment": detect_secrets(svc.get("environment", {})),
        "volumes": svc.get("volumes", []),
        "image": svc.get("image", ""),
        "restart": svc.get("restart", ""),
    }


def parse_ports(ports: list) -> list[dict]:
    """포트 매핑을 정규화한다.

    형식: "host_ip:host_port:container_port/protocol"
    예: "8080:80", "0.0.0.0:3000:3000", "127.0.0.1:5432:5432/tcp"
    """
    result = []
    for p in ports:
        if isinstance(p, dict):
            # long syntax
            result.append({
                "host_ip": p.get("host_ip", "0.0.0.0"),
                "host_port": str(p.get("published", "")),
                "container_port": str(p.get("target", "")),
                "protocol": p.get("protocol", "tcp"),
                "raw": str(p),
            })
            continue

        p = str(p)
        protocol = "tcp"
        if "/" in p:
            p, protocol = p.rsplit("/", 1)

        parts = p.split(":")
        if len(parts) == 3:
            host_ip, host_port, container_port = parts
        elif len(parts) == 2:
            host_ip = "0.0.0.0"
            host_port, container_port = parts
        else:
            host_ip = "0.0.0.0"
            host_port = container_port = parts[0]

        # Handle port ranges
        result.append({
            "host_ip": host_ip,
            "host_port": host_port,
            "container_port": container_port,
            "protocol": protocol,
            "raw": str(p),
        })

    return result


SECRET_PATTERNS = [
    re.compile(r"(password|passwd|secret|token|api.?key|credentials)", re.I),
]


def detect_secrets(env: Any) -> list[dict]:
    """환경 변수에서 하드코딩된 시크릿을 탐지한다."""
    findings = []
    items = []

    if isinstance(env, dict):
        items = list(env.items())
    elif isinstance(env, list):
        for item in env:
            if "=" in str(item):
                k, v = str(item).split("=", 1)
                items.append((k, v))
            else:
                items.append((str(item), ""))

    for key, value in items:
        value = str(value)
        # Skip variable references like ${VAR} or $VAR
        if not value or value.startswith("${") or value.startswith("$"):
            continue

        # Check key name against secret patterns
        for pattern in SECRET_PATTERNS:
            if pattern.search(key):
                masked = value[:2] + "***" if len(value) > 2 else "***"
                findings.append({
                    "key": key,
                    "masked_value": masked,
                    "raw_key": key,
                })
                break

        # Check for credentials embedded in URLs (e.g. postgresql://user:pass@host)
        url_cred = re.search(r"://([^:]+):([^@]+)@", value)
        if url_cred:
            user, passwd = url_cred.groups()
            masked = passwd[:2] + "***" if len(passwd) > 2 else "***"
            findings.append({
                "key": f"{key} (URL embedded)",
                "masked_value": f"{user}:{masked}",
                "raw_key": key,
            })

    return findings

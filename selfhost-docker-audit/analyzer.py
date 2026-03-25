"""교차 분석 엔진 — Compose 선언 vs iptables 실제 vs UFW 규칙 비교"""

from dataclasses import dataclass, field


@dataclass
class Finding:
    severity: str  # CRITICAL, WARNING, INFO
    category: str
    service: str
    message: str
    detail: str = ""


def analyze(compose_data: dict, iptables_nat: list, iptables_filter: list, ufw: dict, has_firewall: bool = False) -> list[Finding]:
    """모든 분석을 수행하고 Finding 리스트를 반환한다."""
    findings = []

    findings.extend(check_compose_security(compose_data))
    if has_firewall:
        findings.extend(check_port_exposure(compose_data, iptables_nat, ufw))
        findings.extend(check_ufw_bypass(compose_data, iptables_nat, ufw))
        findings.extend(check_docker_user_chain(iptables_filter))
        findings.extend(check_undeclared_ports(compose_data, iptables_nat))

    # Sort by severity
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    findings.sort(key=lambda f: severity_order.get(f.severity, 9))

    return findings


def check_compose_security(compose_data: dict) -> list[Finding]:
    """Compose 파일 자체의 보안 문제를 검사한다."""
    findings = []

    for name, svc in compose_data["services"].items():
        # Privileged mode
        if svc["privileged"]:
            findings.append(Finding(
                severity="CRITICAL",
                category="privileged_mode",
                service=name,
                message=f"서비스 '{name}'이 privileged 모드로 실행됨",
                detail="컨테이너가 호스트의 모든 디바이스와 커널 기능에 접근 가능. 탈출 시 호스트 전체 장악 위험.",
            ))

        # Host network mode
        if svc["network_mode"] == "host":
            findings.append(Finding(
                severity="CRITICAL",
                category="host_network",
                service=name,
                message=f"서비스 '{name}'이 host 네트워크 모드 사용",
                detail="컨테이너가 호스트 네트워크 스택을 직접 사용. 모든 컨테이너 포트가 호스트에 바인딩됨.",
            ))

        # Dangerous capabilities
        dangerous_caps = {"SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "ALL"}
        added_caps = set(svc["cap_add"])
        risky_caps = added_caps & dangerous_caps
        if risky_caps:
            findings.append(Finding(
                severity="WARNING",
                category="dangerous_capability",
                service=name,
                message=f"서비스 '{name}'에 위험한 capability 추가: {', '.join(risky_caps)}",
                detail="이 capability는 컨테이너 격리를 약화시킴.",
            ))

        # Hardcoded secrets
        for secret in svc["environment"]:
            findings.append(Finding(
                severity="WARNING",
                category="hardcoded_secret",
                service=name,
                message=f"서비스 '{name}'에 시크릿 하드코딩: {secret['key']}={secret['masked_value']}",
                detail="환경 변수에 시크릿을 하드코딩하면 git history에 노출됨. Docker secrets 또는 .env 파일 사용 권장.",
            ))

        # 0.0.0.0 binding
        for port in svc["ports"]:
            if port["host_ip"] == "0.0.0.0":
                findings.append(Finding(
                    severity="INFO",
                    category="wildcard_binding",
                    service=name,
                    message=f"서비스 '{name}'의 포트 {port['host_port']} → {port['container_port']}이 0.0.0.0에 바인딩",
                    detail="모든 인터페이스에서 접근 가능. 내부 전용이면 127.0.0.1로 제한 권장.",
                ))

    return findings


def check_port_exposure(compose_data: dict, iptables_nat: list, ufw: dict) -> list[Finding]:
    """Compose 포트와 iptables 실제 규칙을 비교한다."""
    findings = []

    # Build set of iptables exposed ports
    iptables_ports = {rule["host_port"] for rule in iptables_nat}

    for name, svc in compose_data["services"].items():
        for port in svc["ports"]:
            try:
                host_port = int(port["host_port"])
            except (ValueError, TypeError):
                continue

            if host_port in iptables_ports:
                findings.append(Finding(
                    severity="INFO",
                    category="port_confirmed",
                    service=name,
                    message=f"서비스 '{name}'의 포트 {host_port} → iptables DNAT 규칙 확인됨",
                    detail="Compose 선언과 iptables 규칙이 일치.",
                ))

    return findings


def check_ufw_bypass(compose_data: dict, iptables_nat: list, ufw: dict) -> list[Finding]:
    """UFW에서 차단했지만 Docker가 우회하여 열려있는 포트를 탐지한다.

    핵심 로직: UFW default deny + 특정 포트 미허용인데,
    Docker iptables에서 해당 포트가 DNAT으로 열려있으면 → CRITICAL
    """
    findings = []

    if not ufw["active"]:
        findings.append(Finding(
            severity="WARNING",
            category="ufw_inactive",
            service="(system)",
            message="UFW가 비활성화 상태",
            detail="호스트 방화벽이 꺼져있어 Docker 포트가 외부에 직접 노출됨.",
        ))
        return findings

    # UFW allowed ports
    ufw_allowed = set()
    for rule in ufw["rules"]:
        if rule["action"] == "ALLOW" and rule["port"] is not None:
            ufw_allowed.add(rule["port"])

    # UFW denied ports (explicit deny)
    ufw_denied = set()
    for rule in ufw["rules"]:
        if rule["action"] in ("DENY", "REJECT") and rule["port"] is not None:
            ufw_denied.add(rule["port"])

    # iptables exposed ports via Docker
    iptables_ports = {rule["host_port"] for rule in iptables_nat}

    # Cross-reference with compose services
    for name, svc in compose_data["services"].items():
        for port in svc["ports"]:
            try:
                host_port = int(port["host_port"])
            except (ValueError, TypeError):
                continue

            # 127.0.0.1 바인딩은 외부 노출 아님 → skip
            if port["host_ip"] == "127.0.0.1":
                continue

            in_iptables = host_port in iptables_ports
            in_ufw_allow = host_port in ufw_allowed

            if in_iptables and not in_ufw_allow:
                # Docker opened this port but UFW didn't explicitly allow it
                if ufw["default_incoming"] == "deny":
                    severity = "CRITICAL"
                    if host_port in ufw_denied:
                        msg = (
                            f"서비스 '{name}'의 포트 {host_port}: "
                            f"UFW에서 명시적 DENY인데 Docker가 우회하여 외부 노출!"
                        )
                    else:
                        msg = (
                            f"서비스 '{name}'의 포트 {host_port}: "
                            f"UFW default deny인데 Docker가 iptables를 직접 조작하여 외부 노출!"
                        )
                    findings.append(Finding(
                        severity=severity,
                        category="ufw_bypass",
                        service=name,
                        message=msg,
                        detail=(
                            "Docker는 iptables의 DOCKER 체인을 직접 조작하므로 UFW 규칙을 우회함. "
                            "DOCKER-USER 체인에서 차단하거나, 포트를 127.0.0.1로 바인딩하거나, "
                            "docker daemon에 --iptables=false 설정 필요."
                        ),
                    ))

    return findings


def check_docker_user_chain(iptables_filter: list) -> list[Finding]:
    """DOCKER-USER 체인 설정 상태를 검사한다."""
    findings = []

    if not iptables_filter:
        findings.append(Finding(
            severity="INFO",
            category="docker_user_empty",
            service="(system)",
            message="DOCKER-USER 체인에 사용자 정의 규칙 없음",
            detail=(
                "DOCKER-USER 체인은 Docker 트래픽을 제어할 수 있는 유일한 체인. "
                "외부 접근 제한이 필요하면 여기에 DROP/REJECT 규칙 추가 권장."
            ),
        ))

    # Check if DOCKER-USER has only RETURN (default)
    if all(r["action"] == "RETURN" for r in iptables_filter):
        findings.append(Finding(
            severity="WARNING",
            category="docker_user_default",
            service="(system)",
            message="DOCKER-USER 체인이 기본 상태(RETURN만 존재) — Docker 포트 필터링 미설정",
            detail="모든 Docker 포트 트래픽이 필터링 없이 통과됨.",
        ))

    return findings


def check_undeclared_ports(compose_data: dict, iptables_nat: list) -> list[Finding]:
    """iptables에는 있지만 Compose에 선언되지 않은 포트를 찾는다."""
    findings = []

    # Compose declared ports
    compose_ports = set()
    for name, svc in compose_data["services"].items():
        for port in svc["ports"]:
            try:
                compose_ports.add(int(port["host_port"]))
            except (ValueError, TypeError):
                continue

    # iptables ports
    for rule in iptables_nat:
        if rule["host_port"] not in compose_ports:
            findings.append(Finding(
                severity="WARNING",
                category="undeclared_port",
                service="(unknown)",
                message=f"iptables에 포트 {rule['host_port']}의 DNAT 규칙이 있으나 분석 대상 Compose에 미선언",
                detail=f"다른 Compose 파일이나 직접 실행된 컨테이너일 수 있음. 규칙: {rule['raw']}",
            ))

    return findings

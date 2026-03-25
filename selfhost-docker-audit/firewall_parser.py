"""iptables / UFW 출력 파서 — DOCKER 체인 및 UFW 규칙 추출"""

import re
import subprocess


def capture_iptables_nat() -> str:
    """iptables -L -n -t nat 출력을 캡처한다."""
    try:
        result = subprocess.run(
            ["sudo", "iptables", "-L", "-n", "-t", "nat"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError(f"iptables 실행 실패: {e}")


def capture_iptables_filter() -> str:
    """iptables -L -n (filter table) 출력을 캡처한다."""
    try:
        result = subprocess.run(
            ["sudo", "iptables", "-L", "-n"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError(f"iptables 실행 실패: {e}")


def capture_ufw_status() -> str:
    """ufw status verbose 출력을 캡처한다."""
    try:
        result = subprocess.run(
            ["sudo", "ufw", "status", "verbose"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError(f"ufw 실행 실패: {e}")


def parse_iptables_nat(output: str) -> list[dict]:
    """iptables nat 테이블에서 DOCKER 체인의 포트 포워딩 규칙을 추출한다.

    예시 라인:
    DNAT tcp  --  0.0.0.0/0  0.0.0.0/0  tcp dpt:8321 to:172.18.0.2:80
    DNAT tcp  --  !172.18.0.0/16  0.0.0.0/0  tcp dpt:3001 to:172.18.0.3:3001
    """
    rules = []
    in_docker_chain = False
    chain_name = ""

    for line in output.splitlines():
        # Detect chain header
        chain_match = re.match(r"^Chain\s+(\S+)", line)
        if chain_match:
            chain_name = chain_match.group(1)
            in_docker_chain = "DOCKER" in chain_name.upper()
            continue

        if not in_docker_chain:
            continue

        # Skip header/empty lines
        if line.startswith("target") or not line.strip():
            continue

        # Parse DNAT rules
        dnat_match = re.match(
            r"\s*DNAT\s+(tcp|udp)\s+--\s+(\S+)\s+(\S+)\s+.*dpt:(\d+)\s+to:(\S+)",
            line,
        )
        if dnat_match:
            protocol, source, dest, host_port, target = dnat_match.groups()
            target_ip, target_port = target.rsplit(":", 1) if ":" in target else (target, host_port)
            rules.append({
                "chain": chain_name,
                "protocol": protocol,
                "source": source,
                "host_port": int(host_port),
                "target": target,
                "target_ip": target_ip,
                "target_port": int(target_port),
                "raw": line.strip(),
            })

    return rules


def parse_iptables_filter(output: str) -> list[dict]:
    """iptables filter 테이블에서 DOCKER-USER 체인 규칙을 추출한다."""
    rules = []
    in_docker_user = False

    for line in output.splitlines():
        chain_match = re.match(r"^Chain\s+(\S+)", line)
        if chain_match:
            in_docker_user = chain_match.group(1) == "DOCKER-USER"
            continue

        if not in_docker_user:
            continue

        if line.startswith("target") or not line.strip():
            continue

        # Parse ACCEPT/DROP/REJECT rules
        rule_match = re.match(
            r"\s*(ACCEPT|DROP|REJECT|RETURN)\s+(tcp|udp|all)\s+--\s+(\S+)\s+(\S+)(.*)",
            line,
        )
        if rule_match:
            action, protocol, source, dest, extra = rule_match.groups()
            port = None
            port_match = re.search(r"dpt:(\d+)", extra)
            if port_match:
                port = int(port_match.group(1))
            rules.append({
                "action": action,
                "protocol": protocol,
                "source": source,
                "destination": dest,
                "port": port,
                "raw": line.strip(),
            })

    return rules


def parse_ufw_status(output: str) -> dict:
    """UFW 상태 출력을 파싱한다."""
    result = {"active": False, "default_incoming": "unknown", "rules": []}

    if "inactive" in output.lower():
        return result

    if "Status: active" in output:
        result["active"] = True

    # Default policy
    default_match = re.search(r"Default:\s+(\w+)\s+\(incoming\)", output)
    if default_match:
        result["default_incoming"] = default_match.group(1).lower()

    # Parse rules
    # Format: "22/tcp    ALLOW IN    Anywhere"
    # or:     "3000     DENY IN     Anywhere"
    rule_pattern = re.compile(
        r"^\s*(\S+)\s+(ALLOW|DENY|REJECT|LIMIT)\s+(IN|OUT)?\s*(.*)",
        re.MULTILINE,
    )
    for match in rule_pattern.finditer(output):
        port_proto, action, direction, from_to = match.groups()

        port = None
        protocol = "any"
        if "/" in port_proto:
            port_str, protocol = port_proto.split("/", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        else:
            try:
                port = int(port_proto)
            except ValueError:
                continue

        result["rules"].append({
            "port": port,
            "protocol": protocol,
            "action": action,
            "direction": direction or "IN",
            "from": from_to.strip(),
            "raw": match.group(0).strip(),
        })

    return result

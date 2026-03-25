#!/usr/bin/env python3
"""selfhost-docker-audit — Docker Compose + 방화벽 교차 보안 감사 CLI"""

import argparse
import sys
from pathlib import Path

from compose_parser import parse_compose_file
from firewall_parser import (
    capture_iptables_filter,
    capture_iptables_nat,
    capture_ufw_status,
    parse_iptables_filter,
    parse_iptables_nat,
    parse_ufw_status,
)
from analyzer import analyze
from reporter import print_report


def main():
    parser = argparse.ArgumentParser(
        description="Docker Compose + 방화벽 교차 보안 감사 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
예시:
  # Compose 파일만 분석 (방화벽 정보 없이)
  %(prog)s docker-compose.yml

  # 라이브 방화벽 정보와 교차 분석 (sudo 필요)
  %(prog)s docker-compose.yml --live

  # 미리 캡처한 방화벽 출력 파일 사용
  %(prog)s docker-compose.yml --iptables-nat iptables_nat.txt --ufw ufw.txt

  # 여러 compose 파일 분석
  %(prog)s compose1.yml compose2.yml --live
""",
    )
    parser.add_argument(
        "compose_files",
        nargs="+",
        help="분석할 docker-compose.yml 파일 경로 (여러 개 가능)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="iptables/ufw를 직접 실행하여 라이브 데이터 수집 (sudo 필요)",
    )
    parser.add_argument(
        "--iptables-nat",
        help="iptables -L -n -t nat 출력 파일 (--live 대신 사용)",
    )
    parser.add_argument(
        "--iptables-filter",
        help="iptables -L -n 출력 파일 (--live 대신 사용)",
    )
    parser.add_argument(
        "--ufw",
        help="ufw status verbose 출력 파일 (--live 대신 사용)",
    )

    args = parser.parse_args()

    # Collect firewall data
    iptables_nat_output = ""
    iptables_filter_output = ""
    ufw_output = ""

    if args.live:
        print("🔍 라이브 방화벽 데이터 수집 중... (sudo 필요)")
        try:
            iptables_nat_output = capture_iptables_nat()
            iptables_filter_output = capture_iptables_filter()
            ufw_output = capture_ufw_status()
        except RuntimeError as e:
            print(f"⚠ 방화벽 데이터 수집 실패: {e}", file=sys.stderr)
            print("  → --iptables-nat / --ufw 옵션으로 파일을 직접 지정해주세요.", file=sys.stderr)
            sys.exit(1)
    else:
        if args.iptables_nat:
            iptables_nat_output = Path(args.iptables_nat).read_text()
        if args.iptables_filter:
            iptables_filter_output = Path(args.iptables_filter).read_text()
        if args.ufw:
            ufw_output = Path(args.ufw).read_text()

    # Parse firewall data
    nat_rules = parse_iptables_nat(iptables_nat_output) if iptables_nat_output else []
    filter_rules = parse_iptables_filter(iptables_filter_output) if iptables_filter_output else []
    ufw_data = parse_ufw_status(ufw_output) if ufw_output else {"active": False, "default_incoming": "unknown", "rules": []}

    has_firewall = bool(iptables_nat_output or ufw_output)

    # Merge all compose files into one combined data structure
    combined_services = {}
    parsed_files = []
    for compose_file in args.compose_files:
        try:
            compose_data = parse_compose_file(compose_file)
            parsed_files.append(compose_file)
            for name, svc in compose_data["services"].items():
                # Prefix with source file for disambiguation
                key = name
                if key in combined_services:
                    key = f"{name} ({Path(compose_file).parent.name})"
                combined_services[key] = svc
        except (FileNotFoundError, ValueError) as e:
            print(f"⚠ {e}", file=sys.stderr)
            continue

    if not parsed_files:
        print("⚠ 분석할 Compose 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    combined = {"file": ", ".join(parsed_files), "services": combined_services}
    all_findings = analyze(combined, nat_rules, filter_rules, ufw_data, has_firewall=has_firewall)
    compose_label = ", ".join(str(Path(f).resolve()) for f in parsed_files)
    print_report(all_findings, compose_label, live=has_firewall)

    # Exit code based on findings
    critical_count = sum(1 for f in all_findings if f.severity == "CRITICAL")
    if critical_count > 0:
        sys.exit(2)
    elif all_findings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

# selfhost-docker-audit

> Docker Compose + 방화벽 교차 분석으로 의도치 않은 포트 노출을 탐지하는 CLI 보안 감사 도구

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ docker-compose   │    │ iptables -L -n   │    │ ufw status       │
│ .yml (입력)      │    │ -t nat (입력)    │    │ verbose (입력)   │
└────────┬────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ compose_parser   │    │ firewall_parser  │    │ firewall_parser  │
│ - 포트 매핑      │    │ - DOCKER DNAT    │    │ - UFW 규칙       │
│ - privileged     │    │ - DOCKER-USER    │    │ - default policy │
│ - 시크릿 탐지    │    │                  │    │                  │
└────────┬────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                      │                       │
         └──────────────┬───────┴───────────────────────┘
                        ▼
              ┌──────────────────┐
              │    analyzer      │
              │ - UFW bypass     │
              │ - 포트 교차검증  │
              │ - 보안 체크      │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │    reporter      │
              │ 🔴 CRITICAL      │
              │ 🟡 WARNING       │
              │ 🔵 INFO          │
              └──────────────────┘
```

## Demo

실제 홈서버 compose 파일(momentia, cusdis, monitoring) 3개를 동시 분석한 결과:

```
======================================================================
  Docker Security Audit Report
======================================================================
  Compose: momentia, cusdis, monitoring
  Mode:    Live (iptables/ufw)
======================================================================

  Summary: 🔴 CRITICAL: 4 │ 🟡 WARNING: 8 │ 🔵 INFO: 9

  ── CRITICAL (4) ──

  🔴 [ufw_bypass] 서비스 'frontend'의 포트 9965: UFW default deny인데
     Docker가 iptables를 직접 조작하여 외부 노출!

  🔴 [ufw_bypass] 서비스 'backend'의 포트 3001: UFW default deny인데
     Docker가 iptables를 직접 조작하여 외부 노출!

  🔴 [ufw_bypass] 서비스 'db'의 포트 5432: UFW default deny인데
     Docker가 iptables를 직접 조작하여 외부 노출!

  🔴 [ufw_bypass] 서비스 'grafana'의 포트 3000: UFW default deny인데
     Docker가 iptables를 직접 조작하여 외부 노출!

  ── WARNING (8) ──

  🟡 [hardcoded_secret] 서비스 'backend'에 시크릿 하드코딩: DATABASE_URL (URL embedded)
  🟡 [hardcoded_secret] 서비스 'backend'에 시크릿 하드코딩: JWT_SECRET
  🟡 [hardcoded_secret] 서비스 'db'에 시크릿 하드코딩: POSTGRES_PASSWORD
  🟡 [hardcoded_secret] 서비스 'cusdis'에 시크릿 하드코딩: PASSWORD
  🟡 [hardcoded_secret] 서비스 'grafana'에 시크릿 하드코딩: GF_SECURITY_ADMIN_PASSWORD
  🟡 [docker_user_default] DOCKER-USER 체인이 기본 상태 — Docker 포트 필터링 미설정
  🟡 [undeclared_port] iptables에 포트 8123의 DNAT 규칙이 있으나 분석 대상에 미선언

  ── INFO (9) ──

  🔵 [wildcard_binding] 4개 서비스의 포트가 0.0.0.0에 바인딩
  🔵 [port_confirmed] 5개 서비스의 포트가 iptables DNAT 규칙과 일치

======================================================================
  ⚠ 4개의 CRITICAL 이슈가 발견되었습니다. 즉시 조치가 필요합니다.
======================================================================
```

참고: cusdis는 `127.0.0.1:8321:3000`으로 올바르게 바인딩되어 UFW bypass 경고가 발생하지 않음.

## 실행 방법

```bash
# 의존성 설치
uv sync

# Compose 파일만 분석 (방화벽 정보 없이)
uv run python main.py /path/to/docker-compose.yml

# 라이브 방화벽 정보와 교차 분석 (sudo 필요)
uv run python main.py /path/to/docker-compose.yml --live

# 미리 캡처한 방화벽 출력 파일 사용
uv run python main.py docker-compose.yml \
  --iptables-nat iptables_nat.txt \
  --iptables-filter iptables_filter.txt \
  --ufw ufw_status.txt

# 여러 compose 파일 동시 분석
uv run python main.py compose1.yml compose2.yml compose3.yml --live
```

### Exit codes
- `0`: 이슈 없음
- `1`: WARNING 이상 발견
- `2`: CRITICAL 발견

## 구조

```
selfhost-docker-audit/
├── main.py              # CLI 엔트리포인트
├── compose_parser.py    # Docker Compose YAML 파서
├── firewall_parser.py   # iptables/UFW 출력 파서
├── analyzer.py          # 교차 분석 엔진
├── reporter.py          # 터미널 리포트 출력
├── testdata/            # 테스트용 fixture
│   ├── iptables_nat.txt
│   ├── iptables_filter.txt
│   ├── ufw_status.txt
│   └── dangerous-compose.yml
├── BUILD_LOG.md         # 빌드 일지
├── STATUS.md            # 프로토타입 상태
└── README.md            # 이 파일
```

## 원본
prototype-pipeline spec: selfhost-docker-audit

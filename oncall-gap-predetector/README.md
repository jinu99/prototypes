# Oncall Monitoring Gap Predetector

> Docker Compose + Prometheus config 정적 분석으로 모니터링 사각지대를 자동 탐지하는 CLI 도구

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ docker-compose   │     │ prometheus.yml    │     │ alert_rules.yml │
│     .yml         │     │ (scrape configs)  │     │ (alert rules)   │
└───────┬─────────┘     └────────┬─────────┘     └───────┬─────────┘
        │                        │                        │
        ▼                        ▼                        ▼
   ┌─────────────────────── parser.py ──────────────────────┐
   │  parse_docker_compose  parse_prometheus  parse_alerts   │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
                     ┌─── analyzer.py ───┐
                     │ • Type inference  │
                     │   (image + port)  │
                     │ • Target matching │
                     │ • Gap detection   │
                     │ • Coverage calc   │
                     └────────┬──────────┘
                              │
                              ▼
                    ┌─── reporter.py ───┐
                    │ • JSON report     │
                    │ • Markdown report │
                    └────────┬─────────┘
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
           report.json            report.md
```

## Demo

```bash
$ uv run python main.py demo --format markdown

=== Oncall Gap Predetector — Demo ===

# Oncall Monitoring Gap Report

## Summary

| Metric | Value |
|--------|-------|
| Total services | 8 |
| Monitored | 3 |
| Unmonitored | 5 |
| Avg coverage | 14.4% |

## Service Coverage

| Service | Type | Monitored | Coverage | Alerts | Gaps |
|---------|------|-----------|----------|--------|------|
| nginx | http | ❌ | [░░░░░░░░░░] 0.0% | — | up, http_requests_total, ... |
| api | http | ✅ | [███████░░░] 75.0% | APIHighErrorRate, APIDown | http_request_duration_seconds |
| postgres | database | ✅ | [████░░░░░░] 40.0% | PostgresDown, PostgresHighConnections | replication_lag, slow_queries, db_size_bytes |
| redis | cache | ❌ | [░░░░░░░░░░] 0.0% | — | up, memory_usage_bytes, ... |
| rabbitmq | queue | ❌ | [░░░░░░░░░░] 0.0% | — | up, queue_depth, ... |
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 (샘플 설정 파일 사용)
uv run python main.py demo

# 실제 설정 파일 스캔
uv run python main.py scan \
  --compose path/to/docker-compose.yml \
  --prometheus path/to/prometheus.yml \
  --alerts path/to/alert_rules.yml \
  --format both \
  --output ./reports
```

## 구조

```
oncall-gap-predetector/
├── main.py           # 진입점
├── cli.py            # CLI (scan, demo 서브커맨드)
├── models.py         # 데이터클래스 (Service, MonitoringTarget, AlertRule, GapReport)
├── parser.py         # YAML 파서 (Docker Compose, Prometheus, Alert Rules)
├── analyzer.py       # 서비스 타입 추론 + 갭 분석 로직
├── reporter.py       # JSON/Markdown 리포트 생성
├── samples/          # 데모용 샘플 설정 파일
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   └── alert_rules.yml
├── BUILD_LOG.md      # 빌드 일지
└── STATUS.md         # 검증 결과
```

## 원본
prototype-pipeline spec: oncall-gap-predetector

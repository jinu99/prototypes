# Indie Ops Dashboard

> 솔로 개발자를 위한 경량 인프라 운영 대시보드 — 서버 리소스 패턴 분석 + 비용 최적화 인사이트

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Collection Layer                                                   │
│                                                                     │
│  collector.py (30초 주기)          uptime.py (백그라운드)           │
│  ┌──────────────────────┐         ┌──────────────────────┐         │
│  │ psutil               │         │ HTTP GET (retry 2회) │         │
│  │  • cpu_percent       │         │  • httpbin.org       │         │
│  │  • virtual_memory    │         │  • example.com       │         │
│  │  • net_io_counters   │         └──────────┬───────────┘         │
│  └──────────┬───────────┘                    │                     │
│             │                                │                     │
│             ▼                                ▼                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │              database.py — SQLite (metrics.db)          │       │
│  │  ┌──────────────┐ ┌───────────────┐ ┌────────────────┐ │       │
│  │  │ metrics      │ │ uptime_checks │ │cron_heartbeats │ │       │
│  │  │ (CPU/Mem/Net)│ │ (status/ms)   │ │ (job_name/ts)  │ │       │
│  │  └──────────────┘ └───────────────┘ └────────────────┘ │       │
│  └──────────────────────────┬──────────────────────────────┘       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Analysis Layer                                                     │
│                                                                     │
│  analyzer.py                                                        │
│  ┌────────────────────────┐    ┌─────────────────────────────────┐ │
│  │ classify_metrics()     │    │ compute_cost_comparison()       │ │
│  │  CPU ≥ 10% → active    │───▶│  EC2 t3.micro: $7.59/월       │ │
│  │  CPU < 10% → idle      │    │  Lambda: 요청 기반 과금        │ │
│  │  → 시간대별 세그먼트   │    │  → 절감액 & 추천 메시지       │ │
│  └────────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Presentation Layer — server.py (FastAPI + Uvicorn :8099)          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ REST API                                                       │ │
│  │  GET /api/metrics ─── GET /api/analysis ─── GET /api/uptime  │ │
│  │  POST /api/uptime/check ────── POST /api/heartbeat/{job}     │ │
│  └───────────────────────────────┬───────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ static/index.html — Dashboard UI (Chart.js + vanilla JS)     │ │
│  │  ┌─────────────────────────┐  ┌────────────────────────────┐ │ │
│  │  │ Main                    │  │ Sidebar                    │ │ │
│  │  │  • CPU/Memory 시계열   │  │  • Uptime 상태             │ │ │
│  │  │  • Active/Idle 세그먼트│  │  • Cron Heartbeat 요약    │ │ │
│  │  │  • 일별 활성 시간      │  │                            │ │ │
│  │  │  • EC2 vs Lambda 비용  │  │                            │ │ │
│  │  └─────────────────────────┘  └────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Demo

### 서버 실행

```bash
uv sync
uv run uvicorn server:app --host 0.0.0.0 --port 8099
```

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8099
INFO:     Seeding 36h demo data...
INFO:     Seed complete — 4320 metric rows inserted
INFO:     Metric collector started (30s interval)
INFO:     Uptime checker started
```

첫 실행 시 36시간 분량의 시뮬레이션 데이터가 자동 생성되며, 이후 30초마다 실제 시스템 메트릭을 수집합니다.

### 대시보드 (http://localhost:8099)

다크 테마 기반 2-컬럼 레이아웃:

- **메인 영역**: CPU/Memory 시계열 차트, Active/Idle 세그먼트 바, 일별 활성 시간 막대 차트, EC2 vs Lambda 비용 비교 그리드
- **사이드바**: Uptime 체크 상태 (초록/빨간 점 + 응답 시간), Cron Heartbeat 요약 (마지막 수신 시각 + 횟수)

### API 호출 예시

```bash
# 최근 24시간 메트릭 조회
curl http://localhost:8099/api/metrics?hours=24
```

```json
[
  {"ts": 1710500000.0, "cpu_percent": 34.2, "memory_percent": 61.5,
   "net_sent_bytes": 102400, "net_recv_bytes": 204800},
  ...
]
```

```bash
# 패턴 분석 + 비용 비교
curl http://localhost:8099/api/analysis?hours=24
```

```json
{
  "segments": [
    {"start": "07:00", "end": "09:00", "state": "active"},
    {"start": "09:00", "end": "18:00", "state": "active"},
    {"start": "18:00", "end": "22:00", "state": "active"},
    {"start": "22:00", "end": "07:00", "state": "idle"}
  ],
  "daily_hours": {"2025-03-14": 12.5, "2025-03-15": 11.8},
  "active_percent": 48.2,
  "cost": {
    "ec2_monthly": 7.59,
    "lambda_monthly": 3.12,
    "savings_monthly": 4.47,
    "savings_percent": 58.9,
    "recommendation": "이 서버는 하루 평균 12.2시간만 활성 → Lambda 전환 시 월 $4.47 절감 가능"
  }
}
```

```bash
# 즉시 업타임 체크 실행
curl -X POST http://localhost:8099/api/uptime/check
```

```json
[
  {"url": "https://httpbin.org/status/200", "status": "up", "response_ms": 142.3},
  {"url": "https://example.com", "status": "up", "response_ms": 87.1}
]
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행 (http://localhost:8099)
uv run uvicorn server:app --host 0.0.0.0 --port 8099
```

첫 실행 시 36시간 분량의 데모 데이터가 자동 생성됩니다. 이후 30초마다 실제 시스템 메트릭이 수집됩니다.

## 구조

```
indie-ops-dashboard/
├── server.py          # FastAPI 서버 (API + 정적 파일 서빙)
├── collector.py       # psutil 기반 30초 간격 메트릭 수집
├── analyzer.py        # 활성/유휴 패턴 분류 + EC2 vs Lambda 비용 비교
├── database.py        # SQLite 스키마 및 쿼리 헬퍼
├── uptime.py          # HTTP 업타임 체크 (retry 2회)
├── seed_data.py       # 36시간 시뮬레이션 데이터 생성
├── test_e2e.py        # E2E 검증 테스트
├── test_screenshot.py # Playwright 스크린샷 (시스템 의존성 필요)
├── static/
│   └── index.html     # 대시보드 UI (Chart.js + vanilla JS)
├── BUILD_LOG.md       # 빌드 일지
├── STATUS.md          # 검증 결과
└── pyproject.toml     # 의존성 정의
```

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 대시보드 HTML |
| GET | `/api/metrics?hours=24` | 시계열 메트릭 조회 |
| GET | `/api/analysis?hours=24` | 패턴 분석 + 비용 비교 |
| GET | `/api/uptime` | 업타임 체크 이력 |
| POST | `/api/uptime/check` | 즉시 업타임 체크 실행 |
| GET | `/api/heartbeats` | 크론 하트비트 요약 |
| POST | `/api/heartbeat/{job_name}` | 하트비트 수신 |

## 원본
prototype-pipeline spec: indie-ops-dashboard

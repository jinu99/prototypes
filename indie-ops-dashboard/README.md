# Indie Ops Dashboard

> 솔로 개발자를 위한 경량 인프라 운영 대시보드 — 서버 리소스 패턴 분석 + 비용 최적화 인사이트

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

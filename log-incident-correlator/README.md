# Log-Incident Correlator

> Drain3 기반 first-seen 로그 패턴 탐지와 배포 이벤트 자동 상관관계 분석 프로토타입

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Log Files     │     │  Deploy Events  │
│  (plaintext)    │     │  (JSON / CSV)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   log_parser    │     │  deploy_events  │
│  Drain3 템플릿   │     │  파싱 & 정규화    │
│  추출 + first-  │     │                 │
│  seen 탐지       │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌──────────────────────────────────────────┐
│              db.py (SQLite)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ log_     │ │ deploy_  │ │ correla- │ │
│  │ templates│ │ events   │ │ tions    │ │
│  └──────────┘ └──────────┘ └──────────┘ │
└──────────────────┬───────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │   correlator    │
         │ 시간 윈도우 기반   │
         │ 상관관계 분석      │
         │ (deploy 후 N분   │
         │  내 first-seen)  │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
┌─────────────────┐ ┌─────────────────┐
│    cli.py       │ │   server.py     │
│  터미널 결과 출력  │ │  HTTP API +     │
│  (demo/상관분석) │ │  dashboard.html │
│                 │ │  타임라인 시각화   │
└─────────────────┘ └─────────────────┘
```

**데이터 흐름 요약:**
1. 로그 파일을 Drain3 알고리즘으로 파싱하여 로그 템플릿과 first-seen 시간을 추출
2. 배포 이벤트(timestamp, commit hash, 설명)를 JSON/CSV에서 로드
3. 두 데이터를 SQLite에 저장 후, 시간 윈도우(기본 30분) 내 상관관계 분석
4. 결과를 CLI 또는 웹 대시보드로 출력

## Demo

```bash
$ uv run python cli.py demo
============================================================
LOG-INCIDENT CORRELATOR — DEMO
============================================================

[1/3] Generating sample data...
  Log file: sample_data/sample.log (382KB)
  Deploy events: sample_data/deploys.json

[2/3] Ingesting logs and deploy events...
  Parsed 12000 lines, found 21 unique templates
  Loaded 3 deploy events

[3/3] Correlating (window=30min)...

======================================================================
  DEPLOY: 2026-03-12T03:00:00
  COMMIT: a1b2c3d
  DESC:   Payment module refactor v2.1
  NEW TEMPLATES AFTER DEPLOY: 3
======================================================================
  ⏱ +1.4min  │ ERROR <*> [payment] NullPointerException in PaymentProcessor.charge() at line <*>
  ⏱ +2.2min  │ ERROR <*> [payment] Failed to process payment for order=<*>: missing field 'currency'
  ⏱ +3.6min  │ WARN <*> [payment] Retry attempt <*>/3 for transaction <*>

======================================================================
  DEPLOY: 2026-03-12T10:00:00
  COMMIT: e4f5g6h
  DESC:   Auth service certificate rotation
  NEW TEMPLATES AFTER DEPLOY: 2
======================================================================
  ⏱ +1.7min  │ ERROR <*> [auth] LDAP connection timeout after 30s to ldap.internal:389
  ⏱ +4.1min  │ ERROR <*> [auth] Failed to validate token: certificate expired

======================================================================
  DEPLOY: 2026-03-12T18:00:00
  COMMIT: i7j8k9l
  DESC:   Database connection pool upgrade
  NEW TEMPLATES AFTER DEPLOY: 3
======================================================================
  ⏱ +1.2min  │ ERROR <*> [db] Connection pool exhausted: max=50 active=50 waiting=<*>
  ⏱ +2.8min  │ FATAL <*> [db] Deadlock detected on table 'orders' between tx <*> and <*>
  ⏱ +5.3min  │ ERROR <*> [web] 503 Service Unavailable: upstream db connection failed

RESULT: 8 new templates correlated to 3 deploys

Run 'uv run python cli.py serve' to see the dashboard.
```

웹 대시보드는 `uv run python cli.py serve` 실행 후 `http://localhost:8080`에서 배포-로그 상관관계 타임라인을 시각적으로 확인할 수 있다.

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 실행 (샘플 데이터 생성 + 분석 + 결과 출력)
uv run python cli.py demo

# 대시보드 실행
uv run python cli.py serve
# → http://localhost:8080
```

## 개별 명령어

```bash
# 로그 파일 파싱
uv run python cli.py ingest <logfile>

# 배포 이벤트 로드 (JSON/CSV)
uv run python cli.py deploys <file>

# 상관관계 분석 (기본 30분 윈도우)
uv run python cli.py correlate --window 30

# 대시보드 서버
uv run python cli.py serve --port 8080
```

## 구조

```
├── cli.py              # CLI 엔트리포인트
├── log_parser.py       # Drain3 기반 로그 템플릿 추출
├── deploy_events.py    # 배포 이벤트 파싱 (JSON/CSV)
├── correlator.py       # 시간 윈도우 상관관계 분석
├── db.py               # SQLite 저장/조회
├── server.py           # 대시보드 HTTP 서버
├── dashboard.html      # 타임라인 시각화 대시보드
├── generate_sample.py  # 샘플 데이터 생성기
├── sample_data/        # 생성된 샘플 데이터
├── BUILD_LOG.md        # 빌드 일지
└── STATUS.md           # 완료 상태
```

## 원본
prototype-pipeline spec: log-incident-correlator

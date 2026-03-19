# Indie Prod Monitor

> Simhash 기반 경량 로그 클러스터링 + 헬스체크 + 하트비트 — 제로 설정 단일 바이너리

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         indie-prod-monitor           │
                    │                                     │
  stdin pipe ──────▶│  ┌──────────┐    ┌──────────────┐   │
  (log stream)      │  │ Tokenize │───▶│   Simhash    │   │
                    │  │ + Strip  │    │  Clustering  │──────▶ [ALERT] new cluster
  POST /ingest ───▶│  └──────────┘    └──────┬───────┘   │     (stdout / webhook)
  (HTTP log push)   │                         │           │
                    │                  ┌──────▼───────┐   │
                    │                  │   SQLite DB   │   │
                    │                  │  (clusters,   │   │
                    │                  │   checks,     │   │
                    │                  │   heartbeats) │   │
                    │                  └──────▲───────┘   │
                    │                         │           │
  POST /healthcheck─│──▶ Register URL ────────┤           │
                    │    Periodic ping ────────┤──────────▶ [ALERT] health down
                    │                         │           │
  POST /heartbeat/  │──▶ Record beat ─────────┤           │
  {name}            │    Overdue check ───────┘──────────▶ [ALERT] heartbeat miss
                    │                                     │
  GET /status ─────▶│──▶ JSON overview                    │
                    └─────────────────────────────────────┘
```

## Demo

### stdin 파이프 — 로그 클러스터링

```bash
$ printf 'ERROR: db connection failed\nERROR: db connection failed host=replica\nWARN: slow query 5000ms\nERROR: auth token expired user 12345\nERROR: auth token expired user 67890\n' \
  | ./indie-prod-monitor -db demo.db

2026/03/19 21:08:56 new cluster #1 (hash=8731024635130171): ERROR: db connection failed
2026/03/19 21:08:56 [ALERT:new_cluster] New error pattern detected — ERROR: db connection failed
2026/03/19 21:08:56 new cluster #2 (hash=c075d04634830161): ERROR: db connection failed host=replica
2026/03/19 21:08:56 [ALERT:new_cluster] New error pattern detected — ERROR: db connection failed host=replica
2026/03/19 21:08:56 new cluster #3 (hash=28310b16f4783e11): WARN: slow query detected 5000ms
2026/03/19 21:08:56 [ALERT:new_cluster] New error pattern detected — WARN: slow query detected 5000ms
2026/03/19 21:08:56 new cluster #4 (hash=1de630d462914852): ERROR: auth token expired for user 12345
2026/03/19 21:08:56 [ALERT:new_cluster] New error pattern detected — ERROR: auth token expired for user 12345
```

5줄 입력 → 4클러스터 (auth token 2건이 같은 클러스터로 매칭)

### HTTP API

```bash
# 로그 수집
curl -X POST http://localhost:9111/ingest \
  -d '{"lines":["ERROR: timeout connecting to redis","FATAL: out of memory"]}'

# 헬스체크 등록
curl -X POST http://localhost:9111/healthcheck \
  -d '{"name":"my-api","url":"https://api.example.com/health","interval":60}'

# 하트비트 등록 + 비트
curl -X POST http://localhost:9111/heartbeat/nightly-backup \
  -d '{"interval":86400}'

# 상태 조회
curl http://localhost:9111/status
```

## 실행 방법

```bash
# 빌드
go build -o indie-prod-monitor .

# 기본 실행 (서버 모드)
./indie-prod-monitor

# stdin 파이프 연결
my-app 2>&1 | ./indie-prod-monitor

# 옵션
./indie-prod-monitor \
  -db monitor.db \          # SQLite DB 경로 (기본: monitor.db)
  -addr :9111 \             # HTTP 주소 (기본: :9111)
  -level warn \             # 최소 로그 레벨 (기본: warn)
  -threshold 10 \           # simhash 거리 임계값 (기본: 10)
  -webhook https://ntfy.sh/my-topic  # 알림 웹훅 URL
```

## 구조

```
indie-prod-monitor/
├── main.go              # CLI 엔트리포인트, 플래그 파싱
├── simhash/
│   └── simhash.go       # simhash 알고리즘 (토큰화, 해싱, 거리 계산)
├── store/
│   └── store.go         # SQLite 저장소 (클러스터, 헬스체크, 하트비트)
├── engine/
│   └── engine.go        # 핵심 로직 (로그 처리, 모니터링 루프)
├── server/
│   └── server.go        # HTTP API 서버
├── alert/
│   └── alert.go         # 알림 시스템 (stdout, webhook)
├── go.mod / go.sum
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: indie-prod-monitor

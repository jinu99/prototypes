# Stack Cascade Predictor

> YAML 의존성 그래프 기반으로 클라우드 서비스 장애의 영향 범위를 즉시 파악하고 시각화하는 도구

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  example_graph   │     │  RSS/Atom    │     │   Simulation    │
│  .yaml           │     │  Feeds       │     │   API           │
│  (의존성 정의)    │     │  (mock/real) │     │   (장애 주입)    │
└────────┬────────┘     └──────┬───────┘     └────────┬────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server (server.py)                │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐  │
│  │ graph.py │  │  feed.py  │  │  db.py   │  │  SSE      │  │
│  │ YAML→BFS │  │ RSS parse │  │ SQLite   │  │ realtime  │  │
│  │ cascade  │  │ classify  │  │ history  │  │ push      │  │
│  └──────────┘  └───────────┘  └──────────┘  └───────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ SSE (Server-Sent Events)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Web Dashboard (static/index.html)              │
│  ┌───────────────────────────┐  ┌────────────────────────┐  │
│  │  Cytoscape.js + dagre    │  │  Sidebar               │  │
│  │  의존성 그래프 시각화      │  │  시뮬레이션 컨트롤      │  │
│  │  장애 노드 색상 변경      │  │  이벤트 로그           │  │
│  │  cascade 엣지 하이라이트  │  │  cascade 영향 표시     │  │
│  └───────────────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Demo

### AWS US-East-1 Outage Simulation
```bash
# 서버 시작 후
curl -X POST http://localhost:8099/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"service_id":"aws-us-east-1","status":"outage"}'

# 결과: 7개 서비스 cascade
# aws-us-east-1: outage
# api-gateway: outage (hard dep)
# auth-service: outage → user-service: outage → payment-service: outage
# web-frontend: outage, mobile-app: outage
```

### Soft Dependency 전파
```bash
# Cloudflare outage → CDN은 outage(hard), API Gateway는 degraded(soft)
curl -X POST http://localhost:8099/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"service_id":"cloudflare","status":"outage"}'
```

### RSS Feed 폴링
```bash
curl -X POST http://localhost:8099/api/poll-now
# Mock 피드 결과: aws-us-east-1(degraded), github(degraded), stripe(degraded)
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run python server.py
# http://localhost:8099 접속
```

## API

| Endpoint | Method | 설명 |
|---|---|---|
| `/` | GET | 대시보드 HTML |
| `/api/graph` | GET | 현재 그래프 상태 |
| `/api/events` | GET | SSE 실시간 스트림 |
| `/api/simulate` | POST | 장애 주입 `{service_id, status}` |
| `/api/reset` | POST | 전체 리셋 |
| `/api/poll-now` | POST | 즉시 RSS 피드 폴링 |
| `/api/history` | GET | 상태 변경 이력 |

## 구조

```
stack-cascade-predictor/
├── server.py              # FastAPI 서버 + SSE + REST API
├── graph.py               # YAML 파싱 + BFS cascade 전파
├── feed.py                # RSS/Atom 피드 수집 + mock 데이터
├── db.py                  # SQLite 상태 이력 저장
├── example_graph.yaml     # 의존성 그래프 예시
├── static/
│   └── index.html         # Cytoscape.js 대시보드
├── BUILD_LOG.md           # 빌드 일지
├── STATUS.md              # 검증 결과
└── pyproject.toml         # 의존성 정의
```

## 원본
prototype-pipeline spec: stack-cascade-predictor

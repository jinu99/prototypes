# Webhook Chaos Tester

> CLI tool that runs chaos scenarios (duplicate, delay, reorder) against webhook endpoints to find idempotency and error-handling bugs.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI (cli.py)                           │
│              click 기반 명령어: run / demo / echo               │
└──────┬──────────────────┬───────────────────────┬───────────────┘
       │                  │                       │
       ▼                  ▼                       ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐
│ Loader       │  │ Engine        │  │ Echo Server            │
│ (loader.py)  │  │ (engine.py)   │  │ (echo_server.py)       │
│              │  │               │  │                        │
│ YAML 파싱    │  │ 시나리오 실행 │  │ 테스트용 HTTP 서버     │
│ → Scenario[] │  │ httpx로 전송  │  │ POST /webhook 수신     │
└──────┬───────┘  └───────┬───────┘  │ GET  /_requests 조회   │
       │                  │          │ GET  /_reset    초기화  │
       │                  │          │                        │
       ▼                  │          │ 모드:                  │
┌──────────────┐          │          │  · 기본: 200 응답      │
│ scenarios/   │          │          │  · --reject-duplicates │
│  default.yaml│          │          │    : 409 중복 거부     │
│  stress.yaml │          │          └────────────┬───────────┘
└──────────────┘          │                       │
                          │    HTTP POST (JSON)   │
                          │──────────────────────▶│
                          │                       │
                          ▼                       │
                  ┌───────────────┐               │
                  │ ScenarioResult│◀──── 응답 ────┘
                  │  · verdict    │
                  │  · requests[] │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Report        │
                  │ (report.py)   │
                  │               │
                  │ Markdown 또는 │
                  │ JSON 리포트   │
                  └───────────────┘
```

**데이터 흐름:**
1. CLI가 Loader를 통해 YAML 시나리오를 파싱하거나 기본 시나리오 3종을 로드
2. Engine이 각 시나리오 타입(duplicate/delay/reorder)에 맞는 카오스 패턴으로 HTTP 요청 전송
3. 대상 서버(또는 내장 Echo Server)의 응답 코드로 PASS/FAIL 판정
4. Report 모듈이 결과를 Markdown 또는 JSON 형식으로 출력

## Demo

`demo` 명령어는 Echo Server를 자동으로 시작하고 기본 시나리오 3종을 실행합니다.

```bash
$ uv run webhook-chaos demo

Starting echo server on port 9876...
Target: http://127.0.0.1:9876/webhook
Scenarios: 3

[1/3] duplicate-delivery (duplicate)...
  PASS: All 3 duplicate requests returned 2xx
[2/3] delayed-delivery (delay)...
  PASS: Response 200 after 2.0s delay
[3/3] out-of-order (reorder)...
  PASS: All reversed-order requests returned 2xx

Results: 3/3 passed

# Webhook Chaos Test Report

**Target:** `http://127.0.0.1:9876/webhook`
**Date:** 2026-03-16 14:30:00
**Scenarios:** 3

## Summary: 3 PASS / 0 FAIL

### ✅ duplicate-delivery
- **Type:** duplicate
- **Verdict:** **PASS**
- **Reason:** All 3 duplicate requests returned 2xx

### ✅ delayed-delivery
- **Type:** delay
- **Verdict:** **PASS**
- **Reason:** Response 200 after 2.0s delay

### ✅ out-of-order
- **Type:** reorder
- **Verdict:** **PASS**
- **Reason:** All reversed-order requests returned 2xx
```

JSON 형식으로 리포트를 파일에 저장할 수도 있습니다:

```bash
$ uv run webhook-chaos demo --format json --output report.json
```

특정 webhook 서버를 대상으로 테스트하려면 `run` 명령어를 사용합니다:

```bash
$ uv run webhook-chaos run --target http://your-server.com/webhook
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 자체 데모 (에코 서버 자동 시작 + 기본 시나리오 3종 실행)
uv run webhook-chaos demo

# 특정 URL에 대해 실행
uv run webhook-chaos run --target http://your-server.com/webhook

# 에코 서버만 따로 시작
uv run webhook-chaos echo --port 9876

# 커스텀 시나리오 파일 사용
uv run webhook-chaos demo --scenario scenarios/stress.yaml

# JSON 리포트 출력
uv run webhook-chaos demo --format json --output report.json
```

## 시나리오 작성 가이드

YAML 파일로 커스텀 시나리오를 정의할 수 있습니다.

### 시나리오 타입

| 타입 | 설명 | 판정 기준 |
|------|------|-----------|
| `duplicate` | 같은 페이로드를 N번 전송 | 모두 2xx면 PASS |
| `delay` | 지연 후 전송 | 2xx면 PASS |
| `reorder` | 여러 페이로드를 역순으로 전송 | 모두 2xx면 PASS |

### YAML 형식

```yaml
scenarios:
  - name: my-duplicate-test
    type: duplicate
    description: "설명"
    payload:
      event: payment.completed
      id: evt_001
      amount: 5000
    count: 5  # 반복 횟수 (기본값: 3)

  - name: my-delay-test
    type: delay
    payload:
      event: order.shipped
      id: evt_002
    delay_seconds: 3.0  # 지연 시간 (기본값: 2.0)

  - name: my-reorder-test
    type: reorder
    payloads:  # 순서대로 정의하면 역순으로 전송됨
      - { event: step1, seq: 1 }
      - { event: step2, seq: 2 }
      - { event: step3, seq: 3 }
```

### 에코 서버 모드

```bash
# 기본 모드 (모든 요청에 200 응답)
uv run webhook-chaos echo

# 중복 거부 모드 (같은 Idempotency-Key로 2번째부터 409 응답)
uv run webhook-chaos echo --reject-duplicates
```

## 구조

```
webhook-chaos-tester/
├── webhook_chaos/
│   ├── __init__.py
│   ├── cli.py          # CLI 진입점 (click)
│   ├── engine.py       # 카오스 시나리오 실행 엔진
│   ├── loader.py       # YAML 시나리오 로더
│   ├── echo_server.py  # 테스트용 에코 서버
│   └── report.py       # Markdown/JSON 리포트 생성
├── scenarios/
│   ├── default.yaml    # 기본 시나리오 3종
│   └── stress.yaml     # 스트레스 테스트 시나리오
├── pyproject.toml
└── README.md
```

## 원본

prototype-pipeline spec: webhook-chaos-tester

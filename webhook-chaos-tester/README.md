# Webhook Chaos Tester

> CLI tool that runs chaos scenarios (duplicate, delay, reorder) against webhook endpoints to find idempotency and error-handling bugs.

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

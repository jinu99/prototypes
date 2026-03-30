# Agent Spending Guard

> AI 에이전트의 결제 API 호출을 네트워크 레벨 프록시에서 가로채어 YAML 정책 기반으로 지출 한도를 강제하는 투명 프록시

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  AI Agent   │────▶│  mitmproxy       │────▶│  Mock Payment    │
│  (agent_sim)│     │  + SpendingGuard │     │  Server (Flask)  │
└─────────────┘     │    addon         │     │  :9000           │
                    │  :8080           │     │  /v1/charges     │
                    │                  │     │  /v1/payment_    │
                    │  ┌────────────┐  │     │    intents       │
                    │  │ Policy     │  │     │  /v2/checkout/   │
                    │  │ (YAML)     │  │     │    orders        │
                    │  └────────────┘  │     └──────────────────┘
                    │  ┌────────────┐  │
                    │  │ PII Detect │  │
                    │  │ (regex)    │  │
                    │  └────────────┘  │
                    │  ┌────────────┐  │
                    │  │ Audit Log  │  │
                    │  │ (SQLite)   │  │
                    │  └────────────┘  │
                    │        │         │
                    │  ┌─────▼──────┐  │
                    │  │ CLI Prompt │  │
                    │  │ (approve/  │  │
                    │  │  deny)     │  │
                    │  └────────────┘  │
                    └──────────────────┘
```

## Demo

### E2E 테스트 (자동)

```
$ uv run python test_e2e.py

==================================================
E2E Test Suite — Agent Spending Guard
==================================================

Starting services...
  Started mock-server (PID 1316491)
  Started mitmdump (PID 1316492)

Waiting for services...
  Both services ready.

[TEST] Pass-through (health check)
  ✅ PASS
[TEST] Normal Stripe charge ($25.00)
  ✅ PASS
[TEST] Over-limit charge ($75.00) — should be blocked
  ✅ PASS
[TEST] PayPal order ($30.00)
  ✅ PASS
[TEST] PII detection (email + phone)
  ✅ PASS (PII warning logged)
[TEST] Audit log entries
  ✅ PASS (4 entries, 1 blocked, 1 with PII)

==================================================
Results: 6 passed, 0 failed
==================================================
```

### 감사 로그 조회

```
$ uv run python audit_query.py

Recent transactions (last 4):
----------------------------------------------------------------------------------------------------
  ✅ [2026-03-30 21:05:19] stripe_charges                     $25.00  usd  approved   within limits
  🚫 [2026-03-30 21:05:19] stripe_charges                     $75.00  usd  blocked    human denied: exceeds per-transaction limit ($75.00 > $50.00)
  ✅ [2026-03-30 21:05:19] paypal_orders                      $30.00  USD  approved   within limits
  ✅ [2026-03-30 21:05:20] stripe_payment_intents             $15.00  usd  approved   within limits  PII: ["email", "phone"]
----------------------------------------------------------------------------------------------------
Daily total:   $70.00
Monthly total: $70.00
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 자동 테스트 (서버 + 프록시 + 시나리오 자동 실행)
uv run python test_e2e.py

# 인터랙티브 데모 (서버 + 프록시 시작 후 별도 터미널에서 agent 실행)
./run_demo.sh
# 다른 터미널에서:
uv run python agent_sim.py

# 감사 로그 조회
uv run python audit_query.py
uv run python audit_query.py --daily-total
uv run python audit_query.py --json
```

## 구조

```
agent-spending-guard/
├── policy.yaml        # YAML 정책 (한도, API 패턴, PII 규칙)
├── mock_server.py     # Mock Stripe/PayPal API 서버 (Flask)
├── proxy_addon.py     # mitmproxy addon (핵심: 패턴 매칭, 한도 체크, 승인 플로우)
├── db.py              # SQLite 감사 로그
├── pii.py             # PII regex 감지 엔진
├── agent_sim.py       # AI 에이전트 시뮬레이터 (5개 시나리오)
├── audit_query.py     # 감사 로그 CLI 조회
├── test_e2e.py        # 자동 E2E 테스트
├── run_demo.sh        # 인터랙티브 데모 실행 스크립트
├── BUILD_LOG.md       # 빌드 일지
└── STATUS.md          # 완료 상태
```

## 원본
prototype-pipeline spec: agent-spending-guard

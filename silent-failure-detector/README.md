# Silent Failure Detector

> HTTP 200인데 실제로는 실패한 요청을 선언적 규칙으로 잡아내는 경량 미들웨어

## Architecture

```
                    ┌──────────────────────────────────────┐
                    │          Express Server               │
                    │                                      │
  HTTP Request ──▶  │  ┌─────────────────────┐             │
                    │  │  SFD Middleware      │             │
                    │  │  (intercept res.json)│             │
                    │  └──────────┬──────────┘             │
                    │             │                        │
                    │  ┌──────────▼──────────┐             │
                    │  │  Route Handler       │──▶ HTTP 200 │──▶ Client
                    │  └──────────┬──────────┘             │
                    │             │ (on finish)            │
                    │  ┌──────────▼──────────┐             │
                    │  │  Rule Engine         │             │
                    │  │  (YAML assertions)   │             │
                    │  └──────────┬──────────┘             │
                    │             │ (if failed)            │
                    │  ┌──────────▼──────────┐             │
                    │  │  SQLite Logger       │             │
                    │  └──────────┬──────────┘             │
                    │             │                        │
                    │  ┌──────────▼──────────┐             │
                    │  │  Dashboard (HTML)    │             │
                    │  │  /dashboard          │             │
                    │  └─────────────────────┘             │
                    └──────────────────────────────────────┘

  rules.yaml ──▶ body_contains / body_check / callback assertions
```

## Demo

서버 실행 후 CLI 데모:

```
$ npm run demo

=== Silent Failure Detector — Demo ===

[1/4] Cleared previous failure data
[2/4] POST /api/orders → {"id":"ord_1774527613542","status":"created","message":"Order placed successfully"}
[3/4] POST /api/payments → {"result":"success","transactionId":"tx_...","details":{"charged":false,...}}
[4/4] PUT /api/users/1 → {"id":"1","name":"Alice","email":"alice@example.com","updated":true,...}

=== Detected Silent Failures: 3 ===

  1. [order-db-write] POST /api/orders
     Expected: order ord_... in DB
     Actual:   not found in DB

  2. [payment-processing] POST /api/payments
     Expected: details.charged == true
     Actual:   false

  3. [profile-update] PUT /api/users/1
     Expected: name = Alice Updated
     Actual:   name = Alice
```

대시보드: `http://localhost:3456/dashboard` — "Run Demo" 버튼으로 시나리오 실행 가능

## 실행 방법

```bash
# 의존성 설치
npm install

# 서버 시작
npm start

# (별도 터미널) 데모 실행
npm run demo

# 또는 브라우저에서 http://localhost:3456/dashboard 접속 후 "Run Demo" 클릭
```

## 규칙 작성

`rules.yaml`에 엔드포인트별 성공 조건을 선언:

```yaml
rules:
  - name: "order-creation"
    endpoint: "POST /api/orders"
    assertions:
      - type: body_contains    # 응답에 특정 필드가 존재하는지
        field: "id"
        condition: exists
      - type: body_check       # 필드 값 비교 (equals, not_empty, gt)
        field: "status"
        condition: equals
        value: "created"
      - type: callback         # 커스텀 검증 함수
        fn: "verifyOrderInDb"
```

Assertion 타입:
- `body_contains` — `condition: exists`로 필드 존재 확인
- `body_check` — `condition: equals|not_empty|gt`로 값 검증
- `callback` — `registerCallback(name, fn)`으로 등록한 커스텀 함수 실행

## 구조

```
silent-failure-detector/
├── src/
│   ├── server.js          # Express 서버 + 콜백 등록
│   ├── middleware.js       # 핵심: res.json 인터셉트 + 비동기 assertion
│   ├── rules.js            # YAML 규칙 로딩 + assertion 엔진
│   ├── db.js               # SQLite 저장/조회
│   ├── demo-service.js     # 3가지 데모 시나리오 라우트
│   ├── dashboard-api.js    # 대시보드 API 엔드포인트
│   ├── run-demo.js         # CLI 데모 러너
│   └── test-dashboard.js   # Playwright 테스트 (시스템 의존)
├── public/
│   └── dashboard.html      # 단일 HTML 대시보드
├── rules.yaml              # 선언적 assertion 규칙
├── data/                   # SQLite DB (자동 생성)
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: silent-failure-detector

# Indie Revenue Attribution

> 인디 개발자를 위한 채널별 매출 어트리뷰션 대시보드 — UTM-to-payment 매칭으로 진짜 CAC와 ROI를 한눈에

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Stripe       │────▶│  FastAPI Server   │◀────│ Umami/       │
│ Webhook      │     │  (port 8787)      │     │ Plausible    │
│ (Test Mode)  │     │                   │     │ (mock seed)  │
└──────────────┘     │  ┌─────────────┐  │     └──────────────┘
                     │  │ SQLite DB   │  │
                     │  │ ┌─payments  │  │
                     │  │ ├─sessions  │  │
                     │  │ └─costs     │  │
                     │  └─────────────┘  │
                     │                   │
                     │  ┌─────────────┐  │     ┌──────────────┐
                     │  │ Matching    │  │     │ Dashboard    │
                     │  │ Engine      │──│────▶│ (HTML+JS)    │
                     │  │ first-touch │  │     │ Chart.js     │
                     │  └─────────────┘  │     └──────────────┘
                     └──────────────────┘
```

## Demo

```
$ uv run python seed_data.py
Matching: 20/20 payments matched
Seeded: 20 sessions, 20 payments, 5 channel costs

$ uv run uvicorn app:app --port 8787
INFO: Uvicorn running on http://127.0.0.1:8787

# Dashboard API 응답 예시:
$ curl -s http://localhost:8787/api/dashboard | python3 -m json.tool
{
  "channels": [
    {"channel": "paid-search", "revenue_display": "$804.00", "true_cac": 171.67, "roi_pct": -21.9},
    {"channel": "paid-social", "revenue_display": "$746.00", "true_cac": 180.00, "roi_pct": 3.6},
    {"channel": "email",       "revenue_display": "$477.00", "true_cac": 93.00,  "roi_pct": 71.0},
    {"channel": "direct",      "revenue_display": "$477.00", "true_cac": 0.00,   "roi_pct": null},
    {"channel": "producthunt", "revenue_display": "$296.00", "true_cac": 187.50, "roi_pct": -60.5}
  ],
  "summary": {"total_revenue_display": "$2,800.00", "blended_cac": 138.95}
}

# Stripe webhook 테스트:
$ curl -X POST http://localhost:8787/webhook/stripe \
  -H 'Content-Type: application/json' \
  -d '{"type":"checkout.session.completed","data":{"object":{"amount_total":9900,"currency":"usd","customer_email":"test@example.com"}}}'
{"status": "stored", "payment_id": "..."}
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 샘플 데이터 생성 (5채널, 20결제, 자동 매칭)
uv run python seed_data.py

# 서버 실행
uv run uvicorn app:app --port 8787

# 브라우저에서 http://localhost:8787 접속
```

## 구조

```
indie-revenue-attribution/
├── app.py              # FastAPI 서버 (webhook, API, 대시보드 서빙)
├── database.py         # SQLite 스키마 및 연결
├── matching.py         # UTM-to-payment 매칭 엔진 (first-touch)
├── seed_data.py        # 샘플 데이터 생성기
├── static/
│   └── index.html      # 대시보드 (Chart.js, vanilla JS)
├── test_screenshot.py  # Playwright 스크린샷 테스트
├── BUILD_LOG.md        # 빌드 일지
├── STATUS.md           # 검증 결과
└── README.md
```

## 원본
prototype-pipeline spec: indie-revenue-attribution

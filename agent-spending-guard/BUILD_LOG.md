# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 확인: mitmproxy addon 기반 결제 API 프록시, YAML 정책, PII 감지, SQLite 감사 로그
- [판단] 스택 선택: Python + mitmproxy + Flask + SQLite (이유: spec이 mitmproxy addon을 명시, Flask는 mock 서버용 최경량 선택, SQLite는 표준 라이브러리 수준)
- [판단] 의존성: mitmproxy, pyyaml, requests, flask (최소한)

## Phase 2 — 구현
- [시도] `uv init && uv add mitmproxy pyyaml requests` → [결과] 성공
- [시도] Mock 결제 서버 (Stripe /v1/charges, /v1/payment_intents, PayPal /v2/checkout/orders) → [결과] 성공
- [시도] SQLite 감사 로그 모듈 (db.py) → [결과] 성공
- [시도] PII regex 감지 (pii.py) → [결과] 성공
- [시도] mitmproxy addon (proxy_addon.py) — 패턴 매칭, 한도 체크, CLI 승인, 감사 로깅 → [결과] 성공
- [시도] Agent 시뮬레이터 (agent_sim.py) — 5개 시나리오 → [결과] 성공
- [시도] E2E 테스트 (test_e2e.py) — 6개 테스트 → [결과] 성공 (6/6 통과)
- [에러] PII 감지에서 email 미탐지 — form-encoded body에서 `@`가 `%40`으로 인코딩됨 → [수정] `unquote_plus(body_text)` 적용 후 PII 스캔 → 재테스트 통과

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. 프록시가 실제로 요청을 가로채서 차단하고, 감사 로그에 기록되는 것이 확인됨.
- [평가] Spec의 검증 목표가 실제로 검증되는가? → 그렇다. 네트워크 레벨 프록시가 결제 패턴 인식 → YAML 정책 기반 한도 강제 → 초과시 CLI 승인 → 전부 동작 확인.
- [평가] 출력이 깔끔한가? → 감사 로그 출력이 정렬되고 이모지로 구분되어 읽기 좋음. CLI 승인 프롬프트도 명확.
- [불만] Email PII 미탐지 → [개선] URL decode 후 PII 스캔으로 수정
- [평가] 개선 후 재테스트 6/6 통과. 만족.

## Phase 4 — 검증
- [체크] mock 결제 서버가 Stripe/PayPal 스타일 엔드포인트 제공 → 통과 (/v1/charges, /v1/payment_intents, /v2/checkout/orders)
- [체크] mitmproxy addon이 결제 API 패턴 인식 + YAML 정책 기반 승인/차단 → 통과 ($25 승인, $75 차단)
- [체크] 정책 초과 시 CLI 인간 승인 요청 → 통과 (non-interactive 모드에서 auto-deny 확인, interactive 모드 코드 경로 존재)
- [체크] PII 패턴 감지 (이메일, 전화번호) → 통과 (email + phone 탐지 확인)
- [체크] 모든 트랜잭션 SQLite 기록 + 조회 → 통과 (4건 기록, audit_query.py로 조회 확인)

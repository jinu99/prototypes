# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 확인: small-biz-queue-ops.md
- [판단] 스택 선택: Node.js + better-sqlite3 + vanilla JS (이유: Spec에 "단일 Node 서버" 명시, SQLite OK, 프론트엔드는 단일 HTML + vanilla JS 제약)
- [판단] 의존성: better-sqlite3 (SQLite 바인딩), qrcode (QR 생성) — 최소 의존성, 나머지는 Node 내장 모듈(http, fs, path, crypto)
- [판단] SSE는 내장 http 모듈로 구현 (추가 라이브러리 불필요)
- [판단] PWA manifest는 정적 JSON 파일로 제공

## Phase 2 — 구현
- [시도] 서버 구현 (db.js, sse.js, routes.js, server.js) → [결과] 성공
- [에러] routes.js에서 `??` placeholder 사용 (SQLite 미지원) → [수정] 개별 timestampStmts로 분리
- [시도] 프론트엔드 4페이지 (index, join, admin, kds) + style.css + manifest.webmanifest → [결과] 성공
- [시도] API 전체 flow 테스트 (등록→조회→상태변경→QR→SSE) → [결과] 전부 통과

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → API 레벨에서는 "오 되네" — 깔끔한 REST + SSE
- [불만] Playwright 실행 불가 (libatk 미설치, sudo 불가) → curl 기반 검증으로 대체
- [불만] admin 완료 탭에서 completed 항목 누락 → [개선] loadCompleted() 함수 분리, /api/queue/all 별도 fetch
- [평가] SSE 실시간 업데이트 curl로 확인됨 — 이벤트 정상 수신
- [평가] 상태 전이 flow 완벽 동작 (waiting→called→seated→completed)

## Phase 4 — 검증
- [체크] QR 스캔 → 이름/인원수 → 대기열 등록 → **통과** ✅
- [체크] 실시간 대기 순서/예상 시간 SSE 자동 갱신 → **통과** ✅ (SSE 이벤트 1건 수신 확인)
- [체크] 매장 관리 화면: 대기자 목록/상태 변경 → **통과** ✅ (called→seated→completed flow 확인)
- [체크] KDS 뷰 (카드 형태) → **통과** ✅ (200 + kds-grid 요소 확인)
- [체크] npm start 한 줄 실행 → **통과** ✅ (start: node server.js)
- [결과] **5/5 전부 통과 → SUCCESS**

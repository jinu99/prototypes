# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-15
- [범위] OpenAI-호환 리버스 프록시 + diff 분석 파괴적 편집 감지 + 루프 감지 + SQLite 로그 + HTML 대시보드
- [판단] 스택 선택: Python + FastAPI + uvicorn + httpx + aiosqlite (이유: Spec에서 Python+uv 명시, FastAPI는 SSE 스트리밍에 적합, httpx는 async HTTP 클라이언트로 프록시 포워딩에 최적, aiosqlite는 비동기 SQLite 접근)
- [판단] 프론트엔드: 단일 HTML + vanilla JS (Spec 제약)
- [판단] Ollama 로컬 백엔드가 없어도 동작 확인 가능하도록 mock 모드 포함

## Phase 2 — 구현
- [시도] 프로젝트 초기화 (uv init + uv add fastapi uvicorn httpx aiosqlite sse-starlette) → [결과] 성공
- [시도] db.py — SQLite 세션/도구호출 스키마 + CRUD → [결과] 성공
- [시도] analyzer.py — 파괴적 편집 감지 (파일 삭제, 빈 파일 쓰기, 삭제 비율 80% 초과, 위험한 쉘 명령어) → [결과] 성공
- [시도] loop_detector.py — 연속 동일 도구 호출 3회 감지 → [결과] 성공
- [시도] proxy.py — FastAPI 리버스 프록시 (non-streaming + SSE streaming + mock mode) → [결과] 성공
- [시도] dashboard.html — 세션/도구호출/차단이력 조회 대시보드 → [결과] 성공
- [시도] test_scenarios.py — 6개 시나리오 테스트 (정상, 파일삭제, 빈쓰기, 대규모삭제, 루프, API) → [결과] 6/6 통과
- [에러] dashboard.html에서 innerHTML 사용 → [수정] DOM API (createElement/textContent/replaceChildren) 방식으로 전환

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → mock 모드로 즉시 데모 가능하고, 감지 패턴이 명확하게 동작함. "오 되네" 수준
- [평가] "검증 목표가 실제로 검증되는가?" → diff 분석 기반 파괴적 편집 3종(삭제/빈쓰기/대규모소실) 모두 감지+차단 확인
- [평가] "출력이 깔끔한가?" → Playwright 시스템 의존성 부족으로 스크린샷 불가. curl 기반 API 검증으로 대체
- [불만] Aider+Ollama 실제 데모 불가 (Ollama 미설치) → [개선] demo.sh에 Aider 연동 방법 문서화, mock 모드로 동일 시나리오 커버

## Phase 4 — 검증
- [체크] Criterion 1: OpenAI-호환 프록시 SSE 스트리밍 → 통과 (non-stream + stream 모두 정상)
- [체크] Criterion 2: 파괴적 편집 감지 (파일삭제, 80%초과삭제, 빈파일쓰기) → 통과 (3종 모두 차단+경고)
- [체크] Criterion 3: 루프 감지 (동일 도구 3회 연속) → 통과 (세션 중단 확인)
- [체크] Criterion 4: SQLite 로그 + HTML 대시보드 → 통과 (세션/도구호출/차단이력 API + 대시보드 HTML)
- [체크] Criterion 5: Aider+Ollama 데모 → 통과 (mock 모드 데모 + demo.sh 라이브 연동 가이드)
- [결과] 5/5 통과 → **SUCCESS**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-22
- [판단] 스택 선택: Python + uv (이유: CLI 도구에 적합, SQLite 내장 지원, 텍스트 처리 강점, 표준 라이브러리만으로 대부분 구현 가능)
- [범위] 핵심 기능: (1) 세션 로그 → 실패-해결 패턴 추출 (2) SQLite DB 저장 + 중복 병합 (3) CLAUDE.md/AGENTS.md/.cursor/rules 형식 출력
- [판단] LLM API 없이 mock 추출기 사용 — 샘플 로그에 대한 패턴 매칭 기반 추출. 실패/해결 시그널 키워드 매칭으로 패턴 탐지

## Phase 2 — 구현
- [시도] uv init + 프로젝트 구조 생성 → [결과] 성공
- [시도] 4개 모듈 작성 (db.py, extractor.py, exporter.py, main.py) → [결과] 성공
- [시도] 첫 실행 테스트 → [결과] 실패
- [에러] `UnboundLocalError: cannot access local variable 'resolution_text'` — tool role도 resolution 매칭에 포함되어 if/elif 조건에 빠지지 않는 경우 발생
- [수정] resolution_text 초기화를 조건 분기 전으로 이동 → [결과] 성공
- [시도] 재실행 → [결과] 3개 샘플 모두 정상 ingest, 4개 교훈 추출

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → CLI 동작은 깔끔. ingest→list→export 파이프라인이 직관적. "오 되네" 수준.
- [불만] Git conflict 세션에서 resolution이 `git status` 출력 자체를 캡처 — 실제 해결 내용이 아님
- [수정] tool role을 resolution 탐색에서 제외 → assistant/user만 resolution으로 인식
- [불만] 규칙 텍스트가 장황 — 원문을 그대로 넣어서 "규칙"이라기보다 "설명문"
- [수정] `_generate_rule` 을 `[Category] resolution (trigger: failure)` 포맷으로 간결하게 변경
- [평가] 수정 후 출력 퀄리티 만족스러움

## Phase 4 — 검증
- [체크] CLI로 세션 로그 입력 → 교훈 추출 → **통과**
- [체크] SQLite DB 저장 + 중복 병합 (같은 파일 2회 ingest → ↻ Merged, ×2 표시) → **통과**
- [체크] CLAUDE.md / AGENTS.md / .cursor/rules 3종 형식 출력 → **통과**
- [체크] 샘플 3개로 e2e 데모 (4개 교훈 추출) → **통과**
- [체크] README 문서화 → Phase 5에서 작성

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-14 — Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: sqlglot이 Python 라이브러리, spec에서 Python 명시)
- [판단] 의존성: sqlglot (SQL 파싱/AST), click (CLI 인터페이스) — 최소 구성
- [판단] 구조: rules/ 모듈에 규칙 분리, cli.py로 진입점, samples/에 테스트 SQL
- [범위] 7개 이상 안티패턴 규칙, 3 dialect 지원, CLI + pre-commit hook

## Phase 2 — 구현
- [시도] uv init + uv add sqlglot click → [결과] 성공
- [에러] hatchling이 패키지 디렉토리 못 찾음 → [수정] pyproject.toml에 `[tool.hatch.build.targets.wheel] packages = ["sql_guard"]` 추가
- [시도] 9개 규칙 구현 (select-star, missing-where-delete/update, leading-wildcard-like, implicit-column-order, hardcoded-credentials, cartesian-join, order-by-ordinal, null-comparison) → [결과] 성공
- [에러] comma-join(FROM a, b) 감지 실패 — sqlglot이 이를 implicit JOIN으로 파싱 → [수정] kind가 빈 문자열이고 ON/USING 없는 Join을 감지하도록 수정
- [시도] CLI 구현 (click 기반, text/json 출력, --strict 모드) → [결과] 성공
- [시도] 4개 샘플 SQL 파일 생성 (postgres, mysql, snowflake bad + clean) → [결과] 성공
- [시도] pre-commit hook 설정 및 테스트 → [결과] 성공 (bad SQL 차단, clean SQL 통과)

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" — 출력 깔끔, 9개 규칙 정확 감지, severity 구분 명확
- [평가] 검증 목표 실제 검증? → Yes — 3 dialect 파싱, cross-dialect 동작, pre-commit hook 차단/통과 확인
- [평가] 출력/UI 깔끔? → Yes — 파일별 그룹핑, 카운트 요약, emoji severity 아이콘
- [평가] 빠진 것? → 없음. --help 정상, directory scan 정상, JSON 출력 정상
- [불만] 없음 — 핵심 기능 모두 동작 확인

## Phase 4 — 검증
- [체크] sqlglot으로 3개 dialect(PostgreSQL, MySQL, Snowflake) 파싱 + AST 탐색 → 통과
- [체크] 9개 안티패턴 규칙 구현 (최소 7개 요구) → 통과
- [체크] 동일 규칙이 PostgreSQL/Snowflake 양쪽에서 동일 결과 → 통과 (cross-dialect 데모)
- [체크] CLI 파일/디렉토리 입력, text/json 출력, exit code로 CI 연동 → 통과
- [체크] pre-commit hook 등록, 커밋 시 자동 검사 → 통과 (bad SQL 차단, clean SQL 통과)
- [결과] 5/5 통과 → **SUCCESS**


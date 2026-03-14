# STATUS: SUCCESS

## 요약
sqlglot AST 기반으로 9개 SQL 안티패턴을 감지하는 CLI 도구. PostgreSQL/MySQL/Snowflake cross-dialect 지원, pre-commit hook으로 CI 워크플로에 통합 가능.

## 완료 기준 결과
- [x] sqlglot으로 3개 dialect(PostgreSQL, MySQL, Snowflake) 파싱 + AST 탐색 — 통과
- [x] 9개 안티패턴 규칙 구현 (최소 7개 요구) — 통과
- [x] 동일 규칙이 dialect 변경 없이 PostgreSQL/Snowflake 양쪽 동작 — 통과
- [x] CLI 파일/디렉토리 입력 → 감지 결과 출력 (exit code CI 연동) — 통과
- [x] pre-commit hook 자동 검사 동작 확인 — 통과

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-14
- 원본 spec: sql-ci-static-guard.md
- 자동 생성: prototype-pipeline spawn

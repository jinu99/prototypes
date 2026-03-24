# STATUS: SUCCESS

## 요약
pg_stat_statements JSON 스냅샷을 오프라인으로 분석하여 N+1 패턴, Seq Scan, Missing Index, 비효율 Nested Loop 등 5가지 안티패턴을 감지하고 CREATE INDEX 등 구체적 개선 제안을 출력하는 Python CLI 도구.

## 완료 기준 결과
- [x] 샘플 pg_stat_statements JSON 데이터를 입력받아 쿼리 핑거프린팅 후 N+1 패턴 후보를 출력한다
- [x] 샘플 EXPLAIN JSON을 파싱하여 Seq Scan, 비효율 Nested Loop 등 안티패턴을 감지하고 구체적 개선 제안(예: CREATE INDEX 문)을 출력한다
- [x] total_exec_time × calls 기준 Top-N 비용 쿼리를 우선순위 리포트로 출력한다
- [x] CLI로 `analyze --input snapshot.json` 형태로 실행 가능하다
- [x] 최소 3개 안티패턴 규칙(N+1, Seq Scan on large table, Missing Index)이 동작한다

## 실행 방법
```bash
uv sync
uv run sql-perf analyze --input samples/snapshot.json
```

## 소요 정보
- 생성일: 2026-03-24
- 원본 spec: sql-query-perf-advisor.md
- 자동 생성: prototype-pipeline spawn

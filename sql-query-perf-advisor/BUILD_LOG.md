# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-24
- [판단] 스택 선택: Python + click + rich (이유: Spec이 Python CLI를 명시, click은 argparse보다 서브커맨드 지원이 편하고, rich는 테이블/컬러 출력에 최적)
- [판단] 패키지명: sql_perf_advisor (uv + setuptools 호환)
- [범위] 오프라인 분석 모드만. DB 연결 없이 JSON 스냅샷 파싱

## Phase 2 — 구현
- [시도] src/ 디렉토리로 모듈 분리 → [결과] 실행은 되지만 `uv pip install -e .`에서 패키지 인식 실패
- [에러] setuptools flat-layout에서 samples/, screenshots/ 등을 패키지로 오인 → [수정] `sql_perf_advisor/`로 리네임 + `[tool.setuptools.packages.find]` 설정
- [시도] MISSING_INDEX와 SEQ_SCAN_LARGE_TABLE 중복 출력 → [수정] 동일 테이블에 대해 MISSING_INDEX가 있으면 SEQ_SCAN 제거
- [시도] BETWEEN 조건에서 created_at이 2번 추출됨 → [수정] _extract_filter_columns()에서 중복 제거
- [시도] N+1 FK 추론이 `orders.users_id`로 잘못 생성 → [수정] 테이블명에서 trailing 's' 제거하여 `user_id` 생성

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → Rich 테이블이 깔끔하고 CREATE INDEX 문까지 제안하므로 "오 되네" 수준
- [평가] 검증 목표 달성? → N+1 패턴 감지, EXPLAIN 파싱, Top-N 리포팅 모두 동작
- [평가] 출력 품질? → 색상 구분, 섹션 분리, severity 레벨 표시 적절
- [평가] 빠진 것? → 프로토타입 범위 내에서 충분. CSV 입력은 Spec에서 선택사항이므로 JSON만 지원
- [불만] 없음. 개선 루프 불필요

## Phase 4 — 검증
- [체크] 쿼리 핑거프린팅 + N+1 패턴 출력 → 통과 (2개 패턴 감지: paired + unpaired)
- [체크] EXPLAIN JSON 안티패턴 감지 + CREATE INDEX 제안 → 통과 (4개 쿼리에서 5개 발견)
- [체크] Top-N 비용 쿼리 리포트 → 통과 (cost_score = total_exec_time × calls 기준 정렬)
- [체크] CLI `analyze --input snapshot.json` → 통과
- [체크] 최소 3개 안티패턴 규칙 → 통과 (N+1, SEQ_SCAN_LARGE_TABLE, MISSING_INDEX, INEFFICIENT_NESTED_LOOP, N+1 Suspect 5개)

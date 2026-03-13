# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-08
- [목표] Git diff에서 변경 Python 함수 식별 → 변경 전/후 성능 비교 → 터미널 리포트
- [판단] 스택 선택: Python + uv (이유: spec이 Python AST 파싱을 명시, Python 표준 라이브러리로 ast/subprocess/tracemalloc 모두 가능)
- [판단] 의존성: rich (터미널 테이블 출력용) — 나머지는 표준 라이브러리로 커버
- [판단] 구조: perf_verify/ 패키지 (diff_parser, ast_analyzer, benchmarker, reporter, cli)

## Phase 2 — 구현
- [시도] 초기 구현: 모든 모듈 작성 → [결과] 성공
- [시도] demo.sh로 e2e 테스트 → [결과] 실패 (SCRIPT_DIR 경로 문제)
- [수정] $(dirname "$0") → SCRIPT_DIR 변수로 절대 경로 사용 → 성공
- [시도] `uv run perf-verify` CLI 테스트 → [결과] 실패 (ModuleNotFoundError)
- [에러] flat-layout에서 모듈 import 실패 → [수정] perf_verify/ 패키지 구조로 전환, pyproject.toml에 setuptools 패키지 설정 추가
- [시도] python → python3 (시스템에 python 심볼릭 링크 없음) → 성공
- [결과] 전체 파이프라인 동작 확인: diff 파싱 → AST 분석 → 벤치마크 → 리포트

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. fibonacci 10.6x, sort_data 11.5x 느려짐 정확히 감지.
- [평가] Spec 검증 목표 달성? → 달성. 변경 함수 식별 + 성능 비교 + 경고 + exit code 모두 동작.
- [불만] 테이블이 터미널 폭을 초과하여 Status 컬럼이 잘림 → [개선] 컬럼 수 축소 (8→6), 헤더 줄바꿈, show_lines=True 적용 → 깔끔하게 표시됨
- [평가] 개선 후 출력 깔끔하고 읽기 쉬움. 만족.

## Phase 4 — 검증
- [체크] `perf-verify` CLI로 변경 함수 목록 출력 → 통과 (add만 감지, multiply 정확히 제외)
- [체크] 변경 전/후 테스트 기반 벤치마크 실행 → 통과 (테스트 자동 발견 및 반복 실행)
- [체크] before/after 비교 테이블 출력 → 통과 (rich 테이블, 깔끔한 6컬럼 레이아웃)
- [체크] 임계값 초과 시 경고 + exit code 1 → 통과 (11.1x SLOWER 감지, exit 1)
- [체크] 샘플 프로젝트 e2e 데모 → 통과 (demo.sh 완전 동작)
- [결과] 5/5 통과 → SUCCESS

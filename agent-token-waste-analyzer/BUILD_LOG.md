# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-12 — Spec 분석 시작
- [판단] 스택 선택: Python + Rich (이유: JSONL 파싱은 표준 라이브러리 json으로 충분, Rich가 터미널 대시보드에 최적, uv로 의존성 관리 간편)
- [판단] 구조: parser.py(JSONL 파서), analyzer.py(패턴 감지 엔진), dashboard.py(Rich 대시보드), main.py(진입점)
- [확인] Claude Code 세션 로그 구조 분석 완료 — type 필드로 메시지 분류, tool_use/tool_result로 tool call 추적, usage 필드로 토큰 수 추출
- [확인] 실제 세션 로그 ~/.claude/projects/ 하위에 존재 확인 (2287개 로그)

## Phase 2 — 구현
- [시도] uv init + uv add rich → [결과] 성공
- [시도] parser.py 작성 — JSONL 라인별 파싱, tool_use 추출, usage 토큰 집계 → [결과] 성공
- [시도] analyzer.py 작성 — 3가지 패턴 감지(repeated_read, unused_search, duplicate_context) + 유효 토큰 비율 산출 → [결과] 성공
- [시도] dashboard.py 작성 — Rich Panel/Table/Text로 대시보드 구성 → [결과] 성공
- [시도] main.py 작성 — CLI (list, analyze, latest 서브커맨드) → [결과] 성공
- [에러] pyproject.toml의 project.scripts 진입점이 `src` 모듈을 찾지 못함 → [수정] run.py 래퍼로 `uv run python run.py` 방식 채택
- [시도] 샘플 세션 로그 생성기 작성 (samples/generate_sample.py) → [결과] 성공
- [시도] 실제 세션 로그(5f593cfd)로 테스트 — 107개 tool call, 9개 패턴 감지 → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 대시보드가 깔끔하고 정보 구조화가 잘됨. "오 되네" 수준.
- [불만] 핫스팟 테이블에서 파일 경로가 truncate되어 가독성 나쁨 → [개선] basename 축약 로직 추가 (.../src/auth.py 형태)
- [평가] 검증 목표 달성 여부 → 3가지 패턴 감지 + 유효 토큰 비율 + 대시보드 + 최적화 제안 모두 동작
- [평가] 출력 깔끔한가 → 개선 후 만족
- [평가] 빠진 것 → 없음. help도 잘 출력됨.

## Phase 4 — 검증
- [체크] tool call 시퀀스 추출 → 통과 (실제 세션에서 10개 tool call 정상 추출)
- [체크] 반복 파일 읽기 감지 + 중복 횟수/낭비량 리포트 → 통과 (auth.py 4회, models.py 2회)
- [체크] 유효 토큰 비율 산출 → 통과 (37.0% effective ratio, total = effective + wasted 검증)
- [체크] 핫스팟 Top 5 + 최적화 제안 표시 → 통과 (5개 핫스팟, 3개 제안)
- [체크] 실제 세션 로그 e2e 데모 → 통과 (5f593cfd 세션: Grade D, 47.3% waste)
- 결과: 5/5 통과 → **SUCCESS**

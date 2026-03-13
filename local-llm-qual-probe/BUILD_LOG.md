# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-07
- [목표] 소형 로컬 LLM의 실패 패턴(JSON 깨짐, 멀티턴 붕괴, 과잉 출력)을 한 줄 명령으로 감지하는 CLI
- [범위] 구조화 출력 진단, 멀티턴 안정성 테스트, 토큰 효율성 검사, 터미널+JSON 리포트
- [판단] 스택 선택: Python + uv + OpenAI SDK (이유: Spec에 명시, OpenAI-호환 API 호출에 최적)
- [판단] 추가 의존성: rich (터미널 리포트 포맷팅), pyyaml (YAML 파싱 테스트)
- [판단] 파일 구조: 모듈별 분리 (probes/structured.py, probes/multiturn.py, probes/efficiency.py, reporter.py, cli.py)
- [판단] mock 전략: 실제 Ollama 없이도 --mock 플래그로 테스트 가능하도록 mock 모드 내장

## Phase 2 — 구현
- [시도] uv init + uv add openai rich pyyaml → [결과] 성공
- [시도] client.py: OpenAI SDK 래퍼 + mock 모드 → [결과] 성공
- [시도] probes/structured.py: JSON/YAML 파싱 + 스키마 검증 → [결과] 성공
- [시도] probes/multiturn.py: 7턴x2 대화 + 반복/망각 감지 → [결과] 성공
- [시도] probes/efficiency.py: thinking on/off + 시스템 프롬프트 변형 비교 → [결과] 성공
- [시도] reporter.py: Rich 테이블 리포트 + JSON 내보내기 → [결과] 성공
- [시도] cli.py: argparse 엔트리포인트 → [결과] 성공
- [시도] pyproject.toml에 [project.scripts] 추가 → [결과] 성공
- [시도] 첫 실행 → [결과] 실패 — `uv run llm-qual-probe`이 실행 안 됨
- [수정] `uv pip install -e .`로 editable install → [결과] 성공
- [에러] 멀티턴 mock이 3개 고정 응답만 반환 → 반복 감지 오탐(stability 35.7%)
- [수정] mock 응답을 턴별 문맥 인식으로 개선 → stability 92.9%
- [에러] 효율성 프로브: thinking on/off 토큰이 동일(162 vs 162) — "reasoning" 키워드가 thinking_off 시스템 프롬프트에도 포함
- [수정] is_thinking 감지를 "show your reasoning"으로 변경 → 162 vs 43 (overhead 276.7%)

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. Rich 테이블로 PASS/WARN/FAIL 색상 구분이 깔끔함
- [평가] Spec 검증 목표 → 3가지 프로브 모두 구현, 한 줄 명령으로 실행 가능
- [평가] 출력 깔끔한가? → 대체로 OK. "Hallucinated fields" 표현이 혼란스러움
- [불만] "Hallucinated fields" → [개선] "Extra fields (not in schema)"로 변경
- [불만] JSON 리포트에 타임스탬프 없음 → [개선] timestamp 필드 추가
- [평가] 빠진 것? → --help 정상 동작 확인, 핵심 흐름 문제 없음

## Phase 4 — 검증
- [체크] 기준1: 한 줄 명령으로 구조화 출력 테스트 + 파싱 성공률 숫자 출력 → 통과 (Parse: 87.5%)
- [체크] 기준2: 5턴 이상 자동 대화 + 붕괴 시점 감지 → 통과 (14턴, Turn 7 collapse 감지)
- [체크] 기준3: thinking on/off 토큰 비교 효율성 리포트 → 통과 (162 vs 43, overhead 276.7%)
- [체크] 기준4: JSON 내보내기 + 터미널 PASS/WARN/FAIL 요약 → 통과
- [결과] 4/4 통과 → SUCCESS

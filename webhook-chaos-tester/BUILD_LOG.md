# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-15 — Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: Spec이 Python/uv 또는 Go 권장. Python은 httpx로 HTTP 제어가 간결하고, YAML 파싱/CLI 구현이 최소 의존성으로 가능)
- [판단] 의존성: httpx(HTTP 클라이언트), pyyaml(시나리오 파일), click(CLI) — 최소 3개
- [판단] 구조: CLI 진입점, 시나리오 실행 엔진, 에코 서버, 리포트 생성기로 분리 (각 모듈 300줄 미만)

## Phase 2 — 구현
- [시도] uv init + uv add httpx pyyaml click → [결과] 성공
- [시도] echo_server.py 작성 (http.server 기반, 스레드) → [결과] 성공
- [시도] engine.py 작성 (duplicate/delay/reorder 3종) → [결과] 성공
- [시도] loader.py + scenarios/*.yaml 작성 → [결과] 성공
- [시도] report.py (Markdown/JSON 생성) → [결과] 성공
- [시도] cli.py (click 기반, run/echo/demo 3개 명령) → [결과] 성공
- [에러] pyproject.toml에 build-system 없어서 entry point 설치 안 됨 → [수정] hatchling 추가 + wheel packages 설정
- [에러] hatchling이 패키지 디렉토리를 못 찾음 (webhook-chaos-tester vs webhook_chaos) → [수정] tool.hatch.build.targets.wheel.packages 명시
- [시도] `uv run webhook-chaos demo` 실행 → [결과] 성공, 3/3 PASS

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. demo 명령 하나로 즉시 확인 가능.
- [평가] 검증 목표 달성 여부 → reject-duplicates 모드에서 duplicate 시나리오가 FAIL로 정확히 감지됨. 카오스 테스팅이 실제 결함을 찾는 모습 확인.
- [불만] 리포트의 Type 필드가 name.split('-')[0]으로 잘못 파싱됨 ("out-of-order" → "out") → [개선] ScenarioResult에 type 필드 추가, CLI에서 시나리오 메타데이터 전달
- [불만] CLI 출력이 무채색 → [개선] click.style로 PASS/FAIL 색상, 타겟 URL 하이라이팅, 결과 요약 색상 추가
- [불만] run/demo 명령에 시나리오 실행 로직 중복 → [개선] _execute_scenarios 함수로 리팩토링

## Phase 4 — 검증
- [체크] `webhook-chaos run --target <URL>` 기본 시나리오 3종 실행 → 통과
- [체크] YAML 파일로 커스텀 시나리오 정의 (stress.yaml) → 통과
- [체크] PASS/FAIL 판정 + Markdown 리포트 → 통과
- [체크] PASS/FAIL 판정 + JSON 리포트 → 통과
- [체크] 에코 서버 포함 자체 데모 (demo 명령) → 통과
- [체크] README 사용법 + 시나리오 작성 가이드 → 통과
- [결과] 전부 통과 → SUCCESS

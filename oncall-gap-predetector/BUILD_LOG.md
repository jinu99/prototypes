# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-17
- [스펙] Docker Compose + Prometheus config 정적 분석으로 모니터링 사각지대 탐지 CLI
- [판단] 스택 선택: Python + uv (이유: YAML 파싱이 핵심이고 PyYAML이 성숙함. argparse로 CLI 구성하여 외부 의존성 최소화. click 대신 argparse 선택 — 의존성 1개 줄임)
- [판단] 파일 구조: models.py(데이터클래스) → parser.py(YAML 파싱) → analyzer.py(타입 추론+갭 분석) → reporter.py(JSON/MD 출력) → cli.py(CLI) → main.py(진입점)
- [판단] 샘플 데이터를 먼저 작성하여 입력 계약 정의 후 구현

## Phase 2 — 구현
- [시도] 샘플 configs 3개(docker-compose, prometheus, alert_rules) 작성 → [결과] 성공
- [시도] models.py 데이터클래스 6개 정의 → [결과] 성공
- [시도] parser.py — Docker Compose/Prometheus/AlertRule 파서 3개 → [결과] 성공
- [시도] analyzer.py — 서비스 타입 추론(IMAGE_TYPE_MAP + PORT_TYPE_MAP) + 갭 분석 → [결과] 성공
- [시도] reporter.py — JSON + Markdown 출력 (커버리지 바 포함) → [결과] 성공
- [시도] cli.py — scan/demo 서브커맨드 + 파일 출력 옵션 → [결과] 성공
- [시도] `uv run python main.py demo` 실행 → [결과] 성공. 8 서비스 분석, JSON+MD 출력 정상
- [시도] `uv run python main.py scan --output /tmp/oncall-test` → [결과] 성공. 파일 저장 확인

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. 8개 서비스에서 5개 미모니터링 탐지, 커버리지% 표시 깔끔
- [평가] 검증 목표 달성 → 정적 분석만으로 모니터링 사각지대 자동 탐지 동작
- [평가] 출력 깔끔 → 커버리지 바, 이모지, 서비스별 상세 갭 다 있음
- [평가] 빠진 것 → 없음. end-to-end 흐름 완성
- [판단] 개선 불필요 → Phase 4 진행

## Phase 4 — 검증
- [체크] Docker Compose에서 서비스 추출 + Prometheus 타겟 비교 → 통과 (8 서비스 추출, 5개 미모니터링 탐지)
- [체크] 서비스 타입 추론 (image + port) → 통과 (nginx→http, postgres→database, redis→cache, rabbitmq→queue, grafana→monitoring, worker→unknown)
- [체크] 필수 메트릭 체크리스트 대비 alert rule 커버리지 분석 → 통과 (api 75%, postgres 40%, 나머지 0%)
- [체크] 샘플 설정 파일로 end-to-end 데모 → 통과 (`uv run python main.py demo`)
- [체크] JSON + Markdown 형식 출력 → 통과 (valid JSON, UTF-8 Markdown)
- [결과] 5/5 통과 → **SUCCESS**

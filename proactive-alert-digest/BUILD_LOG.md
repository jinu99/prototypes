# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-17 Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: spec 명시)
- [판단] 의존성: click(CLI), PyYAML(설정), Jinja2(템플릿), requests(HTTP 체크)
  - click: argparse보다 서브커맨드 관리가 깔끔하고, 프로토타입 수준에서 충분히 가벼움
  - docker SDK 대신 subprocess로 `docker ps` 호출 — 의존성 최소화
- [판단] 플러그인 구조: Protocol 기반 (ABC 대비 상속 불필요, duck typing으로 확장 용이)
- [판단] 파일 구조: src/ 없이 flat 구조 (프로토타입이므로 단순하게)

## Phase 2 — 구현
- [시도] models.py (Severity enum + Alert dataclass + SourcePlugin Protocol) → [결과] 성공
- [시도] 3개 플러그인 (http_check, log_pattern, docker_status) → [결과] 성공
- [시도] engine.py (YAML 로드 + 플러그인 인스턴스화 + 폴링) → [결과] 성공
- [시도] renderer.py + Jinja2 템플릿 (심각도별 정렬, "오늘 확인할 것" 섹션) → [결과] 성공
- [시도] slack.py (webhook 전송) → [결과] 성공
- [시도] cli.py (click 기반 `init` + `run` 명령) → [결과] 성공
- [시도] prometheus_mock 플러그인 (확장성 데모) → [결과] 성공
- 에러 없이 첫 시도에 전체 파이프라인 동작 확인

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → `init → run` 두 명령이면 즉시 동작하고, 다이제스트 출력이 깔끔하게 나옴. "오 되네" 수준
- [평가] 검증 목표: YAML만으로 멀티소스 폴링 → 다이제스트 생성 확인됨 ✓
- [평가] 출력 품질: 심각도별 아이콘(🔴🟡🟢), "오늘 확인할 것" 요약 섹션, 테이블 구조 모두 깔끔
- [평가] 빠진 것: 없음. 핵심 흐름 완전
- [테스트] 다양한 시나리오 실행: 정상/실패 URL, 존재하지 않는 로그, 빈 설정, --slack 플래그 → 모두 정상 동작

## Phase 4 — 검증
- [체크] `digest init`으로 샘플 YAML 생성 (3개 소스 타입) → 통과
- [체크] HTTP/로그/Docker 플러그인 동작 → 통과
- [체크] 심각도별 정렬 마크다운 다이제스트 → 통과
- [체크] Slack webhook 전송 → 통과
- [체크] 새 플러그인 확장 데모 (prometheus_mock) → 통과
- **결과: 5/5 SUCCESS**

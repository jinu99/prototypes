# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-15 — Spec 파일 확인 완료
- [범위] .env에서 시크릿 수집 → 쉘 래퍼로 stdout/stderr 인터셉트 → 시크릿 마스킹 → entropy 기반 탐지 → 마스킹 로그
- [판단] 스택 선택: Python + uv
  - 이유: 쉘 래퍼/subprocess 제어가 Python이 가장 자연스럽고, detect-secrets 라이브러리가 Python 네이티브
  - 표준 라이브러리의 subprocess, re, math(entropy 계산)으로 대부분 커버 가능
  - detect-secrets는 외부 의존성이지만 spec에서 명시적으로 언급하므로 채택 (실제로는 자체 entropy/pattern 탐지가 충분)

## Phase 2 — 구현
- [시도] 3개 모듈 분리 (registry.py, detector.py, scrubber.py + main.py CLI) → [결과] 성공
- [시도] 데모 실행 → [결과] 실패
  - [에러] auto_discover에서 .env 이중 로딩 (*.env glob + .env 직접 로드)
  - [수정] _loaded_files set으로 중복 방지
  - [에러] TOKEN_PATTERN에 `=` 포함되어 `KEY=value`가 하나의 토큰으로 잡힘 → entropy false positive
  - [수정] TOKEN_PATTERN에서 `=` 제거
  - [에러] env var 키 이름(HARMLESS_VAR 등)이 entropy 탐지에 잡힘
  - [수정] ALL_CAPS_UNDERSCORE 패턴 false positive 필터 추가
- [시도] 수정 후 재실행 → [결과] 성공 — 5개 시크릿 정확히 마스킹, false positive 제거
- [시도] entropy 전용 탐지 테스트 (레지스트리에 없는 고엔트로피 문자열) → [결과] 성공
- [시도] exit code 보존 테스트 (exit 42) → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 깔끔한 마스킹 + 메타정보 stderr 분리 → "오 되네"
- [불만] stdout/stderr 처리가 순차적 (stdout 끝나야 stderr 처리) → 인터리빙 부재
- [개선] selectors 기반 비동기 스트림 처리로 교체 → stdout/stderr 실시간 인터리빙
- [불만] DATABASE_URL에 임베디드된 비밀번호 미탐지
- [개선] Connection URL 비밀번호 패턴 `://[^:]+:([^@\s]{8,})@` 추가
- [재평가] 모든 항목 만족

## Phase 4 — 검증
- [체크] .env에서 시크릿 자동 수집 → 통과 (5개 수집, 비시크릿 제외)
- [체크] 쉘 래퍼로 stdout 마스킹 → 통과 (cat .env 시 모든 시크릿 값 ***로 마스킹)
- [체크] entropy 기반 탐지 → 통과 (레지스트리 미등록 고엔트로피 문자열 entropy=1로 탐지)
- [체크] 데모: cat .env 래핑 실행 → 통과 (uv run main.py demo 완전 동작)
- [체크] exit code/출력 구조 보존 → 통과 (0, 1, 2, 42, 127 모두 보존, 빈 줄/탭 유지)
- **결과: 5/5 통과 → SUCCESS**

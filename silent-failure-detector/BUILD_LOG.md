# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 읽기 완료. 검증 목표: OTel 없이 미들웨어로 "HTTP 200이지만 비즈니스 로직 실패" 탐지
- [판단] 스택 선택: Node.js + Express (이유: Spec이 Express/Fastify 명시, 미들웨어 패턴 자연스러움)
- [판단] SQLite: better-sqlite3 (이유: 동기 API, native addon이지만 빌드 안정적)
- [판단] YAML 파싱: js-yaml (사실상 표준)

## Phase 2 — 구현
- [시도] npm init + express 설치 → [결과] Express v5.2.1 설치됨 (v5!)
- [시도] 핵심 모듈 작성 (db, rules, middleware, demo-service, dashboard-api) → [결과] 성공
- [시도] 서버 기동 + curl 테스트 → [결과] 첫 시도에서 404 에러
- [에러] Express v5에서 라우트 404 → [수정] 기존 포트에 좀비 프로세스가 남아있었음. kill 후 정상 동작
- [시도] CLI demo (run-demo.js) 실행 → [결과] 3가지 시나리오 모두 silent failure 정확히 탐지
- [시도] Dashboard HTML + API 연동 → [결과] curl로 HTML 응답 확인, API 정상 동작

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네". CLI 출력에 Expected/Actual이 명확하고, 3종 시나리오 모두 탐지
- [평가] 검증 목표 → YAML 선언적 규칙 → 비동기 assertion → SQLite 저장 → 대시보드 확인 흐름 완성
- [불만] Playwright 실행 불가 (시스템에 libatk 미설치, sudo 없음) → 대시보드 렌더링은 curl + API 레벨로 검증
- [평가] 출력 깔끔함 — CLI demo에서 시나리오별 결과가 읽기 좋고, API 응답도 정형화됨
- [판단] 대시보드 UI는 DOM API로 XSS-safe하게 구현, 다크테마로 깔끔한 편

## Phase 4 — 검증
- [체크] 선언적 규칙 파일(YAML)로 엔드포인트별 성공 조건 정의 → 통과 (rules.yaml에 3개 규칙, body_contains/body_check/callback 타입)
- [체크] 미들웨어가 200 응답 후 비동기로 assertion 실행 + SQLite 기록 → 통과 (setImmediate로 비동기, better-sqlite3로 저장)
- [체크] 데모 3가지 시나리오 탐지 → 통과 (정상=통과, 200+DB미반영=탐지, 200+부분실패=탐지, 간헐적=탐지)
- [체크] 웹 대시보드에서 로그 확인 (시간순 + 엔드포인트별 집계) → 통과 (API: /api/failures, /api/stats 정상)
- [체크] README에 설치→규칙 작성→데모 실행 가이드 → Phase 5에서 작성 예정

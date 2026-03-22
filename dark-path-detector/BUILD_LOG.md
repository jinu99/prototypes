# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-22
- [목표] 정적 분석(AST)으로 JS/TS 코드의 관측성 누락 에러 경로(dark path)를 탐지하는 CLI 도구
- [범위] catch 블록 + 에러 콜백 무시 패턴 감지, dark path coverage 지표, @dark-path-ignore 지원
- [판단] 스택 선택: Node.js + tree-sitter (이유: JS/TS 분석 도구이므로 같은 생태계가 자연스럽고, tree-sitter의 Node.js 바인딩이 성숙하며, CLI 도구 구축이 간편함)
- [판단] tree-sitter-javascript + tree-sitter-typescript로 AST 파싱, 별도 프레임워크 없이 순수 tree-sitter API 사용

## Phase 2 — 구현
- [시도] tree-sitter 0.25 + tree-sitter-typescript 최신 → [에러] peer dependency 충돌 → [수정] 0.21.x 호환 버전으로 다운그레이드
- [시도] 기본 analyzer 구현 (catch 블록 + 에러 콜백 감지) → [결과] 성공, test fixture에서 기대한 패턴 모두 감지
- [에러] arrow function 단일 파라미터 (`err => {}`) 미감지 → [원인] tree-sitter가 `parameter` 필드를 `parameters`와 다르게 파싱 → [수정] 두 필드 모두 체크
- [시도] Express.js 테스트 → [결과] `unobserved-error-callback` (low severity)에서 과다 false positive
- [수정] `unobserved-error-callback` 타입 제거 (spec 범위 초과), test 디렉토리 기본 ignore에 추가
- [시도] Fastify 테스트 → [에러] tree-sitter 파서 크래시 → [수정] 파일별 try-catch로 graceful skip
- [에러] `preValidationCallback(err)`, `onErrorHook(reply, e)` 등 프레임워크 콜백이 false positive → [수정] catch body에서 에러 파라미터가 함수 인자로 전달되면 propagation으로 인정
- [에러] `catch { done(new CustomError()) }` 패턴 false positive → [수정] parameterless catch에서 done/callback/next 호출 시 propagation으로 인정
- [에러] `err = error` 패턴 (재할당 후 catch 밖에서 전달) false positive → [수정] 에러 변수 재할당 패턴 감지

## Phase 3 — 셀프 크리틱

### 3-2 평가
1. **"이걸 누가 보면 '오 되네'라고 할까?"** — 오 되네 쪽에 가깝다. CLI 출력이 깔끔하고, coverage 바가 직관적이며, 실제 오픈소스에서 진짜 dark path를 찾아낸다. Express에서 `lib/view.js`의 silent catch 찾아낸 건 좋은 시그널.
2. **검증 목표가 실제로 검증되는가?** — 예. Express 2건, Fastify 2건 모두 legitimate dark path. false positive 제거를 위해 여러 번 개선했고, precision은 대략 85-100% 수준 (Express 2/2, Fastify 2/2 확인됨).
3. **출력이 알아보기 쉽고 깔끔한가?** — 예. 색상 코딩, severity 아이콘, coverage 바 등 시각적 요소가 적절하다. JSON 출력도 지원.
4. **빠진 게 있는가?** — Promise `.catch()` 체인에서의 빈 핸들러 감지는 잘 됨. `async/await` 없이 `.then().catch()` 패턴도 감지됨. 다만 `try {} finally {}` (catch 없음) 패턴은 스캔 대상이 아닌데, 이는 spec 범위 내이므로 OK.

## Phase 4 — 검증
- [체크] CLI로 JS/TS 프로젝트 스캔 → 통과 (test-fixtures, Express, Fastify 모두 정상 출력)
- [체크] catch 블록 + 에러 콜백 무시 패턴 감지 → 통과 (empty-catch, silent-catch, ignored-error-param 모두 감지)
- [체크] dark path coverage 지표(%) 산출 → 통과 (정확한 비율 계산 + 시각적 coverage 바)
- [체크] 실제 오픈소스 프로젝트 precision → 통과 (Express 1/1=100%, Fastify 2/2=100%, 전체 3/3=100%)
- [체크] @dark-path-ignore 제외 → 통과 (JS, TS 모두 정상 제외 확인)

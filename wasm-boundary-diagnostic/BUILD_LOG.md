# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-21
- [목표] wasm-bindgen `_bg.js` 글루 코드를 정적 분석하여 JS↔WASM 경계 함수의 직렬화 비용을 식별하고 최적화 추천을 제공하는 CLI 도구
- [판단] 스택 선택: Python + uv (이유: 텍스트 파싱/패턴 매칭에 강하고, rich 라이브러리로 터미널 리포트를 깔끔하게 출력 가능. JS AST 파서 대신 정규식 기반 패턴 매칭으로 충분 — wasm-bindgen 글루 코드는 정형화된 구조를 가짐)
- [판단] 파싱 방식: 정규식 패턴 매칭 (이유: wasm-bindgen이 생성하는 글루 코드는 `__wbg_`, `__wbindgen_` 등 일관된 패턴을 사용하므로 AST 파싱 없이도 충분히 정확한 추출 가능)
- [판단] 의존성: `rich` (터미널 리포트), `click` (CLI) — 최소한으로 유지

## Phase 2 — 구현
- [시도] 프로젝트 초기화 (uv init + uv add rich click) → [결과] 성공
- [시도] 샘플 wasm-bindgen 글루 코드 작성 (image_processor_bg.js) → [결과] 성공. 실제 wasm-bindgen 출력 패턴을 재현: export/import 함수, passStringToWasm, getStringFromWasm, passArray8ToWasm, passArrayJsValueToWasm, addHeapObject, getObject, takeObject 등
- [시도] parser.py — 정규식으로 export function 추출, body에서 직렬화 패턴 매칭으로 타입 추론 → [결과] 성공
- [시도] cost_model.py — 타입→비용 등급 매핑, 총점 기반 overall 등급 산출 → [결과] 성공
- [시도] recommender.py — 5가지 최적화 패턴(opaque handle, serde-wasm-bindgen, batch, typed array, cache) → [결과] 성공
- [시도] report.py — Rich 테이블/패널로 터미널 리포트 렌더링 → [결과] 성공
- [시도] cli.py + pyproject.toml 엔트리포인트 설정 → [에러] hatchling이 패키지를 찾지 못함
- [수정] `[tool.hatch.build.targets.wheel] packages = ["src"]` 추가 → [결과] 성공
- [시도] CLI 실행 (wasm-diag samples/image_processor_bg.js) → [결과] 성공. 19개 함수 추출, 비용 분석 및 추천 출력

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 리포트 자체는 괜찮으나 import 함수의 타입 추론에 오류 발견
- [불만] `__wbg_createElement`의 return이 `string`으로 잘못 추론됨 — body에 `getStringFromWasm0`이 있지만 이건 param 디코딩용이지 return 구성이 아님
- [불만] import 함수의 ptr+len 쌍 (arg0, arg1이 실제로는 string ptr+len) 미인식
- [개선] 1차: _infer_return_type에 is_import 분기 추가 — import는 `return addHeapObject()`만 jsvalue로 판단
- [개선] 2차: _infer_params에 pair_info 딕셔너리로 ptr+len 쌍 정확히 추적 (getStringFromWasm0(arg0, arg1) → arg0=string_ptr, arg1=string_len)
- [불만] 추천이 함수별로 반복되어 출력이 너무 김
- [개선] 3차: _render_recommendations를 패턴별 그룹핑으로 변경, affected 함수 목록 표시
- [재평가] "오 되네" — import 타입 추론이 정확해짐, createElement가 jsvalue 반환으로 올바르게 표시, 추천 출력 깔끔

## Phase 4 — 검증
- [체크] 기준1: _bg.js 파싱하여 모든 경계 함수와 타입 추출 → **통과** (19개 함수, 10 export / 9 import)
- [체크] 기준2: 타입별 비용 등급 출력 → **통과** (zero/medium/high 분포, 모든 함수와 파라미터에 비용 등급)
- [체크] 기준3: 고비용 함수에 최소 3가지 패턴 추천 → **통과** (5가지: opaque_handle, serde_wasm_bindgen, batch_processing, typed_array, cache_boundary)
- [체크] 기준4: 샘플에 대해 e2e 리포트 생성 데모 → **통과**
- [결과] **4/4 통과 → SUCCESS**

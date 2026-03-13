# Build Log

## Phase 1 — Spec 확인

- [시작] 2026-03-03
- [Spec] 검증 목표: AST 블록 경계 분석 기반 자동 페이지 분할이 표/코드 블록 페이지 중간 잘림을 줄이는지 검증
- [범위] Markdown → AST → Typst(breakable hint) → PDF, CLI 인터페이스, Pandoc과 before/after 비교
- [완료 기준]
  1. MD→AST 파싱 + 블록 경계 식별 파이프라인
  2. 블록 경계→Typst breakable 힌트→PDF 생성
  3. 표 3+, 코드블록 3+ 포함 테스트 MD에서 블록 중간 잘림 없음 확인
  4. Pandoc 기본 변환 vs 이 도구 before/after 비교 PDF
  5. CLI `docconv convert input.md -o output.pdf`

- [판단] 스택 선택: **Node.js** (이유: remark/unified가 Markdown AST 조작에 가장 성숙한 생태계. markdown-it-py 대비 AST 노드 순회/변환 유틸이 풍부. Typst 마크업 생성은 문자열 처리이므로 언어 무관.)
- [판단] 핵심 의존성:
  - `unified` + `remark-parse` + `remark-gfm`: Markdown→AST (GFM 테이블 지원)
  - `commander`: CLI 인터페이스
  - Typst CLI (v0.14.2): PDF 렌더링
  - Pandoc (v3.6.4): before/after 비교용
- [판단] 바이너리 경로: `/home/jinu/.local/bin/typst`, `/home/jinu/.local/bin/pandoc`

## Phase 2 — 구현

- [시도] npm init + 의존성 설치 → [결과] 성공
- [시도] parser.js (remark-parse) → analyze 명령 → [결과] 테이블 0개 감지
- [에러] remark-parse 기본은 GFM 테이블 미지원 → [수정] remark-gfm 추가 → 테이블 4개 정상 식별
- [시도] typst-gen.js (AST→Typst 변환) → [결과] 성공, breakable:false 적용 확인
- [시도] renderer.js (Typst/Pandoc PDF 생성) → [결과] Typst 성공
- [에러] Pandoc --pdf-engine=typst에서 폰트 에러 → [수정] -V mainfont 및 --pdf-engine 경로 명시 → 성공
- [시도] CLI (convert/compare/analyze) → [결과] 세 명령 모두 정상 동작
- [시도] before/after 비교 → [결과] Pandoc PDF 4건 코드블록 분할 vs docconv 0건 분할

## Phase 3 — 셀프 크리틱

### 3-1. 직접 사용
- `convert test-data/sample.md -o output/test.pdf` → 성공 (6페이지 PDF)
- `analyze test-data/sample.md` → 36블록, 테이블4, 코드5, unbreakable 9 정상 출력
- `compare test-data/sample.md` → Pandoc/docconv 양쪽 PDF 생성 성공
- edge case (표/코드 없는 파일) → 성공

### 3-2. 자체 평가
1. **"오 되네"라고 할까?** → "오 되네" 쪽. CLI 깔끔, PDF 품질 양호.
2. **검증 목표 달성?** → Yes. Pandoc 4건 분할 vs docconv 0건. 명확한 차이.
3. **출력 깔끔한가?** → 양호. 코드블록 배경색, 테이블 테두리 있음.
4. **빠진 게 있는가?** → 코드블록 내부 underscore 이스케이프 버그 발견.

### 3-3. 개선 루프
- [불만] 코드블록 내 `_`가 `\_`로 이스케이프되어 `__init__`이 `\_\_init\_\_`로 출력
- [원인] escapeTypst()가 raw block 내부에도 적용됨
- [개선] convertCode()에서 escapeTypst() 제거 (raw block은 이스케이프 불필요)
- [재검증] v3 PDF에서 `__init__`, `error_handlers` 등 정상 렌더링 확인

## Phase 4 — 검증

- [체크] MD→AST 파싱 + 블록 경계 식별 → **통과** (테이블4, 코드5, unbreakable 9 정상 식별)
- [체크] 블록 경계→Typst breakable 힌트→PDF → **통과** (breakable:false 24건, PDF 150KB 생성)
- [체크] 표3+코드3+ 테스트에서 블록 잘림 없음 → **통과** (6페이지 PDF, 0건 분할)
- [체크] Pandoc before/after 비교 PDF → **통과** (Pandoc 7p/4분할 vs docconv 6p/0분할)
- [체크] CLI `docconv convert input.md -o output.pdf` → **통과** (npx . convert 정상 동작)

**결과: 5/5 통과 → SUCCESS**

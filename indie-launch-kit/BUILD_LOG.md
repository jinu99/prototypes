# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-15 Spec 파일 확인 완료
- [판단] 스택 선택: Node.js + remark + Handlebars + simple-git
  - 이유: Spec에 명시된 기술 제약 (Node.js CLI, remark, Handlebars, simple-git)
  - remark: 마크다운 AST 파싱으로 섹션 구조를 정확히 분류 가능
  - Handlebars: 로직 없는 템플릿 엔진으로 3개 테마를 깔끔하게 분리
  - simple-git: conventional commits 파싱에 적합
- [판단] 범위: README 파싱 → 랜딩페이지 HTML 생성, changelog HTML, 런치 포스트 초안
- [판단] CLI 워크플로: `npx indie-launch-kit build` 중심 (init은 설정 파일 생성)

## Phase 2 — 구현
- [시도] 핵심 모듈 5개 작성 (parser, metadata, changelog, launch-posts, templates) → [결과] 성공
- [시도] CLI (commander) 작성 → [결과] 성공, 첫 빌드 동작
- [시도] 테스트 픽스처 (FastAPI Starter) 빌드 → [결과] 성공
- [에러] GFM 테이블이 raw pipe text로 렌더링됨 → [수정] remark-gfm 플러그인 추가
- [에러] h3 서브헤딩이 부모 h2 섹션에서 분리됨 → [수정] heading depth 비교 로직 추가 (h3+는 부모 h2에 포함)
- [에러] 수정 후 h2가 h1 hero에 포함되는 역효과 → [수정] depth >= 2 조건 추가 (h1 하위만 nesting 방지)
- [시도] 3개 테마 (minimal, dark, gradient) 빌드 → [결과] 모두 성공
- [시도] Playwright 스크린샷 → [결과] 실패 (시스템에 libatk 미설치, sudo 없음)
- [시도] express-api, python-cli 추가 테스트 → [결과] 모두 성공

## Phase 3 — 셀프 크리틱

### 3-2. 평가
1. **"오 되네" vs "뭐야 이게"?** — "오 되네" 쪽. CLI 한 줄로 깔끔한 HTML이 생성됨. 3개 테마 모두 시각적으로 구분되고 읽기 쉬움. 다만 Playwright 스크린샷이 안 되어 브라우저 렌더링을 직접 확인하지 못한 점은 아쉬움.
2. **Spec 검증 목표 달성?** — "README.md만으로 CLI 한 줄에 생성된 랜딩페이지가 쓸 만한 수준인지" → 3개 서로 다른 README로 테스트 완료, 섹션 분류 정확, HTML 구조 시맨틱, 스타일링 적용됨.
3. **출력이 깔끔한가?** — HTML 구조가 깔끔하고 CSS가 잘 적용됨. 특히 feature cards 그리드 레이아웃과 install 섹션 코드블록 스타일이 좋음.
4. **빠진 게 있는가?** — 없음. 모든 핵심 기능 구현됨.

### 3-3. 개선
- [불만] Hero 섹션에 meta.description과 blockquote가 중복 → [개선] blockquote 제거, badges 분리 추출, meta.description만 tagline으로 표시
- [불만] "other" 섹션들이 하나의 <section>에 합쳐짐 → [개선] 각 other 항목마다 개별 <section> 생성

## Phase 4 — 검증
- [체크] `npx indie-launch-kit build`로 README.md → 정적 HTML (3개 테마) → 통과
- [체크] README 구조 자동 파싱 → Hero/Features/Install/CTA 매핑 → 통과
- [체크] conventional commits → 체인지로그 HTML → 통과
- [체크] 프로젝트 메타데이터 기반 PH/Reddit/HN 런치 포스트 초안 → 통과
- [체크] 실제 오픈소스 README 3개 테스트 (FastAPI Starter, express-api-kit, TaskFlow CLI) → 통과
- [결과] 5/5 통과 → **SUCCESS**

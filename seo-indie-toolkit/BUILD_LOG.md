# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 확인: seo-indie-toolkit.md
- [판단] 스택 선택: Node.js + npm + Playwright + Cheerio (이유: Spec에서 Node.js/npm/Playwright 명시. Cheerio는 HTML 파싱용 경량 라이브러리로 jsdom보다 가벼움. xml2js는 sitemap 파싱용)
- [판단] 구조: CLI (src/cli.js) + 웹 서버 (src/server.js) + 단일 HTML UI (public/index.html)
- [범위] Lighthouse 연동은 선택사항이므로 제외. 핵심인 JS 실행 전/후 비교에 집중

## Phase 2 — 구현
- [시도] 프로젝트 초기화 (git init, npm init -y, npm install) → [결과] 성공
- [시도] 핵심 모듈 구현 (crawler.js, analyzer.js, reporter.js, sitemap.js) → [결과] 성공
- [시도] CLI 진입점 구현 (cli.js) → [결과] 성공
- [시도] Playwright chromium 실행 → [결과] 실패
- [에러] `libatk-1.0.so.0: cannot open shared object file` — 시스템에 Playwright 실행용 공유 라이브러리 미설치
- [수정] sudo 불가능하여 apt-get download로 .deb 패키지를 다운로드 후 dpkg-deb -x로 수동 추출. LD_LIBRARY_PATH로 설정하는 browser-env.js 모듈 생성 → [결과] 성공
- [시도] CLI 테스트 (angular.dev, react.dev) → [결과] 성공. SSR 사이트라 문제 없음 확인
- [시도] 테스트 SPA 페이지 생성 (test-spa/index.html) → [결과] 성공. 8개 문제 발견
- [시도] 실제 SPA 사이트 테스트 (draw.io, trello) → [결과] 성공. title 불일치 등 실제 문제 발견
- [에러] codepen.io, canva.com에서 networkidle 타임아웃 → [수정] waitUntil을 domcontentloaded + 3초 대기로 변경
- [시도] 웹 서버 + UI 구현 → [결과] 성공
- [시도] 웹 API 테스트 (curl) → [결과] 성공. JSON 리포트 정상 반환

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네". CLI 출력이 깔끔하고, 웹 UI가 다크 테마로 시각적으로 잘 구성됨
- [평가] 검증 목표 실제 검증? → Yes. 테스트 SPA에서 7개, draw.io에서 2개, trello에서 2개 실제 문제 발견
- [평가] 출력 깔끔한가? → CLI: 심각도별 정렬, 색상 구분, 한국어 해결 방법 제공. 웹 UI: 뱃지, 카드형 레이아웃
- [불만] robots 메타 태그 누락이 모든 사이트에서 "문제"로 표시됨. 실제로는 기본값(index, follow)이므로 문제 아님
- [개선] robots 누락을 이슈에서 제외하도록 analyzer.js 수정

## Phase 4 — 검증
- [체크] CLI로 URL 입력 시 JS 전/후 비교 SEO 리포트 → 통과
- [체크] SPA 사이트 3개 이상에서 인덱싱 문제 발견 데모 → 통과 (테스트SPA: 7개, draw.io: 2개, trello: 2개 = 총 11개)
- [체크] 한국어 평문 진단 ("무엇이 문제이고, 어떻게 고치는가") → 통과
- [체크] sitemap.xml 파싱 다중 페이지 일괄 진단 → 통과 (vite.dev sitemap: 55개 URL 발견, 3개 진단 완료)
- [체크] 웹 UI에서 진단 결과 조회 → 통과 (Playwright 스크린샷 검증, result-card 1개, issue-item 3개 확인)

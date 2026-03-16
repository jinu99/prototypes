# SEO Indie Toolkit

> SPA 크롤러 시뮬레이션으로 검색엔진이 놓치는 SEO 인덱싱 문제를 진단하는 도구

## 실행 방법

```bash
# 의존성 설치
npm install
npx playwright install chromium

# CLI — 단일 페이지 진단
node src/cli.js https://example.com

# CLI — sitemap 기반 일괄 진단
node src/cli.js --sitemap https://example.com/sitemap.xml --limit 5

# 웹 UI 서버
node src/server.js
# → http://localhost:3000 에서 진단 결과 조회

# 데모 (테스트 SPA + 실제 사이트 3개 진단)
node demo.js
```

## 구조

```
seo-indie-toolkit/
├── src/
│   ├── cli.js          # CLI 진입점
│   ├── server.js       # 웹 서버 (API + 정적 파일)
│   ├── crawler.js      # HTTP raw fetch + Playwright 렌더링
│   ├── analyzer.js     # SEO 요소 추출 및 비교
│   ├── reporter.js     # 한국어 리포트 생성 (CLI + JSON)
│   ├── sitemap.js      # sitemap.xml 파서
│   └── browser-env.js  # Playwright 브라우저 환경 설정
├── public/
│   └── index.html      # 웹 UI (단일 HTML + vanilla JS)
├── test-spa/
│   └── index.html      # 테스트용 SPA 페이지
├── demo.js             # 데모 스크립트
├── test-screenshots.js # Playwright 스크린샷 테스트
├── BUILD_LOG.md        # 빌드 일지
├── STATUS.md           # 검증 결과
└── package.json
```

## 원본
prototype-pipeline spec: seo-indie-toolkit

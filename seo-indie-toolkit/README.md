# SEO Indie Toolkit

> SPA 크롤러 시뮬레이션으로 검색엔진이 놓치는 SEO 인덱싱 문제를 진단하는 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          입력 (Input)                           │
│  URL / sitemap.xml ──▶ cli.js 또는 server.js                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      sitemap.js (선택적)                        │
│  sitemap.xml 파싱 ──▶ URL 목록 추출 (sitemap index 재귀 지원)  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     crawler.js (이중 크롤링)                    │
│                                                                 │
│  ┌──────────────────────┐   ┌──────────────────────────────┐   │
│  │  HTTP Raw Fetch      │   │  Playwright Rendering        │   │
│  │  (Googlebot UA)      │   │  (Chromium headless)         │   │
│  │  ─▶ 정적 HTML        │   │  ─▶ JS 실행 후 렌더링 HTML   │   │
│  └──────────┬───────────┘   └──────────────┬───────────────┘   │
│             │         병렬 실행 (Promise.all) │                  │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    analyzer.js (비교 분석)                       │
│                                                                 │
│  extractSeoElements()    extractSeoElements()                   │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ Raw HTML에서     │    │ Rendered HTML에서│                    │
│  │ title, meta,     │    │ title, meta,     │                   │
│  │ OG, JSON-LD,    │    │ OG, JSON-LD,    │                    │
│  │ h1 추출         │    │ h1 추출         │                    │
│  └────────┬────────┘    └────────┬────────┘                    │
│           │                      │                              │
│           └───────┬──────────────┘                              │
│                   ▼                                             │
│           compareSeo()                                          │
│           ─▶ js_dependent / mismatch / missing 판정             │
│           ─▶ severity: high / medium / low 부여                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    reporter.js (리포트 생성)                     │
│                                                                 │
│  ┌─────────────────────┐   ┌─────────────────────────────┐     │
│  │ generateCliReport() │   │ generateJsonReport()        │     │
│  │ ─▶ 터미널 텍스트     │   │ ─▶ JSON (웹 UI용)          │     │
│  │   심각도별 정렬      │   │   issue별 advice 포함       │     │
│  │   한국어 해결 방법   │   │                             │     │
│  └──────────┬──────────┘   └──────────────┬──────────────┘     │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
              ▼                              ▼
┌──────────────────────┐   ┌──────────────────────────────────┐
│  CLI 출력 (터미널)    │   │  웹 UI (localhost:3000)          │
│  단일 URL / 일괄 진단 │   │  public/index.html + REST API   │
│  종합 요약 리포트     │   │  GET /api/analyze?url=...       │
└──────────────────────┘   │  GET /api/sitemap?url=...       │
                           └──────────────────────────────────┘
```

## Demo

### CLI — 단일 페이지 진단

```bash
$ node src/cli.js https://app.diagrams.net

🚀 브라우저를 시작합니다...

🔍 [1/1] 진단 중: https://app.diagrams.net

═══════════════════════════════════════════════════
  SEO 크롤러 시뮬레이션 진단 리포트
  URL: https://app.diagrams.net
═══════════════════════════════════════════════════

발견된 문제: 3개
  🔴 심각: 1개
  🟡 주의: 2개
  🟢 참고: 0개

───────────────────────────────────────────────────
🔴 심각 | JS 의존 | title

  크롤러가 보는 값 (JS 실행 전): (없음)
  실제 렌더링 값 (JS 실행 후):   diagrams.net

  💡 해결 방법:
     제목(title)이 JavaScript에 의존합니다. 검색엔진 크롤러가 JS를
     실행하지 못하면 제목이 표시되지 않습니다. SSR을 적용하거나,
     정적 HTML에 제목을 포함하세요.

───────────────────────────────────────────────────
🟡 주의 | JS 의존 | description

  크롤러가 보는 값 (JS 실행 전): (없음)
  실제 렌더링 값 (JS 실행 후):   Online diagram software

  💡 해결 방법:
     meta description이 JS에 의존합니다. 정적 HTML에 description을
     포함하세요.

═══════════════════════════════════════════════════
```

### CLI — sitemap 기반 일괄 진단

```bash
$ node src/cli.js --sitemap https://example.com/sitemap.xml --limit 3

📡 Sitemap 가져오는 중: https://example.com/sitemap.xml
📋 발견된 URL: 42개
🔢 상위 3개만 진단합니다.
🚀 브라우저를 시작합니다...

🔍 [1/3] 진단 중: https://example.com/
🔍 [2/3] 진단 중: https://example.com/about
🔍 [3/3] 진단 중: https://example.com/pricing

═══════════════════════════════════════════════════
  종합 요약
═══════════════════════════════════════════════════

진단 완료: 3/3개

총 발견된 문제: 5개 (심각: 2개)
```

### 웹 UI

`node src/server.js`로 서버를 시작하면 `http://localhost:3000`에서 웹 인터페이스를 사용할 수 있습니다.

- **GET `/`** — 진단 폼이 포함된 웹 UI 페이지
- **GET `/api/analyze?url=<URL>`** — 단일 URL SEO 진단 (JSON 응답)
- **GET `/api/sitemap?url=<URL>&limit=<N>`** — sitemap 기반 일괄 진단 (JSON 응답)

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

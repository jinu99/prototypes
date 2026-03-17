---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# SEO Indie Toolkit

**SPA 크롤러 시뮬레이션으로 검색엔진이 놓치는 인덱싱 문제를 진단하는 도구**

- 카테고리: Developer Tools / SEO
- 스택: Node.js, Playwright, Cheerio
- 날짜: 2026-03-15

<!--
SPA 프론트엔드가 대세가 되면서, 검색엔진 크롤러가 보는 HTML과 사용자가 보는 HTML이 다른 경우가 많아졌다. 이 프로토타입은 그 차이를 자동으로 잡아내는 도구다. 오늘은 왜 이걸 만들었고, 어떤 결과가 나왔는지 이야기하겠다.
-->

---

## Background

SPA(React, Vue, Angular)가 프론트엔드의 기본이 된 시대.

- 검색엔진 크롤러는 JavaScript를 **제한적으로만** 실행한다
- 서버가 보내는 raw HTML에는 빈 `<div id="root"></div>`만 있고, 실제 콘텐츠는 JS 실행 후에 나타남
- Google은 JS 렌더링을 지원하지만, **지연이 있고 완벽하지 않다**
- 네이버, Bing 등 다른 검색엔진은 JS 렌더링 지원이 더 제한적

결과: 개발자는 자기 사이트가 검색엔진에 어떻게 보이는지 **모르는 채로** 운영한다.

<!--
SPA가 프론트엔드의 기본이 된 지 꽤 됐다. 그런데 검색엔진 크롤러 관점에서 보면, SPA는 근본적으로 문제가 있다. 크롤러가 받는 HTML에는 아무 콘텐츠가 없고, JavaScript를 실행해야 비로소 내용이 나타난다. Google이 JS 렌더링을 지원한다고는 하지만, 지연이 있고 100% 신뢰할 수 없다. 결국 개발자 입장에서는 자기 사이트가 크롤러에게 어떻게 보이는지 확인할 방법이 마땅치 않다.
-->

---

## Pain Point

커뮤니티에서 실제로 반복되는 고통들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/webdev | ⬛⬛⬛ | SEO 도구(Semrush, Ahrefs)가 **$99~139/월**로 비싸고, 인디 개발자에겐 과도하게 복잡 |
| 2 | r/SideProject | ⬛⬛⬛ | SPA가 크롤러에게 **완전히 다른 HTML**을 보여줘서 인덱싱 문제 발생 |
| 3 | GeekNews | ⬛⬛ | Google + 네이버 키워드 순위를 **한 곳에서 추적**하는 도구가 없음 |
| 4 | r/SideProject | ⬛⬛ | 웹사이트 감사 도구가 전문 용어만 뱉어 **비기술자가 실행 불가** |

<!--
Reddit이나 GeekNews에서 이런 얘기가 계속 나온다. SEO 도구가 좋긴 한데 월 100달러 넘게 내야 하고, 인디 개발자에겐 기능이 과도하다. 그리고 더 근본적인 문제는, 기존 도구들이 SPA의 크롤러 관점 렌더링 차이를 제대로 진단하지 못한다는 거다. CLS 점수 0.28이라고 알려줘봤자, 그래서 뭘 어떻게 고치라는 건지 모르겠다는 반응이 대부분이다.
-->

---

## Solution

> **JS 실행 전/후 HTML을 비교해서, 크롤러가 놓치는 SEO 요소를 자동 진단한다**

핵심 접근: **이중 크롤링(Dual Crawling)**

1. **HTTP raw fetch** (Googlebot UA) → 크롤러가 보는 정적 HTML
2. **Playwright headless** 렌더링 → 사용자가 보는 완전한 HTML
3. 두 결과를 **요소 단위로 비교** → JS 의존/불일치/누락 판정

기존 도구와의 차이:
- Semrush/Ahrefs: 점수는 주지만 **SPA 렌더링 차이 미진단**
- Lighthouse: raw 점수만 제공, **한국어 해결 방법 없음**
- 이 도구: **"title이 JS에 의존합니다. SSR을 적용하세요"** 수준의 진단

<!--
접근 방식은 단순하다. 같은 URL을 두 번 가져온다. 한 번은 HTTP로 raw HTML을, 한 번은 Playwright로 JS 실행 후 HTML을. 그리고 이 둘을 SEO 요소 단위로 비교한다. title, meta description, OG 태그, canonical, JSON-LD 같은 것들이 JS 없이도 존재하는지 확인하는 거다. 기존 도구들은 점수를 주지만 SPA 렌더링 차이를 진단하지는 않는다. 이 도구는 그 빈 곳을 노린다.
-->

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      입력 (Input)                           │
│  URL / sitemap.xml ──▶ cli.js 또는 server.js               │
└────────────────────────────┬───────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────┐
│               crawler.js (이중 크롤링)                      │
│  HTTP Raw Fetch ──┐              ┌── Playwright Rendering  │
│  (Googlebot UA)   ├─ Promise.all ┤  (Chromium headless)    │
│  → 정적 HTML      ┘              └→ 렌더링 HTML             │
└────────────────────────────┬───────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────┐
│               analyzer.js (비교 분석)                       │
│  extractSeoElements() × 2 → compareSeo()                   │
│  → js_dependent / mismatch / missing 판정                   │
│  → severity: high / medium / low                            │
└────────────────────────────┬───────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────┐
│               reporter.js (리포트 생성)                     │
│  CLI: 심각도별 정렬 + 한국어 해결 방법                       │
│  JSON: 웹 UI용 구조화 응답 + advice 포함                    │
└────────────────────────────────────────────────────────────┘
```

<!--
구조는 네 개 모듈로 나뉜다. crawler가 같은 URL을 병렬로 두 번 가져오고, analyzer가 Cheerio로 SEO 요소를 추출해서 비교한다. reporter가 결과를 사람이 읽을 수 있는 형태로 만든다. 여기서 핵심은 crawler의 이중 크롤링인데, HTTP raw fetch와 Playwright 렌더링을 Promise.all로 동시에 실행해서 속도를 확보했다. sitemap.js는 sitemap.xml을 파싱해서 URL 목록을 뽑아주는 보조 모듈이다.
-->

---

## Demo

**draw.io (app.diagrams.net) 진단 결과:**

```
발견된 문제: 3개  (🔴 심각: 1개, 🟡 주의: 2개)

🔴 심각 | JS 의존 | title
   크롤러가 보는 값 (JS 실행 전): (없음)
   실제 렌더링 값 (JS 실행 후):   diagrams.net
   💡 제목(title)이 JavaScript에 의존합니다.
      SSR을 적용하거나, 정적 HTML에 제목을 포함하세요.

🟡 주의 | JS 의존 | description
   크롤러가 보는 값 (JS 실행 전): (없음)
   실제 렌더링 값 (JS 실행 후):   Online diagram software
```

**검증 결과:** 3개 사이트(테스트 SPA, draw.io, Trello)에서 **총 11개** 실제 문제 발견

<!--
실제로 draw.io를 진단해보면, title이 JS에 완전히 의존하고 있다는 걸 알 수 있다. 크롤러가 받는 raw HTML에는 title이 비어 있고, JS가 실행된 후에야 "diagrams.net"이 설정된다. 이건 검색 결과에 제목이 안 나올 수도 있다는 의미다. 테스트 SPA에서 7개, draw.io에서 2개, Trello에서 2개, 합쳐서 11개 문제를 찾았다. 기존 SEO 도구에서는 잡아주지 않는 문제들이다.
-->

---

## Key Decisions & Lessons

**1. Cheerio vs jsdom → Cheerio 선택**
HTML 파싱에 jsdom은 과하다. SEO 요소 추출에는 CSS selector만 있으면 충분. Cheerio가 가볍고 빠르다.

**2. networkidle → domcontentloaded + 3초 대기**
codepen.io, canva.com 같은 사이트에서 networkidle 타임아웃 발생. SPA가 SEO 태그를 설정하는 데 3초면 충분하다는 실험적 판단.

**3. robots 누락을 이슈에서 제외**
셀프 크리틱 단계에서 발견 — robots 메타 태그가 없으면 기본값(index, follow)이므로 문제가 아님. 모든 사이트에서 "문제"로 표시되는 false positive를 제거.

| 심의 항목 | 점수 |
|-----------|:----:|
| 문제 진정성 | 3.7 |
| 프로토타입 적합성 | 3.0 |
| 신선도 | 3.7 |
| 학습 가치 | **4.0** |

<!--
기술 판단 몇 가지를 공유하면, 첫째로 HTML 파싱에 jsdom 대신 Cheerio를 골랐다. SEO 요소 추출은 CSS selector면 충분하고, jsdom은 DOM 시뮬레이션까지 하니까 과하다. 둘째로, Playwright의 waitUntil을 networkidle에서 domcontentloaded로 바꿨다. 실제 SPA 사이트들에서 networkidle 타임아웃이 빈번했는데, SEO 태그는 초기 렌더링에서 설정되니까 3초면 충분했다. 셋째로, 셀프 크리틱 과정에서 robots 누락을 false positive로 판정하고 제거했다. 이건 꽤 중요한 판단이었는데, 안 그러면 모든 사이트에서 경고가 뜬다.
-->

---

## Results & Future

### 성과
- [x] CLI로 JS 실행 전/후 비교 SEO 리포트 — **통과**
- [x] 3개 사이트에서 11개 실제 인덱싱 문제 발견 — **통과**
- [x] 한국어 평문 진단 ("무엇이 문제이고, 어떻게 고치는가") — **통과**
- [x] sitemap.xml 파싱 다중 페이지 일괄 진단 — **통과**
- [x] 웹 UI에서 진단 결과 조회 — **통과**

### 한계
- Lighthouse 연동 제외 (선택사항으로 범위 밖)
- 네이버/Google 순위 추적 미구현 (API 키 필요)
- 대량 크롤링 시 Playwright 메모리 부담

### 프로덕트가 되려면
- GitHub Action / CI 통합 → PR마다 SEO 회귀 체크
- 히스토리 저장 (SQLite) → 시간에 따른 SEO 변화 추적
- 네이버 SearchAdvisor 연동 → 한국 시장 차별화

<!--
완료 기준 5개를 전부 통과했다. 솔직히 가장 아쉬운 건 Lighthouse 연동을 못 한 건데, 프로토타입 범위에서는 SPA 크롤러 시뮬레이션에 집중하는 게 맞았다고 본다. 이게 실제 프로덕트가 되려면, GitHub Action으로 CI에 붙여서 PR마다 SEO 회귀를 체크하는 방식이 가장 자연스럽다. 인디 개발자가 매번 CLI를 돌리진 않을 테니까. 그리고 네이버 SearchAdvisor를 연동하면 한국 시장에서 의미 있는 차별점이 생긴다. 결국 이 도구의 가치는 "크롤러가 보는 세계와 사용자가 보는 세계의 차이를 가시화한다"는 데 있다.
-->

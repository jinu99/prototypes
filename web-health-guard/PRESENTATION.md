---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Web Health Guard

**URL 하나로 기술 SEO, AI 크롤러 방어, 팬텀 URL을 한 화면에서 진단하는 웹 도구**

- 카테고리: 웹 개발자 도구 / SEO / 보안
- 스택: Python, FastAPI, httpx, BeautifulSoup, vanilla JS
- 날짜: 2026-03-03

<!--
웹사이트를 운영하다 보면 코드 작성 외에 신경 써야 할 것들이 꽤 많다. SEO는 제대로 되어 있는지, AI 크롤러가 서버 리소스를 갉아먹고 있지는 않은지, Google이 이상한 URL을 인덱싱하고 있지는 않은지. 이 세 가지를 URL 하나 넣으면 한 화면에서 바로 확인할 수 있는 도구를 만들었다.
-->

---

## Background

웹 개발자의 "사이트 건강 관리" 부담이 **세 방향에서 동시에** 증가하고 있다

1. **기술 SEO**: 클라이언트가 SEO를 요구하지만, 기존 도구(Screaming Frog, Lumar)는 SEO 전문가 대상이고 유료($50-500/월). 개발자가 "빠르게 체크"하기엔 과도하다.

2. **AI 크롤러 트래픽**: GPTBot, ClaudeBot, Bytespider 등이 robots.txt를 무시하거나 대량 요청으로 서버를 과부하시키는 새로운 인프라 위협.

3. **팬텀 URL**: Google 크롤러가 페이지 내 일반 텍스트(경로 형태 문자열)를 실제 URL로 오인하여 인덱싱 → 대량 404 에러 → SEO 상태 왜곡.

세 문제 모두 "웹사이트 건강성 유지"라는 동일 워크플로에서 발생하는데, 현재는 각각 별개 도구로 분산 관리해야 한다.

<!--
웹 개발자한테 사이트 관리를 맡기면, 코드만 짜면 되는 게 아니다. SEO 해달라는 요청이 오고, AI 크롤러가 서버를 긁어대고, Google이 이상한 URL을 인덱싱하고 있다. 문제는 이 셋이 결국 같은 워크플로의 서로 다른 단계인데, 도구가 다 따로 있다는 거다. Screaming Frog는 비싸고, Cloudflare는 크롤러만 막아주고, Search Console은 원인을 안 알려준다. 결국 이건 도구 통합 문제다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 세 가지 고통

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/webdev | ★★★ | 클라이언트가 SEO를 요구하지만 키워드 전략·경쟁사 분석은 범위 밖. 기술 SEO조차 체계적으로 점검할 개발자 친화 도구가 없다 |
| 2 | Hacker News | ★★★ | Google이 하이퍼링크가 아닌 일반 텍스트를 URL로 인덱싱 → Search Console에 대량 404 → SEO 상태 왜곡 |
| 3 | r/webdev | ★★★ | LLM 크롤러가 robots.txt 무시하고 대량 요청으로 서버 과부하. 차단 규칙을 직접 작성해야 하는데, 어떤 크롤러가 오는지도 모른다 |

세 signal 모두 최고 등급 — 실제로 개발자들이 겪고 있는 문제다.

<!--
이게 가설이 아니라 실제 커뮤니티에서 계속 나오는 이야기다. Reddit webdev에서는 클라이언트가 SEO 해달라고 하는데 개발자는 키워드 분석 같은 건 할 줄 모른다는 글이 올라오고, HN에서는 Google이 텍스트를 URL로 오인해서 404가 수백 개씩 생긴다는 보고가 나온다. AI 크롤러 트래픽 문제는 말할 것도 없다. 세 가지 다 signal strength 최고 등급이다.
-->

---

## Solution

> SEO 비전문가인 웹 개발자가 URL 하나를 입력하면, 기술 SEO 상태 · AI 크롤러 위협 · 인덱싱 이상을 한 화면에서 파악하고 대응 조치를 바로 알 수 있다

**기존 솔루션과의 차이점:**

| 기존 도구 | 한계 | Web Health Guard |
|-----------|------|------------------|
| Screaming Frog, Lumar | SEO 전문가 대상, 유료 | 개발자 언어로 설명, 무료 |
| Cloudflare AI Bot Mgmt | Cloudflare 종속, 분석 없음 | 크롤러별 차단 현황 + 규칙 자동 생성 |
| Google Search Console | 원인 진단 불가 | 팬텀 URL 원인 탐지 + 대응 가이드 |
| ai.robots.txt (OSS) | 차단 설정만 제공 | 현재 차단 상태 분석 포함 |

핵심: **세 가지를 통합**하되, SEO를 마케팅 용어가 아닌 **기술 용어**(HTTP 상태, DOM 구조)로 설명한다.

<!--
접근법은 단순하다. URL 하나 넣으면 세 가지를 동시에 보여준다. 중요한 건 기존 도구와 뭐가 다르냐인데, 핵심은 두 가지다. 첫째, 세 영역을 한 화면에 통합했다. 둘째, SEO 결과를 마케팅 용어가 아니라 개발자 언어로 설명한다. "메타 디스크립션이 없습니다"가 아니라 "search engine이 auto-generate할 거다"라고 말해준다. 개발자가 뭘 해야 하는지 바로 알 수 있게.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (index.html)                         │
│  URL input → Scan button → fetch(/api/scan) → render dashboard   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ GET /api/scan?url=...
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FastAPI Server (main.py)                        │
│                                                                 │
│  httpx.AsyncClient fetches 3 resources concurrently:             │
│     ┌──────────┐  ┌──────────────┐  ┌──────────────┐           │
│     │ Target Page│  │ /robots.txt  │  │ /sitemap.xml │           │
│     └────┬─────┘  └──────┬───────┘  └──────┬───────┘           │
│          ▼               ▼                  ▼                   │
│   seo_checker      robots_analyzer    phantom_detector          │
│   (14 checks)     (10 AI crawlers)   (sitemap vs text)         │
│          └───────────────┼──────────────────┘                   │
│                          ▼                                      │
│                   JSON Response                                 │
└─────────────────────────────────────────────────────────────────┘
```

- **seo_checker**: pass/fail for 14 checks including title, meta, OG, JSON-LD, viewport
- **robots_analyzer**: block status of 10 AI crawlers + auto-generated robots.txt snippet for unblocked ones
- **phantom_detector**: compares sitemap URLs against path patterns in page text → detects phantom URLs

<!--
구조는 꽤 단순하다. 브라우저에서 URL을 보내면 FastAPI 서버가 세 개의 리소스를 asyncio.gather로 동시에 가져온다. 대상 페이지, robots.txt, sitemap.xml. 그리고 각각을 세 개의 분석 모듈에 넘긴다. seo_checker가 HTML을 파싱해서 14개 항목을 체크하고, robots_analyzer가 robots.txt에서 AI 크롤러 차단 상태를 분석하고, phantom_detector가 사이트맵과 텍스트 패턴을 비교한다. 이걸 JSON으로 합쳐서 프론트엔드 대시보드에 뿌린다.
-->

---

## Demo

**API 응답 예시** (`/api/scan?url=github.com`):

```json
{
  "url": "https://github.com",
  "page_status": 200,
  "seo": [
    {"name": "title", "passed": true, "detail": "\"GitHub\" (6 chars)"},
    {"name": "og:title", "passed": true, "detail": "\"GitHub\""},
    {"name": "structured-data", "passed": false, "detail": "No JSON-LD found"}
  ],
  "robots": {
    "found": true,
    "crawlers": [
      {"name": "GPTBot", "blocked": true, "rule": "User-agent: GPTBot\nDisallow: /"},
      {"name": "ClaudeBot", "blocked": false, "rule": "Not blocked"}
    ],
    "block_snippet": "User-agent: ClaudeBot\nDisallow: /"
  }
}
```

**대시보드 구성**: Summary Bar → SEO Checklist (✓/✗) → AI Crawler Cards → Phantom URL 목록
**응답 시간**: ~74ms (목표 30초 대비 400배 빠름)

<!--
실제로 github.com을 넣어보면, SEO 항목 14개가 pass/fail로 바로 나온다. GitHub은 OG 태그는 잘 되어 있는데 JSON-LD가 없다든지 하는 것들이 보인다. robots.txt 분석에서는 GPTBot은 차단되어 있는데 ClaudeBot은 안 되어 있다는 걸 바로 알 수 있고, 차단 규칙 스니펫도 자동으로 생성해준다. 응답 시간이 74밀리초인데, 목표가 30초였으니 꽤 여유 있다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 선택 | 이유 |
|------|------|------|
| 스택 | FastAPI + httpx + BS4 | async로 3개 리소스 동시 fetch 가능, 경량 |
| 프론트엔드 | 단일 HTML + vanilla JS | spec 제약. 빌드 도구 없이 즉시 실행 |
| DB | 없음 | 일회성 스캔, 상태 저장 불필요 |

### 시행착오

- **SSL 인증서 오류**: `httpx.AsyncClient(verify=False)` — 개발환경 인증서 이슈로 우회
- **innerHTML 보안 경고**: 전체 프론트엔드를 safe DOM methods (`el()` 헬퍼)로 리팩터링
- **팬텀 URL 한계**: 대형 사이트(GitHub, Wikipedia)에서는 0건 — clean text 특성 때문. 단위 테스트로 알고리즘 정상 확인

### 심의 점수
문제 진정성 **4.0**/5 · 프로토타입 적합성 **3.3**/5 · 신선도 **3.0**/5 · 학습 가치 **3.3**/5
반대 의견: "Lighthouse + Clarity 조합으로 대부분 커버됨. 팬텀 URL만 독특하나 단독으로는 깊이 부족" (준혁)

<!--
스택은 spec에서 정해진 부분도 있지만, FastAPI를 고른 건 asyncio.gather로 세 개의 HTTP 요청을 동시에 보낼 수 있어서다. 실제로 응답 시간이 74ms까지 내려간 건 이 판단 덕분이다. 시행착오도 있었는데, innerHTML을 쓰니까 보안 훅에서 경고가 떠서 프론트엔드 전체를 safe DOM methods로 다시 짰다. 솔직히 좀 번거로웠는데, 결과적으로는 맞는 판단이었다. 심의에서 준혁이 Lighthouse로 커버 가능하다고 반대했는데, 일리 있는 지적이다. 다만 세 영역 통합이라는 포인트는 기존 도구에 없다.
-->

---

## Results & Future

### 성과 (5/5 완료 기준 통과)

- ✅ SEO 14개 항목 — pass/fail + 개발자 언어 설명
- ✅ AI 크롤러 10종 차단 분석 + 미차단 시 차단 규칙 자동 생성 (419 chars)
- ✅ 팬텀 URL 후보 + 고아 사이트맵 URL + 대응 가이드 4종 (410, noindex, 301, sitemap 정리)
- ✅ 단일 대시보드, 응답 ~74ms
- ✅ 외부 API 키 없이 동작

### 한계점
- 팬텀 URL이 "clean" 사이트에서는 잘 안 잡힌다 (알고리즘은 정상, 대상 특성 문제)
- SSL verify=False는 프로덕션에서 수정 필요
- Playwright 없이 UI를 직접 눈으로 검증하지 못함

### 프로덕트가 되려면
- 서버 액세스 로그 파싱으로 **실제** AI 크롤러 트래픽 분석 (현재는 robots.txt 기반)
- Google Search Console API 연동 → 실제 인덱싱 데이터 기반 팬텀 URL 탐지
- 지속적 모니터링 + 알림 (현재는 일회성 스캔)
- 히스토리 저장 → 시간별 SEO 상태 변화 추적

<!--
완료 기준 5개를 다 통과했다. 솔직히 아쉬운 건 팬텀 URL인데, 알고리즘 자체는 단위 테스트에서 5개 팬텀 + 3개 고아 URL을 정확히 잡는다. 다만 GitHub이나 Wikipedia 같은 사이트는 텍스트에 raw path를 안 쓰니까 실제 스캔에서는 0건이 나온다. 이건 한계라기보다 대상 특성이다. 이게 실제 프로덕트가 되려면, robots.txt 분석만으로는 부족하고 서버 로그를 직접 파싱해서 실제 크롤러 트래픽을 봐야 한다. 그리고 일회성 스캔이 아니라 지속적 모니터링이 되어야 한다. 그래도 프로토타입으로서 "이 세 가지를 통합하면 개발자한테 유용하다"는 건 검증된 것 같다.
-->

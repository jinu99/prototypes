# Web Health Guard

> URL 하나로 기술 SEO, AI 크롤러 방어, 팬텀 URL을 한 화면에서 진단하는 웹 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (index.html)                     │
│  URL 입력 → Scan 버튼 → fetch(/api/scan) → 대시보드 렌더링     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ GET /api/scan?url=...
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Server (main.py)                     │
│                                                                  │
│  1. URL 정규화 (https:// 보정)                                   │
│  2. httpx.AsyncClient 로 3개 리소스 동시 fetch:                  │
│     ┌──────────┐  ┌──────────────┐  ┌──────────────┐            │
│     │ 대상 페이지│  │ /robots.txt  │  │ /sitemap.xml │            │
│     └────┬─────┘  └──────┬───────┘  └──────┬───────┘            │
│          │               │                  │                    │
│          ▼               ▼                  ▼                    │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────┐          │
│  │ seo_checker  │ │robots_analyzer│ │phantom_detector│          │
│  │              │ │               │ │                │          │
│  │ 14개 항목    │ │ AI 크롤러     │ │ 사이트맵 URL   │          │
│  │ 점검:        │ │ 10종 차단     │ │ vs 텍스트 패턴 │          │
│  │ · title      │ │ 여부 분석     │ │ 비교 → 팬텀    │          │
│  │ · meta desc  │ │               │ │ URL 탐지       │          │
│  │ · canonical  │ │ 차단 안 된    │ │                │          │
│  │ · viewport   │ │ 크롤러용      │ │ 고아 사이트맵  │          │
│  │ · OG tags    │ │ robots.txt    │ │ URL 탐지       │          │
│  │ · JSON-LD    │ │ 스니펫 생성   │ │                │          │
│  │ · h1, lang   │ │               │ │ 조치 가이드    │          │
│  │ · charset    │ │               │ │ 제공           │          │
│  │ · img alt    │ │               │ │                │          │
│  │ · robots meta│ │               │ │                │          │
│  └──────┬───────┘ └───────┬───────┘ └───────┬────────┘          │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                      │
│                    JSON Response                                 │
│         { seo: [...], robots: {...}, phantom: {...} }            │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    단일 대시보드 (vanilla JS)                    │
│                                                                  │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐        │
│  │SEO Pass  │ │SEO Issues │ │AI Crawlers │ │Phantom   │        │
│  │  12/14   │ │    2      │ │ 8 blocked  │ │URLs: 3   │        │
│  └──────────┘ └───────────┘ └────────────┘ └──────────┘        │
│                                                                  │
│  · Technical SEO Checklist (✓/✗ 항목별 상세)                    │
│  · AI Crawler Defense (크롤러별 차단 카드 + 스니펫 복사)        │
│  · Phantom URL Detection (팬텀 목록 + 조치 가이드)              │
└─────────────────────────────────────────────────────────────────┘
```

## Demo

웹 대시보드 기반 도구로, 서버 실행 후 브라우저에서 URL을 입력하면 진단 결과가 한 화면에 표시됩니다.

**서버 실행:**

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

**주요 화면/엔드포인트:**

- **`/`** — 메인 대시보드. URL 입력창과 Scan 버튼이 있는 단일 페이지 UI
- **`/api/scan?url=<target>`** — 스캔 API 엔드포인트. 아래와 같은 JSON 응답 반환:

```json
{
  "url": "https://example.com",
  "page_status": 200,
  "seo": [
    {"name": "title", "passed": true, "detail": "\"Example Domain\" (14 chars)", "category": "meta"},
    {"name": "meta-description", "passed": false, "detail": "No meta description found", "category": "meta"},
    {"name": "og:title", "passed": false, "detail": "No og:title", "category": "og"}
  ],
  "robots": {
    "found": true,
    "crawlers": [
      {"name": "GPTBot", "ua": "GPTBot", "org": "OpenAI", "blocked": true, "rule": "User-agent: GPTBot\nDisallow: /"},
      {"name": "ClaudeBot", "ua": "ClaudeBot", "org": "Anthropic", "blocked": false, "rule": "Not blocked"}
    ],
    "block_snippet": "User-agent: ClaudeBot\nDisallow: /"
  },
  "phantom": {
    "phantoms": [{"url": "https://example.com/internal/admin", "source": "text_pattern", "risk": "Path mentioned in page text but not linked"}],
    "orphan_sitemap_urls": [],
    "sitemap_url_count": 42,
    "linked_url_count": 15,
    "text_path_count": 3
  }
}
```

**대시보드 구성:**

| 섹션 | 설명 |
|---|---|
| Summary Bar | SEO 통과/실패, AI 크롤러 차단 수, 팬텀 URL 수를 한눈에 표시 |
| Technical SEO Checklist | 14개 항목(title, meta, OG, JSON-LD 등)의 ✓/✗ 결과와 상세 설명 |
| AI Crawler Defense | 10종 AI 크롤러(GPTBot, ClaudeBot 등)의 차단 상태 카드 + robots.txt 스니펫 복사 |
| Phantom URL Detection | 텍스트에서 발견된 팬텀 URL, 사이트맵 고아 URL 목록 + 조치 가이드(410, noindex, 301, sitemap 정리) |

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# http://localhost:8000 접속 후 URL 입력
```

## 구조

```
web-health-guard/
├── main.py              # FastAPI 서버 + /api/scan 엔드포인트
├── seo_checker.py       # 기술 SEO 14개 항목 체크 (meta, OG, 구조화 데이터 등)
├── robots_analyzer.py   # robots.txt 파싱 + AI 크롤러 10종 차단 분석
├── phantom_detector.py  # 팬텀 URL 탐지 (사이트맵 vs 텍스트 패턴)
├── static/
│   └── index.html       # 단일 대시보드 (vanilla JS)
├── e2e_test.py          # E2E 검증 스크립트
├── BUILD_LOG.md         # 빌드 일지
├── STATUS.md            # 최종 상태
└── pyproject.toml       # 의존성 (uv)
```

## 원본
prototype-pipeline spec: web-health-guard

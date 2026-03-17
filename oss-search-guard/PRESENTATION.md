---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# OSS Search Guard

**오픈소스 프로젝트의 검색 결과에서 사칭 사이트를 자동 감지하는 CLI 도구**

- 카테고리: 오픈소스 보안 / 메인테이너 도구
- 스택: Python, uv, DuckDuckGo Search, difflib
- 날짜: 2026-03-07

<!--
오늘 소개할 프로토타입은 OSS Search Guard다. 오픈소스 프로젝트 이름을 검색엔진에 치면 가짜 사이트가 공식 페이지보다 위에 뜨는 문제가 있는데, 이걸 자동으로 감지해주는 CLI 도구를 만들었다. 왜 이게 필요한지, 어떻게 동작하는지 얘기해보겠다.
-->

---

## Background

- 오픈소스 프로젝트가 유명해질수록 **사칭 사이트**가 생긴다
- `minimap2.com`, `czkawka.com` 같은 도메인이 공식 GitHub보다 검색 상위에 노출
- Fullstory 보고서에서 **165개 사칭 도메인**이 실증된 실제 위협
- 사용자는 검색 결과 1페이지만 보고 다운로드한다 — 악성코드 유포의 주요 경로

<!--
배경부터 얘기하면, 오픈소스 프로젝트가 어느 정도 인지도가 생기면 프로젝트명으로 도메인을 등록하고 가짜 다운로드 페이지를 만드는 사례가 꽤 많다. 18,000 스타짜리 프로젝트에서도 발생한다. 사람으로 치면 유명인 사칭 계정 같은 건데, 검색엔진이 이걸 구별 못 하니까 사용자가 그냥 첫 번째 링크 눌러서 악성코드를 받게 되는 거다. 결국 이건 검색 결과의 신뢰성 문제다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 신호들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/opensource | ⬤⬤⬤⬤ | 눈에 안 띄는 핵심 라이브러리의 지속가능한 펀딩 부족 |
| 2 | Hacker News | ⬤⬤⬤ | AI 생성 PR이 대량으로 쏟아져 리뷰 부담이 직접 수정보다 크다 |
| 3 | GeekNews | ⬤⬤⬤ | **프로젝트명 검색 시 가짜 웹사이트가 공식 사이트보다 상위 노출** |

메인테이너가 수동으로 검색 결과를 모니터링하기엔 한계가 있다.

<!--
커뮤니티에서 이런 얘기가 계속 나온다. 레딧, 해커뉴스, 긱뉴스 세 곳에서 비슷한 신호가 잡히는데, 그중 우리가 주목한 건 3번이다. 프로젝트명을 검색했을 때 가짜 사이트가 상위에 뜨는 문제. 메인테이너 입장에서는 코드 유지보수만 해도 바쁜데, 검색 결과까지 모니터링하라는 건 현실적으로 어렵다. 결국 자동화가 필요한 영역이다.
-->

---

## Solution

> **GitHub 레포 URL 하나로 검색 결과의 사칭 위협을 자동 진단**

### 기존 도구와의 차이

| 도구 | 접근 방식 | 한계 |
|------|----------|------|
| **openSquat** | 신규 도메인 등록 감시 | 이미 존재하는 사칭 사이트 감지 불가 |
| **Vouch** | 신뢰 네트워크 기반 PR 필터 | 검색 결과 모니터링 미지원 |
| **OSS Search Guard** | **검색 결과 기반 사칭 감지** | 검색엔진 의존 |

핵심 아이디어: "메인테이너가 내 프로젝트명을 검색하면 사용자가 뭘 보는가?"를 자동으로 답하는 도구

<!--
기존에 openSquat이라는 도구가 있긴 한데, 이건 새로 등록되는 도메인을 감시하는 거다. 이미 존재하는 가짜 사이트가 검색 상위에 뜨는 건 잡지 못한다. 우리 접근은 다르다. 실제로 검색엔진에 쿼리를 날려서 사용자가 보는 결과를 그대로 분석한다. 관점의 차이인데, 도메인 등록이 아니라 검색 결과라는 사용자 접점에서 문제를 본 거다.
-->

---

## Architecture

```
┌─────────────────────┐
│   CLI (cli.py)      │
└────────┬────────────┘
         │ GitHub repo URL
         ▼
┌─────────────────────┐     ┌──────────────────────┐
│  GitHub Parser      │────▶│  GitHub API          │
│  (github_parser.py) │◀────│  (public REST API)   │
│  · URL 파싱          │     └──────────────────────┘
│  · 공식 도메인 추출    │
└────────┬────────────┘
         │ project_info + official_domains
         ▼
┌─────────────────────┐     ┌──────────────────────┐
│  Searcher           │────▶│  DuckDuckGo          │
│  (searcher.py)      │◀────│  (검색 엔진)          │
│  · 3종 쿼리 검색      │     └──────────────────────┘
│  · 중복 제거          │
└────────┬────────────┘
         │ filtered results[]
         ▼
┌─────────────────────┐
│  Analyzer           │  difflib 유사도 + 휴리스틱 점수
│  (analyzer.py)      │  typosquatting / 의심 TLD / 키워드
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Reporter           │  DANGER / WARNING / SAFE
│  (reporter.py)      │  ANSI 컬러 CLI 리포트
└─────────────────────┘
```

<!--
구조는 네 단계로 나뉜다. 먼저 GitHub API에서 프로젝트의 공식 도메인 목록을 뽑고, DuckDuckGo에 세 가지 쿼리를 날린다. 프로젝트명, 프로젝트명 download, 프로젝트명 official site. 이렇게 수집한 검색 결과를 analyzer가 휴리스틱으로 분석한다. 도메인이 프로젝트명과 일치하는지, typosquatting인지, TLD가 의심스러운지. 마지막으로 reporter가 DANGER, WARNING, SAFE 세 단계로 리포트를 출력한다.
-->

---

## Demo

```
$ uv run oss-search-guard https://github.com/lh3/minimap2

[1/3] Parsing GitHub repository...
  Project: minimap2  |  Homepage: https://lh3.github.io/minimap2/

[2/3] Searching DuckDuckGo...
  Collected 42 unique results → Relevant: 18

[3/3] Analyzing search results...

══════════════════════════════════════════════════
  Overall Threat Level: DANGER
  Summary: 14 safe / 3 warning / 1 danger

  --- DANGEROUS RESULTS ---
    [DANGER] minimap2.download (score: 70)
      > Domain exactly matches project name — likely impersonation
      > Suspicious TLD: .download

  --- SUSPICIOUS RESULTS ---
    [WARNING] minimap2-tool.xyz (score: 35)
      > Domain contains project name
      > Suspicious TLD: .xyz
══════════════════════════════════════════════════
```

<!--
실제 실행 결과를 보면, minimap2라는 바이오인포매틱스 도구를 넣었을 때 minimap2.download라는 도메인을 DANGER로 잡아낸다. 도메인이 프로젝트명과 정확히 일치하고, TLD가 .download라는 두 가지 근거로 70점을 매긴 거다. czkawka, nicotine-plus도 마찬가지로 사칭 사이트를 정확히 감지했다. 솔직히 이 정도면 꽤 쓸만하다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 선택 | 이유 |
|------|------|------|
| 검색 엔진 | DuckDuckGo (ddgs) | API 키 없이 무료 사용, 초기에 duckduckgo-search 실패 → ddgs로 교체 |
| 유사도 분석 | difflib.SequenceMatcher | 외부 의존성 없이 typosquatting 감지, 충분한 정확도 |
| 점수 체계 | 가중 휴리스틱 | ML 모델 대신 해석 가능한 규칙 기반 — "왜 위험한지" 설명 가능 |

### 시행착오
- 도메인 정확 일치 시 초기 25점 → **50점으로 상향** (DANGER 기준 미달 해결)
- 다운로드 애그리게이터(uptodown 등) **false positive** → 별도 화이트리스트로 분리

### 심의 점수
- 문제 진정성: **4.7/5** | 프로토타입 적합성: **3.7/5** | 신선도: **3.7/5**

<!--
기술 판단 몇 가지를 짚어보면, 검색 엔진은 DuckDuckGo를 골랐다. API 키 없이 바로 쓸 수 있어서. 근데 초기에 duckduckgo-search 패키지가 ddgs로 리네임된 걸 몰라서 삽질했다. 유사도 분석은 표준 라이브러리 difflib로 충분했고, 점수 체계는 ML 대신 규칙 기반을 선택했다. 이유는 간단한데, "이 도메인이 왜 위험한가"를 설명할 수 있어야 메인테이너가 신뢰하기 때문이다. 블랙박스 모델이 "위험하다"고만 하면 아무도 안 믿는다.
-->

---

## Results & Future

### 성과 (6/6 통과)
- ✅ GitHub URL → 프로젝트명 + 공식 도메인 자동 추출
- ✅ DuckDuckGo 검색 40~60개 수집 → 관련성 필터링
- ✅ 의심 도메인 유사도 점수 + 판별 근거 출력
- ✅ minimap2, czkawka, nicotine-plus 사칭 사이트 정확 감지
- ✅ DANGER / WARNING / SAFE 3단계 컬러 리포트

### 한계
- DuckDuckGo 검색 결과 ≠ Google 검색 결과 (사용자 대부분은 Google)
- 1회성 스캔 — 지속적 모니터링 미지원
- 휴리스틱 기반이라 새로운 패턴의 사칭은 놓칠 수 있음

### 프로덕트가 되려면
- Google Custom Search API 또는 SerpAPI 연동
- 크론잡 기반 정기 스캔 + 변화 감지 알림
- GitHub Action으로 배포 (메인테이너가 레포에 붙이기만 하면 동작)

<!--
완료 기준 6개 모두 통과했다. 솔직히 한계도 있는데, 가장 아쉬운 건 DuckDuckGo 결과가 Google이랑 다르다는 점이다. 실제 사용자 대부분은 Google을 쓰니까. 그리고 1회성 스캔이라 지속적 모니터링이 안 된다. 이걸 프로덕트로 만들려면 Google 검색 API 연동하고, GitHub Action으로 패키징해서 메인테이너가 레포에 붙이기만 하면 주기적으로 스캔되게 만들어야 한다. 결국 이 프로토타입이 검증한 건 "검색 결과 기반 사칭 감지가 가능한가"인데, 답은 가능하다는 거다.
-->

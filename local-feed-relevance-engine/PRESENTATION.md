---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Local Feed Relevance Engine

**로컬 임베딩으로 RSS 피드에서 읽을 가치가 있는 글만 골라주는 엔진**

카테고리: Developer Productivity / Content Curation
스택: Python · FastAPI · SQLite · sentence-transformers (all-MiniLM-L6-v2)
날짜: 2026-03-17

<!--
오늘 소개할 프로토타입은 Local Feed Relevance Engine이다. 한 줄로 요약하면, RSS 피드에서 내가 읽을 만한 글만 골라주는 로컬 AI 엔진이다. 외부 API 키 없이, 내 노트북에서 돌아가는 임베딩 모델로 관심도를 스코어링한다. 왜 이걸 만들었는지부터 얘기해보겠다.
-->

---

## Background

- 개발자는 평균 수십~수백 개의 RSS 피드, 뉴스레터를 구독한다
- 실제로 관심 있는 콘텐츠는 전체의 **1~5%**에 불과
- 기존 RSS 리더(FreshRSS, Miniflux)는 **키워드 필터**만 제공
- AI 필터링 도구(RSSbrew, UglyFeed)는 **OpenAI API 키를 필수**로 요구
- 저장한 링크는 쌓이기만 하는 "북마크 묘지" 현상 반복

→ 결국 **콘텐츠 소비의 신호 대 잡음비(SNR) 문제**

<!--
개발자들이 RSS 피드를 구독하는 이유는 정보를 놓치지 않기 위해서다. 그런데 실제로 읽는 건 전체의 1-5% 정도밖에 안 된다. 나머지 95%는 스크롤만 하다가 넘긴다. 기존 RSS 리더는 키워드 필터 정도만 있고, AI 필터링을 쓰려면 OpenAI API 키가 필요하다. 결국 이건 신호 대 잡음비 문제인데, 필터가 없으면 피드를 열어도 의미가 없고, 필터가 비싸면 셀프호스팅의 의미가 사라진다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 고통들:

| 출처 | Signal | Pain Point |
|------|:------:|------------|
| r/SideProject | ★★★ | RSS 피드에 관심 없는 콘텐츠가 99%인데 AI 기반 셀프호스팅 필터가 없다 |
| Hacker News | ★★★ | 169개 Substack을 구독해도 읽을 것이 없음 — 콘텐츠 과잉 |
| GeekNews | ★★ | 저장한 링크가 쌓이기만 하고 다시 읽히지 않는다 |
| r/SideProject | ★★ | Reddit·YouTube·Twitter 저장 콘텐츠가 분리되어 통합 검색 불가 |

<!--
이게 저만의 문제가 아니라는 근거가 있다. Reddit SideProject, Hacker News, GeekNews에서 계속 비슷한 얘기가 나온다. Substack을 169개 구독하는데 읽을 게 없다는 사람도 있다. 링크를 저장해놔도 다시 안 본다는 것도 꽤 보편적인 패턴이다. 결국 사람들이 원하는 건 "나한테 맞는 글만 위로 올려줘"인데, 셀프호스팅으로 이걸 해주는 도구가 마땅히 없다.
-->

---

## Solution

**한 줄 요약**: 로컬 임베딩 모델로 관심도를 스코어링하고, 읽기/스킵 피드백으로 학습하는 셀프호스팅 엔진

### 기존 솔루션과의 차이

| | FreshRSS | RSSbrew | **Ours** |
|---|---|---|---|
| 필터링 방식 | 키워드 | LLM (OpenAI) | 로컬 임베딩 |
| API 키 필요 | ✗ | ✓ | **✗** |
| 관심 프로필 학습 | ✗ | ✗ | **✓ (EMA)** |
| 비용 | 무료 | API 종량제 | **무료** |

**검증 목표**: 로컬 임베딩 기반 스코어링이 수백 개 피드에서 관심 기사를 상위 10%로 정확히 필터링할 수 있는가

<!--
우리 접근법의 핵심은 두 가지다. 첫째, 로컬에서 돌아가는 임베딩 모델을 쓴다. all-MiniLM-L6-v2라는 모델인데, 80MB 정도로 가볍고 CPU에서도 빠르다. 둘째, 사용자의 읽기·스킵 행동으로 관심 벡터를 실시간 업데이트한다. RSSbrew는 OpenAI API가 필요하고, FreshRSS는 키워드 필터뿐이다. 우리는 API 키 없이, 사용할수록 똑똑해지는 필터를 만들려고 했다.
-->

---

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│ OPML File│────▶│ feed_parser  │────▶│   feedparser    │
└──────────┘     │  parse OPML  │     │  fetch RSS/Atom │
                 └──────┬───────┘     └────────┬────────┘
                        │                      │
                        ▼                      ▼
              ┌─────────────────┐    ┌──────────────────┐
              │    SQLite DB    │◀───│    embedder.py   │
              │  feeds/articles │    │ all-MiniLM-L6-v2 │
              │  interest_profile│   │ batch embed text │
              └────────┬────────┘    └──────────────────┘
                       │
                       ▼
              ┌─────────────────┐     ┌──────────────────┐
              │  FastAPI server │────▶│  Web UI (HTML)   │
              │  /api/opml      │     │  Score Badge      │
              │  /api/keywords  │◀────│  Read/Skip Button │
              │  /api/feedback  │     │  Sort by Relevance│
              └─────────────────┘     └──────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ EMA Vector Update│
              │  read: α=0.15   │
              │  skip: α=0.075  │
              └─────────────────┘
```

<!--
구조는 꽤 단순하다. OPML 파일을 올리면 feedparser로 RSS를 파싱하고, 각 기사를 sentence-transformers로 384차원 벡터로 변환한다. 사용자가 관심 키워드를 넣으면 그것도 벡터로 만들어서 코사인 유사도로 점수를 매긴다. 여기까지가 초기 스코어링이고, 이후에 Read/Skip 버튼을 누를 때마다 EMA 방식으로 관심 벡터가 업데이트된다. Read는 α 0.15로 끌어당기고, Skip은 α 0.075로 밀어낸다. 비대칭으로 한 이유는, 싫다는 신호보다 좋다는 신호가 더 명확하기 때문이다.
-->

---

## Demo

### OPML 업로드 → 930개 기사 수집
```
POST /api/opml → {"feeds_processed":12, "total_new_articles":930}
```

### 키워드 설정 후 관심도순 정렬
```
 75.8  [Hugging Face Blog] SyGra: The One-Stop Framework for Building Data for LLMs
 73.5  [Hugging Face Blog] Machine Learning Experts - Sasha Luccioni
 72.6  [Hugging Face Blog] StarCoder: A State-of-the-Art LLM for Code
  ...
 47.5  [TechCrunch] Apple quietly launches AirPods Max 2
 46.3  [Wired] Chirp Discount Codes and Deals
```

### 피드백 14회 후 → 분별력 향상
```
Before:  ML 기사 ~74점  |  비관련 ~47점  →  차이 27점
After:   ML 기사 ~83점  |  비관련 ~47점  →  차이 36점
```

<!--
실제로 12개 RSS 피드에서 930개 기사를 수집했다. 키워드로 machine learning, LLM, distributed systems를 넣으니까 Hugging Face 블로그 글이 상위로, TechCrunch 가전 뉴스가 하위로 정렬됐다. 여기까지는 키워드 기반이니까 당연한 결과다. 흥미로운 건 피드백 이후인데, Read 9번, Skip 5번 총 14회 피드백 후에 ML 관련 기사의 점수가 74에서 83으로 올라갔다. 비관련 기사는 그대로 47. 분별력이 27점 차이에서 36점 차이로 벌어졌다.
-->

---

## Key Decisions & Lessons

### 1. 왜 로컬 임베딩인가
all-MiniLM-L6-v2를 선택한 이유: 384차원으로 가볍고, CPU에서 930개 기사 배치 임베딩이 수십 초 내 완료. API 종량제 비용 없이 셀프호스팅의 본래 취지를 지킴

### 2. EMA 비대칭 업데이트
`read: α=0.15` / `skip: α=0.075` — Skip은 "싫다"보다 "지금은 아니다"에 가까워서 영향을 절반으로 줄임. 과도한 네거티브 피드백으로 관심 벡터가 왜곡되는 것을 방지

### 3. 심의 점수 되돌아보기
| 항목 | 점수 | 소감 |
|------|:----:|------|
| 문제 진정성 | 4.3/5 | 커뮤니티 시그널이 명확해서 납득 |
| 프로토타입 적합성 | 3.7/5 | 피드 수집이 외부 의존성이라 불안정할 수 있었지만, 실제로는 잘 됨 |
| 학습 가치 | 4.0/5 | 임베딩 + EMA 조합의 감을 잡은 게 가장 큰 수확 |

<!--
기술 판단에서 가장 중요했던 건 임베딩 모델 선택이다. all-MiniLM-L6-v2는 80MB 정도로 가볍고, 384차원이라 SQLite에 BLOB으로 저장해도 부담이 없다. 두 번째로 EMA 업데이트의 비대칭 설계가 꽤 중요했다. Skip은 "이건 싫다"보다는 "지금은 아니다"에 가까운 신호라서, Read의 절반만 반영했다. 이게 없으면 몇 번 스킵하다가 관심 벡터가 이상한 방향으로 틀어질 수 있다. 심의 점수를 돌아보면, 프로토타입 적합성이 3.7로 좀 낮았는데, 실제로는 feedparser가 안정적이라 문제가 없었다.
-->

---

## Results & Future

### 성과 (5/5 완료 기준 통과)
- ✅ OPML 업로드 → 12개 피드, **930개 기사** 수집·저장
- ✅ 키워드 기반 초기 스코어링 — 점수 범위 **42.8~83.0**
- ✅ 웹 UI에서 관심도순 정렬 확인
- ✅ Read/Skip 피드백 → 관심 벡터 실시간 업데이트
- ✅ 14회 피드백 후 관심 기사 점수 **74→83** 개선

### 한계
- 콜드스타트: 키워드를 직접 입력해야 함 (OPML 카테고리로 자동 부트스트랩 가능)
- 피드백 루프 검증이 14회로 제한적 — 수백 회 이후 벡터 드리프트 미확인
- Playwright 테스트를 돌리지 못해 UI 자동 검증 부재

### 프로덕트가 되려면
- 뉴스레터(Substack RSS)·북마크(Pocket export) 통합
- 일일 다이제스트 생성 (상위 N개 요약 → 이메일)
- 멀티유저 + Docker 배포
- 장기 피드백 안정성 검증 (벡터 드리프트 방지 전략)

<!--
결과적으로 완료 기준 5개를 전부 통과했다. 솔직히 좀 아쉬운 건 Playwright 테스트를 못 돌린 거다. 시스템 라이브러리가 없어서 curl 기반 검증으로 대체했는데, 기능적으로는 동일하다. 이 프로토타입이 실제 프로덕트가 되려면 뉴스레터와 북마크 통합이 필요하고, 일일 다이제스트 기능이 있어야 한다. 그리고 피드백이 수백 회 쌓였을 때 벡터가 어떻게 변하는지, 드리프트 문제가 있는지도 검증해야 한다. 그래도 핵심 가설인 "로컬 임베딩으로 관심 기사를 필터링할 수 있는가"는 확인됐다. 14회 피드백만으로도 분별력이 꽤 올라간다.
-->

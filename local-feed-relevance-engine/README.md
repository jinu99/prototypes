# Local Feed Relevance Engine

> 로컬 임베딩(all-MiniLM-L6-v2)으로 RSS 피드 기사의 관심도를 스코어링하고, 읽기/스킵 피드백으로 개인화하는 엔진

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
              │  interest_profile│    │ batch embed text │
              └────────┬────────┘    └──────────────────┘
                       │
                       ▼
              ┌─────────────────┐     ┌──────────────────┐
              │  FastAPI server │────▶│  Web UI (HTML)   │
              │  /api/opml      │     │  스코어 뱃지      │
              │  /api/keywords  │◀────│  Read/Skip 버튼   │
              │  /api/feedback  │     │  관심도순 정렬     │
              └─────────────────┘     └──────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  EMA 벡터 업데이트│
              │  read: α=0.15   │
              │  skip: α=0.075  │
              └─────────────────┘
```

## Demo

### 1. OPML 업로드 → 930개 기사 수집
```bash
$ curl -X POST http://127.0.0.1:8000/api/opml -F "file=@sample.opml"
{"feeds_processed":12,"total_new_articles":930}
```

### 2. 키워드 설정 → 스코어링
```bash
$ curl -X POST http://127.0.0.1:8000/api/keywords \
  -H "Content-Type: application/json" \
  -d '{"keywords":["machine learning","LLM","distributed systems"]}'
{"keywords":["machine learning","LLM","distributed systems"],"articles_scored":930}
```

### 3. 관심도순 상위 기사
```
 75.8  [Hugging Face Blog] SyGra: The One-Stop Framework for Building Data for LLMs
 73.5  [Hugging Face Blog] Machine Learning Experts - Sasha Luccioni
 73.4  [Hugging Face Blog] Machine Learning Experts - Margaret Mitchell
 72.6  [Hugging Face Blog] StarCoder: A State-of-the-Art LLM for Code
  ...
 47.5  [TechCrunch] Apple quietly launches AirPods Max 2
 46.3  [Wired] Chirp Discount Codes and Deals
```

### 4. 피드백 14회 후 → 점수 개선
```
Before: ML articles ~74, Non-ML ~47
After:  ML articles ~83, Non-ML ~47 → 관심 기사 분별력 향상
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 서버 실행
uv run python server.py

# http://127.0.0.1:8000 접속
```

## 구조

```
local-feed-relevance-engine/
├── server.py          # FastAPI 서버 (6 endpoints)
├── database.py        # SQLite 스키마 및 CRUD
├── embedder.py        # sentence-transformers 래핑, 스코어링, EMA
├── feed_parser.py     # OPML 파싱, RSS 수집
├── static/
│   └── index.html     # 웹 UI (다크 테마, vanilla JS)
├── sample.opml        # 테스트용 12개 피드
├── test_e2e.py        # Playwright e2e 테스트
├── BUILD_LOG.md       # 빌드 일지
├── STATUS.md          # 완료 상태
└── pyproject.toml     # uv 프로젝트 설정
```

## 원본
prototype-pipeline spec: local-feed-relevance-engine

# Community Keyword Monitor

> 멀티플랫폼 커뮤니티(Reddit, RSS)에서 키워드를 모니터링하고 통합 타임라인으로 확인하는 대시보드

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Dashboard)                      │
│                     static/index.html (vanilla JS)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server (server.py)                    │
│                                                                 │
│  GET /api/matches ─── 타임라인 조회 (필터: source, keyword, …)  │
│  POST /api/collect/* ─ 수집 트리거                              │
│  GET/POST/DELETE /api/config/* ─ 설정 관리                      │
└────────┬───────────────────┬───────────────────┬────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌────────────────┐ ┌────────────────┐ ┌──────────────────────────┐
│ Reddit         │ │ RSS            │ │ SQLite DB (monitor.db)   │
│ Collector      │ │ Collector      │ │                          │
│ (mock 데이터)  │ │ (feedparser)   │ │ ┌──────────┐ ┌────────┐ │
│                │ │                │ │ │ matches  │ │ config │ │
│ reddit_        │ │ rss_           │ │ └──────────┘ └────────┘ │
│ collector.py   │ │ collector.py   │ │        db.py             │
└───────┬────────┘ └───────┬────────┘ └──────────────────────────┘
        │                  │                     ▲
        │                  │                     │
        │    ┌─────────────┘                     │
        │    │    insert_match()                  │
        │    │    get_config()                    │
        └────┴───────────────────────────────────┘

데이터 흐름:
  1. 사용자가 대시보드에서 "수집" 버튼 클릭 → POST /api/collect/all
  2. 서버가 Reddit Collector + RSS Collector 순차 호출
  3. 각 Collector는 config 테이블에서 키워드/소스 목록 조회
  4. 외부 소스(Reddit mock / RSS feed)에서 데이터 수집
  5. 키워드 매칭 후 matches 테이블에 저장 (중복 무시)
  6. 대시보드가 GET /api/matches로 타임라인 렌더링
```

## Demo

### 서버 실행

```bash
$ uv run uvicorn server:app --host 127.0.0.1 --port 8765
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8765
```

### 대시보드 (웹 UI)

브라우저에서 `http://127.0.0.1:8765` 접속 시 통합 타임라인 대시보드가 표시됩니다:

- **타임라인 뷰**: Reddit/RSS에서 수집된 키워드 매칭 결과를 시간순으로 표시
- **필터링**: source 유형(reddit/rss), 키워드, 최소 score로 필터 가능
- **수집 트리거**: 버튼 클릭으로 Reddit + RSS 데이터 즉시 수집
- **설정 관리**: 모니터링할 키워드, subreddit, RSS feed URL 추가/삭제

### API 사용 예시

```bash
# 전체 수집 트리거
$ curl -X POST http://127.0.0.1:8765/api/collect/all
{"reddit": {"collected": 12, "source": "reddit (mock)"},
 "rss":    {"collected": 5,  "source": "rss"}}

# 타임라인 조회 (python 키워드, score 10 이상)
$ curl "http://127.0.0.1:8765/api/matches?keyword=python&min_score=10"
[{"id": 1, "source_type": "reddit", "source_name": "r/python",
  "title": "Just released my first Python package — feedback welcome!",
  "url": "https://reddit.com/r/python/comments/...",
  "keyword": "python", "score": 342, ...}, ...]

# 모니터링 키워드 추가
$ curl -X POST "http://127.0.0.1:8765/api/config/keyword?value=rust"
{"status": "added", "key": "keyword", "value": "rust"}

# 현재 설정 조회
$ curl http://127.0.0.1:8765/api/config
{"keywords": ["python", "fastapi", "machine learning", "rust"],
 "subreddits": ["python", "programming", "machinelearning"],
 "rss_feeds": ["https://hnrss.org/newest?q=python", ...]}
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 서버 실행
uv run uvicorn server:app --host 127.0.0.1 --port 8765

# 브라우저에서 http://127.0.0.1:8765 접속
```

## 구조

```
community-keyword-monitor/
├── server.py              # FastAPI 서버 (API + 정적 파일 서빙)
├── db.py                  # SQLite DB 레이어 (스키마, CRUD)
├── reddit_collector.py    # Reddit 키워드 수집 (mock/stub)
├── rss_collector.py       # RSS 피드 키워드 수집 (실제 파싱)
├── static/
│   └── index.html         # 대시보드 UI (vanilla JS)
├── test_browser.py        # Playwright 브라우저 테스트
├── BUILD_LOG.md           # 빌드 일지
├── STATUS.md              # 프로토타입 상태
└── pyproject.toml         # 의존성 관리
```

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 대시보드 |
| GET | `/api/matches` | 타임라인 조회 (source, min_score, keyword, limit) |
| POST | `/api/collect/all` | Reddit + RSS 수집 트리거 |
| POST | `/api/collect/reddit` | Reddit만 수집 |
| POST | `/api/collect/rss` | RSS만 수집 |
| GET | `/api/config` | 설정 조회 |
| POST | `/api/config/{key}?value=...` | 설정 추가 |
| DELETE | `/api/config/{key}?value=...` | 설정 제거 |

## 원본
prototype-pipeline spec: community-keyword-monitor

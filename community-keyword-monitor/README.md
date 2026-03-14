# Community Keyword Monitor

> 멀티플랫폼 커뮤니티(Reddit, RSS)에서 키워드를 모니터링하고 통합 타임라인으로 확인하는 대시보드

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

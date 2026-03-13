# Web Health Guard

> URL 하나로 기술 SEO, AI 크롤러 방어, 팬텀 URL을 한 화면에서 진단하는 웹 도구

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

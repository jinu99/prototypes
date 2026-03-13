# LLM Context Debugger

> OpenAI Chat Completions API 프록시로 컨텍스트 윈도우의 토큰 구성을 실시간 분석·시각화

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행 (mock 모드 — API 키 불필요)
LLM_DEBUG_MODE=MOCK uv run python proxy.py

# 실행 (real 모드 — 실제 OpenAI API로 전달)
uv run python proxy.py
```

서버 시작 후 http://localhost:8088 에서 대시보드 확인.

### 사용법

1. OpenAI 클라이언트의 `base_url`을 `http://localhost:8088/v1`로 변경
2. 평소처럼 API 호출 → 프록시가 자동으로 인터셉트·분석
3. 대시보드에서 컴포넌트별 토큰 비율, diff, 경고 확인

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8088/v1")
```

또는 "Load Demo" 버튼으로 샘플 데이터 확인.

## 구조

```
├── proxy.py           # FastAPI 프록시 서버 (메인 엔트리포인트)
├── token_counter.py   # tiktoken 기반 토큰 카운팅
├── store.py           # 인메모리 호출 기록 저장소 + diff 계산
├── dashboard.html     # 단일 HTML 대시보드 (vanilla JS)
├── test_dashboard.py  # Playwright 테스트 스크립트
├── BUILD_LOG.md       # 빌드 일지
└── STATUS.md          # 완료 상태
```

## 원본
prototype-pipeline spec: llm-context-debugger

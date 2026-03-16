# LLM Context Debugger

> OpenAI Chat Completions API 프록시로 컨텍스트 윈도우의 토큰 구성을 실시간 분석·시각화

## Architecture

```
┌─────────────────┐       ┌──────────────────────────────────────────────────┐
│  OpenAI Client  │       │           FastAPI Proxy (proxy.py:8088)          │
│                 │       │                                                  │
│  base_url =     │  POST │  /v1/chat/completions                           │
│  localhost:8088 ├──────▶│  ┌────────────────────┐  ┌───────────────────┐  │
│                 │       │  │  Token Analyzer     │  │  In-Memory Store  │  │
└─────────────────┘       │  │  (token_counter.py) │  │  (store.py)       │  │
                          │  │                     │  │                   │  │
                          │  │  tiktoken 기반으로   │─▶│  CallRecord 저장   │  │
                          │  │  메시지별 토큰 분해  │  │  + diff 계산       │  │
                          │  │                     │  │                   │  │
                          │  │  컴포넌트 분류:      │  └────────┬──────────┘  │
                          │  │  system / user /    │           │             │
                          │  │  assistant / tool / │           │             │
                          │  │  tools_definition   │  GET /api/calls         │
                          │  └────────────────────┘  GET /api/diff/{a}/{b}   │
                          │                                    │             │
                          └──────────────────────┬─────────────┼─────────────┘
                                                 │             │
                                    Forward ─────┘             │
                                    (real 모드)                │
                                                 │             ▼
                          ┌──────────────────┐   │  ┌──────────────────────┐
                          │  OpenAI API      │◀──┘  │  Dashboard           │
                          │  (upstream)      │      │  (dashboard.html)    │
                          └──────────────────┘      │                      │
                                                    │  • 토큰 바 차트       │
                                                    │  • Treemap 시각화     │
                                                    │  • 메시지별 breakdown  │
                                                    │  • 호출 간 diff 비교   │
                                                    │  • 경고 표시 (>50%)    │
                                                    └──────────────────────┘
```

**데이터 흐름:**
1. OpenAI 클라이언트가 `localhost:8088/v1`로 요청 전송
2. `token_counter.py`가 tiktoken(cl100k_base)으로 메시지별 토큰 수를 계산하고 컴포넌트별로 분류
3. `store.py`가 분석 결과를 인메모리 `CallRecord`로 저장하고 호출 간 diff를 계산
4. Mock 모드면 즉시 응답, real 모드면 원본 OpenAI API로 포워딩
5. 대시보드(`localhost:8088`)가 2초 간격으로 `/api/calls`를 폴링하여 시각화

## Demo

### 서버 실행

```bash
# Mock 모드로 실행 (API 키 불필요)
$ LLM_DEBUG_MODE=MOCK uv run python proxy.py

INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8088
```

### API 호출 인터셉트

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8088/v1", api_key="mock")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
)
```

프록시 콘솔 출력:

```
============================================================
[Call #1] model=gpt-4 total=24 tokens
  system: 13 (54.2%)
  user: 8 (33.3%)
  ⚠ WARNING: system uses 54.2% of context (13/24 tokens)
============================================================
```

### 대시보드 (http://localhost:8088)

- **Overview 탭**: 컴포넌트별 토큰 분포를 바 차트와 treemap으로 시각화
- **Messages 탭**: 각 메시지의 role, 토큰 수, 내용 미리보기를 테이블로 표시
- **Diff 탭**: 두 API 호출 간 컨텍스트 변화를 비교 (추가/삭제된 메시지, 컴포넌트별 토큰 변화량)
- **Load Demo 버튼**: 3개의 샘플 호출 데이터를 자동 주입하여 대시보드 기능 체험

### REST API

```bash
# 모든 호출 기록 조회
$ curl http://localhost:8088/api/calls

# 특정 호출 상세 조회
$ curl http://localhost:8088/api/calls/1

# 두 호출 간 diff 비교
$ curl http://localhost:8088/api/diff/1/2

# 데모 데이터 주입
$ curl -X POST http://localhost:8088/api/demo
```

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

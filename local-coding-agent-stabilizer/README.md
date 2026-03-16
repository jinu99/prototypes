# Local Coding Agent Stabilizer

> OpenAI-호환 프록시로 로컬 LLM 코딩 에이전트의 파괴적 파일 편집을 실시간 감지·차단하는 미들웨어

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Coding Agent (Aider 등)                     │
│              OPENAI_API_BASE=http://localhost:8400/v1            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ OpenAI-호환 API 요청
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    proxy.py (FastAPI :8400)                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  /v1/chat/completions  ─── 핵심 프록시 엔드포인트          │  │
│  │                                                            │  │
│  │  요청 수신 → 백엔드 전달 → 응답 내 tool_calls 추출        │  │
│  │              (SSE 스트리밍 투명 전달)                       │  │
│  └──────────┬──────────────────────┬─────────────────────────┘  │
│             │                      │                             │
│             ▼                      ▼                             │
│  ┌──────────────────┐   ┌──────────────────────┐                │
│  │   analyzer.py    │   │  loop_detector.py    │                │
│  │                  │   │                      │                │
│  │ • 파일 삭제 감지 │   │ • 동일 도구 연속     │                │
│  │ • 빈 파일 쓰기   │   │   3회 호출 감지      │                │
│  │ • 80%+ 코드 소실 │   │ • 세션별 호출 이력   │                │
│  │ • 위험 shell 명령│   │   추적 (SessionTracker)│               │
│  └────────┬─────────┘   └──────────┬───────────┘                │
│           │ (is_destructive, reason) │ (is_loop, reason)         │
│           └──────────┬──────────────┘                            │
│                      ▼                                           │
│           ┌────────────────────┐    ┌────────────────────┐      │
│           │  차단 시: 경고 응답 │    │  정상 시: 원본 전달 │      │
│           │  ⚠️ BLOCKED 반환   │    │  + 로그 기록        │      │
│           └────────┬───────────┘    └────────┬───────────┘      │
│                    └──────────┬──────────────┘                   │
│                               ▼                                  │
│                    ┌──────────────────┐                          │
│                    │     db.py        │                          │
│                    │  (SQLite 로그)   │                          │
│                    │                  │                          │
│                    │ • sessions 테이블│                          │
│                    │ • tool_calls     │                          │
│                    │   테이블         │                          │
│                    └────────┬─────────┘                          │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐  │
│  │  Dashboard (dashboard.html)  ─  GET /                      │  │
│  │  /api/sessions · /api/tool-calls · /api/blocked · /api/stats│  │
│  │  세션 상태, 도구 호출 이력, 차단 이벤트 실시간 조회          │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              LLM Backend (Ollama :11434 / Mock)                 │
└─────────────────────────────────────────────────────────────────┘
```

## Demo

Mock 모드로 실행하여 모든 감지 시나리오를 테스트할 수 있습니다 (Ollama 불필요).

```bash
$ ./demo.sh

================================================
  Agent Stabilizer — Demo
================================================

Starting proxy in MOCK mode (no backend needed)...

Running test scenarios...

🧪 Running Stabilizer Test Scenarios

Target: http://localhost:8400

=== Test 1: Normal tool call ===
  Content: I've written a simple hello world program.
  Blocked: False
  PASS

=== Test 2: File deletion ===
  Content: ⚠️ BLOCKED by Stabilizer: File deletion detected: /src/main.py
  Blocked: True
  PASS

=== Test 3: Empty file write ===
  Content: ⚠️ BLOCKED by Stabilizer: Empty file write detected: /src/utils.py
  Blocked: True
  PASS

=== Test 4: Massive deletion (>80%) ===
  Content: ⚠️ BLOCKED by Stabilizer: Excessive deletion in /src/app.py: 99% of content removed
  Blocked: True
  PASS

=== Test 5: Loop detection ===
  Content: ⚠️ BLOCKED by Stabilizer: Loop detected: tool 'edit_file' called 3 times consecutively
  Blocked: True
  PASS

=== Test 6: Dashboard APIs ===
  Stats: {"total_sessions": 5, "active_sessions": 4, "total_tool_calls": 8, "total_blocked": 5}
  Dashboard HTML: OK
  PASS

========================================
Results: 6 passed, 0 failed out of 6

================================================
  Dashboard: http://localhost:8400/
  Press Ctrl+C to stop
================================================
```

Aider 연동 시 파괴적 편집이 차단되는 예시:

```bash
# 1. 프록시 시작
$ uv run python proxy.py --mock

# 2. Aider를 프록시 경유로 실행
$ OPENAI_API_BASE=http://localhost:8400/v1 aider --model ollama/codellama

# 3. Aider에서 파괴적 요청을 하면 Stabilizer가 차단
> delete all files in src/
⚠️ BLOCKED by Stabilizer: File deletion detected: /src/main.py

# 4. 대시보드에서 차단 이벤트 확인
#    http://localhost:8400/
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# Mock 모드 실행 (Ollama 불필요)
uv run python proxy.py --mock

# 라이브 모드 실행 (Ollama 필요)
uv run python proxy.py --backend http://localhost:11434

# 데모 (자동으로 서버 시작 + 테스트 실행)
./demo.sh
```

대시보드: http://localhost:8400/

### Aider 연동

```bash
# 1. 프록시 시작
uv run python proxy.py

# 2. Aider를 프록시 경유로 실행
OPENAI_API_BASE=http://localhost:8400/v1 aider --model ollama/codellama
```

## 기능

- **파괴적 편집 감지**: 파일 삭제, 빈 파일 쓰기, 80% 이상 코드 소실 차단
- **루프 감지**: 동일 도구 연속 3회 호출 시 세션 중단
- **SSE 스트리밍**: OpenAI-호환 스트리밍 응답 투명 전달
- **세션 로그**: SQLite에 모든 도구 호출 + 차단 이벤트 기록
- **대시보드**: 세션 상태, 도구 호출 이력, 차단 이벤트 실시간 조회

## 구조

```
├── proxy.py            # FastAPI 리버스 프록시 (메인 서버)
├── analyzer.py         # diff 분석 기반 파괴적 편집 감지
├── loop_detector.py    # 연속 동일 도구 호출 루프 감지
├── db.py               # SQLite 세션/도구호출 로그
├── dashboard.html      # 단일 HTML 대시보드 (vanilla JS)
├── test_scenarios.py   # 자동화된 테스트 시나리오
├── test_dashboard.py   # Playwright 대시보드 테스트
├── demo.sh             # 원클릭 데모 스크립트
├── BUILD_LOG.md        # 빌드 일지
└── STATUS.md           # 프로토타입 상태
```

## 원본
prototype-pipeline spec: local-coding-agent-stabilizer

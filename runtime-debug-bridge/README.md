# Runtime Debug Bridge

> AI 코딩 에이전트가 MCP를 통해 실행 중인 앱의 런타임 컨텍스트(stdout, stderr, HTTP 트래픽, 프로세스 상태)를 직접 조회할 수 있는 디버깅 브릿지

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  사용자 / AI 에이전트 (Claude Code)                              │
│                                                                 │
│  "최근 에러 로그 보여줘"                                         │
│  "HTTP 트래픽 확인해줘"                                          │
│  "프로세스 상태 확인해줘"                                         │
└────────────────────┬────────────────────────────────────────────┘
                     │ JSON-RPC (stdio)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP Server (mcp_server.py)                                     │
│  ┌───────────────────┬──────────────────┬─────────────────────┐ │
│  │ get_recent_logs   │ get_http_traffic │ get_process_state   │ │
│  │     _tool         │     _tool        │     _tool           │ │
│  └────────┬──────────┴────────┬─────────┴──────────┬──────────┘ │
└───────────┼───────────────────┼────────────────────┼────────────┘
            │                   │                    │
            ▼                   ▼                    ▼
┌───────────────────┐ ┌─────────────────┐ ┌───────────────────────┐
│  Storage (SQLite) │ │  Storage        │ │  ProcInfo             │
│  storage.py       │ │  storage.py     │ │  procinfo.py          │
│                   │ │                 │ │                       │
│  logs 테이블      │ │  http_traffic   │ │  /proc/<pid>/status   │
│  - session_id     │ │  테이블         │ │  /proc/<pid>/fd       │
│  - stream         │ │  - method, url  │ │  /proc/<pid>/environ  │
│  - line, ts       │ │  - status_code  │ │  /proc/<pid>/cmdline  │
└────────┬──────────┘ │  - headers/body │ └───────────────────────┘
         │            └────────┬────────┘
         │                     │
         │    ┌────────────────┘
         ▼    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Capture Engine (capture.py)                                    │
│                                                                 │
│  ┌──────────────────────┐    ┌────────────────────────────────┐ │
│  │  subprocess 래핑     │    │  HTTP Forward Proxy            │ │
│  │  asyncio PIPE로      │    │  proxy.py                      │ │
│  │  stdout/stderr 캡처  │    │                                │ │
│  │       │              │    │  HTTP_PROXY 환경변수 주입 →    │ │
│  │       ▼              │    │  아웃바운드 요청 가로채기 →    │ │
│  │  실시간 SQLite 저장  │    │  요청/응답 SQLite 저장         │ │
│  └──────────────────────┘    └────────────────────────────────┘ │
│                         │                                       │
│                         ▼                                       │
│               ┌───────────────────┐                             │
│               │  대상 앱 프로세스  │                             │
│               │  (your_app.py)    │                             │
│               └───────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

**데이터 흐름 요약:**
1. `rdb wrap` → 대상 앱을 subprocess로 실행하며 stdout/stderr를 실시간 캡처, HTTP 프록시를 주입하여 아웃바운드 트래픽도 캡처
2. 캡처된 데이터는 SQLite(`~/.rdb/capture.db`)에 session 단위로 저장
3. `rdb mcp` → MCP 서버가 stdio transport로 실행되어 AI 에이전트가 3개 도구를 통해 런타임 데이터 조회

## Demo

### 1. 앱 래핑 및 캡처

```bash
$ uv run rdb wrap -- python3 examples/buggy_app.py

[rdb] Session: a1b2c3d4e5f6
[rdb] HTTP proxy: http://127.0.0.1:54321
[rdb] Running: python3 examples/buggy_app.py
[rdb] ---
Starting buggy app...
Making HTTP request to httpbin.org...
ERROR: Something went wrong!
Traceback (most recent call last):
  ...
ZeroDivisionError: division by zero
[rdb] ---
[rdb] Process exited with code 1
[rdb] Session a1b2c3d4e5f6 saved to /home/user/.rdb/capture.db
```

### 2. 캡처된 로그 조회 (CLI)

```bash
$ uv run rdb logs --stream stderr

[ERR] ERROR: Something went wrong!
[ERR] Traceback (most recent call last):
[ERR]   ...
[ERR] ZeroDivisionError: division by zero
```

### 3. HTTP 트래픽 조회 (CLI)

```bash
$ uv run rdb http

GET http://httpbin.org/get → 200
POST http://httpbin.org/post → 200
GET http://httpbin.org/status/500 → 500
```

### 4. 프로세스 상태 조회 (CLI)

```bash
$ uv run rdb ps 12345

{
  "pid": 12345,
  "open_fds": [{"fd": 0, "target": "/dev/pts/0"}, ...],
  "memory": {"rss_kb": 28416, "vsize_kb": 215040, "peak_kb": 215040},
  "cmdline": "python3 examples/buggy_app.py",
  "status": {"state": "S (sleeping)", "threads": 2, "ppid": 12300}
}
```

### 5. E2E 데모 (MCP 연동 포함)

```bash
$ uv run python3 examples/e2e_demo.py

============================================================
Runtime Debug Bridge — End-to-End Demo
============================================================

[1/4] Running buggy app through rdb wrap...
[rdb] Session: a1b2c3d4e5f6
...

[2/4] Querying recent logs via MCP (get_recent_logs_tool)...
  Session: a1b2c3d4e5f6
  Error logs (3 lines):
    [stderr] ERROR: Something went wrong!
    [stderr] ZeroDivisionError: division by zero

[3/4] Querying HTTP traffic via MCP (get_http_traffic_tool)...
  HTTP requests (2 captured):
    GET http://httpbin.org/get → 200
    POST http://httpbin.org/post → 200

[4/4] Querying process state via MCP (get_process_state_tool)...
  PID: 54321
  Memory: RSS=28416 KB
  Status: S (sleeping)
  Open FDs: 8

============================================================
Demo complete. All 3 MCP tools responded successfully.
============================================================
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 대상 앱을 래핑하여 실행 (stdout/stderr + HTTP 트래픽 캡처)
uv run rdb wrap -- python3 your_app.py

# 캡처된 로그 조회
uv run rdb logs
uv run rdb logs --stream stderr

# 캡처된 HTTP 트래픽 조회
uv run rdb http

# 프로세스 상태 조회 (/proc 기반)
uv run rdb ps <pid>

# MCP 서버 실행 (Claude Code 연동용)
uv run rdb mcp
```

## Claude Code 연동

`.claude/mcp.json` 또는 `.mcp.json`에 추가:

```json
{
  "mcpServers": {
    "runtime-debug-bridge": {
      "command": "uv",
      "args": ["--directory", "/path/to/runtime-debug-bridge", "run", "rdb", "mcp"]
    }
  }
}
```

연동 후 Claude Code에서:
- "최근 에러 로그 보여줘" → `get_recent_logs_tool`
- "HTTP 트래픽 확인해줘" → `get_http_traffic_tool`
- "프로세스 상태 확인해줘" → `get_process_state_tool`

## E2E 데모

```bash
uv run python3 examples/e2e_demo.py
```

## 구조

```
runtime-debug-bridge/
├── rdb/
│   ├── __init__.py
│   ├── cli.py          # CLI 엔트리포인트 (wrap, mcp, logs, http, ps)
│   ├── capture.py      # subprocess 래핑 + 실시간 stdout/stderr 캡처
│   ├── proxy.py        # HTTP 포워드 프록시 (아웃바운드 트래픽 캡처)
│   ├── procinfo.py     # /proc 파일시스템에서 프로세스 상태 읽기
│   ├── storage.py      # SQLite 스토리지 (로그, HTTP 트래픽)
│   └── mcp_server.py   # MCP 서버 (stdio transport, 3개 도구)
├── examples/
│   ├── buggy_app.py    # 테스트용 버그 앱
│   ├── e2e_demo.py     # End-to-end 데모 스크립트
│   └── mcp_config.json # Claude Code MCP 설정 예시
├── BUILD_LOG.md
├── STATUS.md
└── pyproject.toml
```

## 원본
prototype-pipeline spec: runtime-debug-bridge

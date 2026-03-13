# Runtime Debug Bridge

> AI 코딩 에이전트가 MCP를 통해 실행 중인 앱의 런타임 컨텍스트(stdout, stderr, HTTP 트래픽, 프로세스 상태)를 직접 조회할 수 있는 디버깅 브릿지

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

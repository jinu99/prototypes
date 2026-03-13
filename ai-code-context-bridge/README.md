# AI Code Context Bridge

> Mermaid 아키텍처 다이어그램을 파싱하여 AI 코딩 에이전트에게 파일별 구조화된 컨텍스트를 제공하는 MCP 서버 & CLI

## 실행 방법

```bash
# 의존성 설치
uv sync

# Mermaid 다이어그램 파싱
uv run context-bridge parse sample_project/architecture.mmd

# 파일의 아키텍처 컨텍스트 조회
uv run context-bridge lookup "services/order-service/src/api/routes.py" \
  -d sample_project/architecture.mmd \
  -c sample_project/mapping.json

# CLAUDE.md 자동 생성
uv run context-bridge generate-claude-md \
  -d sample_project/architecture.mmd \
  -c sample_project/mapping.json \
  --project-name "E-Commerce Platform"

# 전/후 비교 데모
uv run context-bridge demo \
  -d sample_project/architecture.mmd \
  -c sample_project/mapping.json \
  --project-name "E-Commerce Platform"

# MCP 서버 시작 (stdio transport)
uv run context-bridge serve \
  -d sample_project/architecture.mmd \
  -c sample_project/mapping.json

# (bonus) git hook 설치
uv run context-bridge install-hook .

# (bonus) 변경 의도 수동 기록
uv run context-bridge record-intent . \
  -f "services/order-service/src/api/routes.py" \
  -m "Add order cancellation endpoint"
```

## Claude Code MCP 연동

`~/.claude/claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "architecture-context": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/your/project",
        "run", "context-bridge", "serve",
        "-d", "your-architecture.mmd",
        "-c", "your-mapping.json"
      ]
    }
  }
}
```

이후 Claude Code에서 `get_file_context`, `list_services`, `get_service_context` 도구를 호출할 수 있습니다.

## 구조

```
ai-code-context-bridge/
├── src/context_bridge/
│   ├── cli.py              # CLI 진입점 (7 commands)
│   ├── mermaid_parser.py   # Mermaid C4/flowchart 파서
│   ├── mapper.py           # 파일↔서비스 매핑 엔진
│   ├── mcp_server.py       # MCP 서버 (4 tools)
│   ├── claude_md_gen.py    # CLAUDE.md 생성기
│   ├── demo.py             # 전/후 비교 데모
│   └── intent_hook.py      # git hook 변경 의도 기록
├── sample_project/
│   ├── architecture.mmd    # 샘플 C4 다이어그램 (8 services)
│   ├── architecture-flowchart.mmd  # 샘플 flowchart (12 nodes)
│   ├── mapping.json        # 파일↔서비스 매핑 설정
│   └── CLAUDE.md           # 생성된 CLAUDE.md 예시
├── test_mcp.py             # MCP 서버 통합 테스트
├── BUILD_LOG.md            # 빌드 일지
└── STATUS.md               # 검증 결과 (SUCCESS)
```

## 원본
prototype-pipeline spec: ai-code-context-bridge

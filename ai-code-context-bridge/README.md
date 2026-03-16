# AI Code Context Bridge

> Mermaid 아키텍처 다이어그램을 파싱하여 AI 코딩 에이전트에게 파일별 구조화된 컨텍스트를 제공하는 MCP 서버 & CLI

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         입력 (Input)                            │
│  ┌─────────────────────┐    ┌──────────────────────────┐       │
│  │  architecture.mmd   │    │    mapping.json           │       │
│  │  (Mermaid C4 또는    │    │  (파일 경로 → 서비스      │       │
│  │   Flowchart 다이어그램)│    │   glob 패턴 매핑 설정)    │       │
│  └──────────┬──────────┘    └────────────┬─────────────┘       │
└─────────────┼────────────────────────────┼─────────────────────┘
              │                            │
              ▼                            ▼
┌─────────────────────────┐  ┌──────────────────────────┐
│    MermaidParser         │  │    MappingConfig          │
│  mermaid_parser.py       │  │  mapper.py                │
│                          │  │                           │
│  • C4 Context/Container  │  │  • glob 패턴 매칭         │
│  • Flowchart/Graph       │  │  • 서비스/레이어 룰 관리   │
│  • 노드 + 관계 추출      │  │                           │
└──────────┬───────────────┘  └────────────┬──────────────┘
           │  ParsedDiagram                │  MappingRule[]
           │  (nodes + relationships)      │
           └──────────┬────────────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │     ContextMapper        │
        │     mapper.py            │
        │                          │
        │  파일 경로 ─▶ 서비스 매핑  │
        │  관련 서비스 탐색          │
        │  FileContext 생성         │
        └──────────┬───────────────┘
                   │
       ┌───────────┼───────────────┐
       │           │               │
       ▼           ▼               ▼
┌────────────┐ ┌──────────┐ ┌───────────────┐
│  CLI (7cmd)│ │MCP Server│ │ CLAUDE.md Gen │
│  cli.py    │ │mcp_server│ │ claude_md_gen │
│            │ │  .py     │ │   .py         │
│ • parse    │ │          │ │               │
│ • lookup   │ │ 4 Tools: │ │ 아키텍처 문서  │
│ • demo     │ │ get_file │ │ 자동 생성     │
│ • serve    │ │ _context │ │               │
│ • generate │ │ list_    │ └───────────────┘
│   -claude  │ │ services │
│   -md      │ │ list_    │  ┌──────────────┐
│ • install  │ │ relation │  │ Intent Hook  │
│   -hook    │ │ ships    │  │ intent_hook  │
│ • record   │ │ get_     │  │   .py        │
│   -intent  │ │ service_ │  │              │
│            │ │ context  │  │ git 변경 의도 │
└────────────┘ └──────────┘  │ 메타데이터    │
                             │ 기록          │
                             └──────────────┘
```

**데이터 흐름 요약**: Mermaid 다이어그램(.mmd)과 매핑 설정(.json)을 입력받아, 파서가 서비스/관계를 추출하고, 매퍼가 파일 경로를 서비스에 연결합니다. 이 컨텍스트는 CLI 조회, MCP 서버(AI 에이전트 연동), CLAUDE.md 자동 생성 세 가지 채널로 제공됩니다.

## Demo

### 1. Mermaid 다이어그램 파싱

```bash
$ uv run context-bridge parse sample_project/architecture.mmd

{
  "type": "c4_context",
  "nodes": [
    {"id": "customer", "label": "Customer", "type": "person", "layer": "external", ...},
    {"id": "api_gateway", "label": "API Gateway", "type": "system", "layer": "backend", ...},
    {"id": "order_service", "label": "Order Service", "type": "system", "layer": "backend", ...},
    ...
  ],
  "relationships": [
    {"source": "customer", "target": "api_gateway", "label": "Uses", "technology": "HTTPS"},
    {"source": "api_gateway", "target": "order_service", "label": "Routes orders", "technology": "REST/JSON"},
    ...
  ]
}
```

### 2. 파일별 아키텍처 컨텍스트 조회

```bash
$ uv run context-bridge lookup "services/order-service/src/api/routes.py" \
    -d sample_project/architecture.mmd \
    -c sample_project/mapping.json

{
  "file_path": "services/order-service/src/api/routes.py",
  "service": "order_service",
  "layer": "backend",
  "related_services": ["notification_service", "payment_ext", "api_gateway", "product_service"],
  "description": "Order Service — order lifecycle, payment orchestration"
}
```

### 3. 전/후 비교 데모

```bash
$ uv run context-bridge demo \
    -d sample_project/architecture.mmd \
    -c sample_project/mapping.json \
    --project-name "E-Commerce Platform"

======================================================================
  Context Bridge Demo — E-Commerce Platform
======================================================================

  Diagram: 8 services, 9 relationships
  Mapping: 7 file pattern rules

──────────────────────────────────────────────────────────────────────
  Scenario 1: Add a new endpoint to the Order Service that cancels an order
──────────────────────────────────────────────────────────────────────

## Without Context Bridge
❌ Missing: 서비스 소속, 레이어, 통신 관계, 아키텍처 제약

## With Context Bridge
✅ Agent가 파악하는 정보:
- 이 파일은 order_service (backend layer) 소속
- notification_service, payment_ext, product_service와 통신
- 변경 시 하류 서비스 영향도 자동 확인 가능
```

### 4. CLAUDE.md 자동 생성

```bash
$ uv run context-bridge generate-claude-md \
    -d sample_project/architecture.mmd \
    -c sample_project/mapping.json \
    --project-name "E-Commerce Platform"

Generated CLAUDE.md
```

서비스 목록, 통신 흐름, 파일↔서비스 매핑이 포함된 `CLAUDE.md`가 생성됩니다. AI 코딩 에이전트가 이 파일을 자동으로 읽어 아키텍처 컨텍스트를 확보합니다.

### 5. MCP 서버 연동

```bash
$ uv run context-bridge serve \
    -d sample_project/architecture.mmd \
    -c sample_project/mapping.json

Starting MCP server (stdio transport)...
```

서버 실행 후 Claude Code 등 AI 에이전트가 `get_file_context`, `list_services`, `list_relationships`, `get_service_context` 4개 도구를 호출하여 실시간으로 아키텍처 컨텍스트를 조회할 수 있습니다.

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

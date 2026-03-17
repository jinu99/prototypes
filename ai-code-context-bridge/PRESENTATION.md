---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# AI Code Context Bridge

**Mermaid 아키텍처 다이어그램 → AI 에이전트용 구조화된 컨텍스트**

- 카테고리: AI-assisted Development / Developer Tooling
- 스택: Python, uv, MCP SDK, Click
- 날짜: 2026-03-03

<!--
오늘 소개할 프로토타입은 AI Code Context Bridge다. 한 줄로 요약하면, Mermaid로 그린 아키텍처 다이어그램을 파싱해서 AI 코딩 에이전트에게 "이 파일이 어디 소속이고, 누구랑 통신하는지"를 알려주는 도구다. MCP 서버와 CLI, 두 가지 형태로 제공된다.
-->

---

## Background

**AI 코딩 에이전트의 맹점: 코드는 읽지만, 그림은 못 본다**

- Claude Code, Codex, Cursor 등 AI 코딩 에이전트가 코드를 직접 읽고 수정하는 시대
- 하지만 대부분의 프로젝트에는 C4 다이어그램, 서비스 경계도, 데이터 흐름도가 별도로 존재
- AI는 이 다이어그램을 **파싱하지 못한다** — 텍스트 파일만 읽을 수 있을 뿐
- 결과: 코드는 돌아가지만, **프로젝트 구조와 어긋나는 코드**를 생성
- CLAUDE.md, .cursorrules 같은 정적 텍스트로는 구조화된 아키텍처 정보 전달이 어려움

<!--
AI 코딩 도구들이 요즘 꽤 쓸만해졌다. 코드를 읽고, 수정하고, 새로 만들기도 한다. 그런데 한 가지 맹점이 있다. 대부분의 팀에는 Mermaid나 C4로 그린 아키텍처 다이어그램이 있는데, AI가 이걸 못 읽는다. 코드는 보지만 그림은 못 보는 거다. 그래서 코드 자체는 돌아가는데, 프로젝트의 전체 구조랑 안 맞는 코드가 나온다. 결국 이건 AI의 "입력"이 부족한 문제다.
-->

---

## Pain Point

**커뮤니티에서 반복적으로 나오는 세 가지 고통**

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | Reddit r/SideProject | ★★★ | AI에게 프로젝트 구조와 설계 의도를 전달할 도구가 없어, **올바른 것을 잘못된 방식으로 구현**한다 |
| 2 | Hacker News | ★★★ | 코드 변경의 **'의도(intent)'가 기록되지 않아** 왜 변경했는지 추적이 어렵다 |
| 3 | Hacker News | ★★★ | 터미널에서 최신 라이브러리 문서를 LLM에 바로 파이프할 도구가 없다 |

- 공통 원인: **AI 에이전트에 대한 구조화된 컨텍스트 입력이 부족**
- 기존 도구들은 AI의 "출력"을 관리하는 데 집중, "입력"을 구조화하는 건 방치

<!--
Reddit이나 Hacker News에서 이런 얘기가 계속 나온다. AI 코딩 도구가 좋은데, 만든 코드가 프로젝트 구조를 무시한다는 거다. 세 가지 signal이 모두 강도 3이다. 첫 번째가 가장 핵심인데, "올바른 것을 잘못된 방식으로 구현한다"는 표현이 정확하다. 기능은 맞는데 아키텍처가 틀린 거다. 이 세 문제의 공통 원인은 결국 하나다. AI에게 주는 입력이 구조화되어 있지 않다.
-->

---

## Solution

**기존 아키텍처 다이어그램을 AI가 이해할 수 있는 구조화된 컨텍스트로 변환**

- 핵심 아이디어: 기존 도구가 AI의 **출력**을 관리한다면, 이 도구는 AI의 **입력**을 구조화
- Mermaid 다이어그램(.mmd) + 매핑 설정(.json) → 파일별 컨텍스트 자동 생성
- 세 가지 채널로 제공:
  - **CLI**: `context-bridge lookup "path/to/file.py"` → 소속 서비스, 레이어, 관련 서비스
  - **MCP 서버**: AI 에이전트가 실시간으로 도구 호출하여 컨텍스트 조회
  - **CLAUDE.md 생성**: 아키텍처 정보가 포함된 CLAUDE.md 자동 생성

- 차별점: C4Diagrammer는 코드→다이어그램 방향. 이 도구는 **다이어그램→AI 컨텍스트** 방향

<!--
접근법은 간단하다. 팀이 이미 가지고 있는 Mermaid 아키텍처 다이어그램을 파싱해서, AI가 이해할 수 있는 JSON 컨텍스트로 바꾸는 거다. 기존에 C4Diagrammer 같은 도구가 있는데 그건 코드에서 다이어그램을 만드는 방향이다. 우리는 반대다. 다이어그램에서 AI 컨텍스트를 뽑는다. 그리고 이걸 CLI, MCP 서버, CLAUDE.md 생성 세 가지 경로로 제공한다. MCP 서버가 핵심인데, AI 에이전트가 코드를 수정하기 전에 "이 파일이 어디 소속이지?" 하고 물어볼 수 있게 된다.
-->

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  입력: architecture.mmd + mapping.json                    │
└────────────┬─────────────────────────┬───────────────────┘
             ▼                         ▼
   ┌──────────────────┐    ┌──────────────────┐
   │  MermaidParser    │    │  MappingConfig   │
   │  C4/Flowchart    │    │  glob 패턴 매칭   │
   │  노드+관계 추출   │    │  서비스 룰 관리   │
   └────────┬─────────┘    └────────┬─────────┘
            └──────────┬───────────┘
                       ▼
            ┌──────────────────┐
            │  ContextMapper   │
            │  파일→서비스 매핑  │
            │  FileContext 생성 │
            └──────┬───────────┘
         ┌─────────┼──────────┐
         ▼         ▼          ▼
   ┌──────────┐ ┌────────┐ ┌──────────────┐
   │ CLI(7cmd)│ │MCP(4t) │ │CLAUDE.md Gen │
   └──────────┘ └────────┘ └──────────────┘
```

- **MermaidParser**: 정규식 기반. C4 Context/Container, Flowchart 두 포맷 지원
- **ContextMapper**: fnmatch로 파일 경로 → 서비스 매핑. 관련 서비스 자동 탐색
- **MCP Server**: `get_file_context`, `list_services`, `list_relationships`, `get_service_context`

<!--
구조는 크게 세 단계다. 먼저 Mermaid 파서가 다이어그램에서 노드와 관계를 추출한다. 정규식으로 충분해서 외부 의존성 없이 구현했다. 그 다음 ContextMapper가 파일 경로를 glob 패턴으로 서비스에 매핑한다. 마지막으로 이걸 CLI, MCP 서버, CLAUDE.md 생성기 세 채널로 내보낸다. MCP 서버가 4개 도구를 제공하는데, AI 에이전트 입장에서 가장 많이 쓸 건 get_file_context다. 파일 경로 하나 넣으면 소속 서비스, 레이어, 관련 서비스를 바로 돌려준다.
-->

---

## Demo

**파일 하나의 아키텍처 컨텍스트를 실시간으로 조회**

```json
$ context-bridge lookup "services/order-service/src/api/routes.py"

{
  "file_path": "services/order-service/src/api/routes.py",
  "service": "order_service",
  "layer": "backend",
  "related_services": [
    "notification_service", "payment_ext",
    "api_gateway", "product_service"
  ],
  "description": "Order Service — order lifecycle, payment orchestration"
}
```

**Before vs After**:
- Without Context Bridge: AI가 서비스 소속, 레이어, 통신 관계를 모른 채 코드 생성
- With Context Bridge: "이 파일은 order_service (backend)이고, notification, payment, product 서비스와 통신" — 이걸 알고 코드를 쓴다

<!--
실제로 돌려보면 이런 결과가 나온다. order-service의 routes.py 파일을 조회하면, 이 파일이 backend 레이어의 order_service 소속이고, notification, payment, api_gateway, product 서비스와 통신한다는 걸 알려준다. 이 정보가 있으면 AI가 order cancellation endpoint를 만들 때 notification 서비스에 알림을 보내야 한다는 걸 고려할 수 있다. 없으면 그냥 DB만 업데이트하는 코드를 만들 거다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 결정 | 이유 |
|------|------|
| **Python + uv** | Mermaid 파싱은 정규식으로 충분, MCP Python SDK가 성숙, 외부 의존성 최소화 |
| **정규식 파서** (외부 파서 라이브러리 X) | C4/Flowchart 두 포맷만 커버하면 되므로 직접 구현이 빠르고 의존성 없음 |
| **fnmatch 기반 매핑** | 디렉토리 구조 → 서비스 매핑에 glob 패턴이 직관적. 복잡한 설정 불필요 |

### 시행착오
- C4 파서에서 System_Ext vs System 순서 문제 → specific-first 정렬로 해결
- Flowchart에서 `[(Order DB)]` 같은 레이블 괄호 잔류 → `_clean_label` 헬퍼 추가

### 심의 점수
- 학습 가치: **4.3**/5 | 문제 진정성: 3.7/5 | 프로토타입 적합성: 3.7/5
- 반대 의견: "전/후 비교가 주관적" — 맞는 지적. 실제 코드 생성 비교까지는 못 감

<!--
스택은 Python과 uv를 골랐다. Mermaid 파싱이 정규식으로 충분하고, MCP Python SDK가 잘 되어 있어서 외부 의존성을 최소화할 수 있었다. 시행착오가 좀 있었는데, C4 파서에서 System과 System_Ext를 구분하는 순서가 중요했다. 패턴 매칭 순서를 specific-first로 바꿔서 해결했다. 심의에서 서연이 "전후 비교가 주관적이다"라고 지적했는데, 솔직히 맞는 말이다. 실제 AI 에이전트에게 코드를 생성시켜서 비교하는 건 이 프로토타입 범위에서 못 했다. 대신 주입되는 정보의 차이를 명확히 보여주는 데 집중했다.
-->

---

## Results & Future

### 성과 (5/5 통과)
- [x] Mermaid C4/Flowchart → JSON 파싱 (C4: 8 nodes/9 rels, Flowchart: 12 nodes/12 rels)
- [x] 파일↔서비스 매핑 (glob 패턴 기반, 미매핑 에러 처리 포함)
- [x] MCP 서버 4개 도구 — 클라이언트 통합 테스트 통과
- [x] 전/후 비교 데모 (3 시나리오)
- [x] (bonus) git hook 변경 의도 기록

### 한계
- 실제 AI 코드 생성 품질 비교는 미검증 (컨텍스트 차이만 보여줌)
- Mermaid만 지원 (PlantUML, Structurizr DSL 미지원)
- 매핑 설정을 수동으로 작성해야 함

### 프로덕트가 되려면
- 매핑 설정 자동 생성 (디렉토리 구조 분석 → 매핑 룰 추론)
- PlantUML, Structurizr DSL 등 다이어그램 포맷 확장
- 실제 코드 생성 A/B 테스트: 컨텍스트 주입 전/후 코드 품질 정량 비교
- IDE 확장 (VS Code) — 파일 열 때 아키텍처 컨텍스트 자동 표시

<!--
완료 기준 5개 중 5개 전부 통과했다. bonus였던 git hook 변경 의도 기록까지 포함해서. 다만 솔직히 아쉬운 부분이 있다. 이 프로토타입이 증명한 건 "이런 정보를 줄 수 있다"는 것이지, "이 정보를 주면 코드가 실제로 나아진다"는 건 아직 검증 못 했다. 프로덕트가 되려면 매핑 설정 자동 생성이 필수다. 지금은 수동으로 JSON을 써야 하는데, 디렉토리 구조를 분석해서 자동으로 룰을 추론하는 게 다음 단계다. 그리고 실제 A/B 테스트로 코드 품질 차이를 정량적으로 보여줘야 설득력이 생긴다.
-->

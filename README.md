# Prototypes

커뮤니티(HN, Reddit, GeekNews, GitHub Trending)에서 발굴한 개발자 pain point를 자동으로 프로토타이핑하는 파이프라인의 산출물.

> crawl → analyze → ideate → select → spawn

각 프로토타입은 독립 실행 가능한 단위로, 자동 생성 후 수동 큐레이션 없이 이 레포에 커밋됩니다.

---

## Index

### AI Agent & LLM Infra

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [agent-first-architecture-transition-cost-asymmetry-and-escalation-quality](./agent-first-architecture-transition-cost-asymmetry-and-escalation-quality) | Agent의 confidence 기반 에스컬레이션이 Workflow의 규칙 기반보다 품질이 높다는 가설을 시뮬레이션으로 검증 | Python |
| [agent-platformization-control-plane-and-tool-composition-infra](./agent-platformization-control-plane-and-tool-composition-infra) | 에이전트 플랫폼화를 위한 컨트롤 플레인 및 도구 조합 인프라 | Python |
| [agent-token-waste-analyzer](./agent-token-waste-analyzer) | Claude Code 세션 로그를 분석하여 토큰 낭비 패턴을 식별하고 최적화 제안을 제공하는 터미널 대시보드 CLI | Python |
| [agentic-coding-workspace](./agentic-coding-workspace) | 셀 기반 인터페이스에서 AI 에이전트 플랜을 사전 검토·수정하고 셀 단위로 재실행하는 코딩 워크스페이스 | Node.js |
| [local-agent-mesh](./local-agent-mesh) | 소형/대형 LLM 간 복잡도 기반 스마트 라우팅 + self-delegation CLI | Python |
| [local-agent-resource-planner](./local-agent-resource-planner) | GGUF 메타데이터 기반 멀티 모델 VRAM 예측 및 리소스 플래닝 도구 | Python |
| [local-coding-agent-stabilizer](./local-coding-agent-stabilizer) | 로컬 LLM 코딩 에이전트의 파괴적 파일 편집을 실시간 감지·차단하는 OpenAI-호환 프록시 | Python |

### AI Code Quality & DevTools

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [ai-code-change-tracker](./ai-code-change-tracker) | tree-sitter AST + git diff로 코드 변경의 downstream 영향 범위 추적 및 spec 괴리 자동 탐지 CLI | Python |
| [ai-code-context-bridge](./ai-code-context-bridge) | Mermaid 아키텍처 다이어그램을 파싱하여 AI 코딩 에이전트에게 구조화된 컨텍스트를 제공하는 MCP 서버 | Python |
| [ai-code-perf-verifier](./ai-code-perf-verifier) | Git diff에서 변경된 함수의 변경 전/후 성능을 비교하여 머지 전 성능 회귀를 탐지하는 CLI | Python |
| [ai-agent-secret-scrubber](./ai-agent-secret-scrubber) | AI 에이전트 출력 스트림에서 시크릿을 실시간 탐지·마스킹하는 쉘 래퍼 | Python |
| [vibe-code-decay-detector](./vibe-code-decay-detector) | Git 히스토리 기반 아키텍처 침식 탐지 — 의존성 결합도, 순환 의존성, churn rate 추적 | Python |
| [vibe-code-prod-audit](./vibe-code-prod-audit) | tree-sitter 기반 바이브코딩 FastAPI 프로젝트 프로덕션 준비도 감사 CLI | Python |

### LLM Ops & Debugging

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [llm-context-debugger](./llm-context-debugger) | OpenAI Chat Completions API 프록시로 컨텍스트 윈도우의 토큰 구성을 실시간 분석·시각화 | Python |
| [local-llm-qual-probe](./local-llm-qual-probe) | 소형 로컬 LLM의 실패 패턴(JSON 깨짐, 멀티턴 붕괴, 과잉 출력)을 한 줄 명령으로 감지하는 CLI | Python |
| [local-llm-resource-monitor](./local-llm-resource-monitor) | KV 캐시 포함 VRAM 추정과 GPU 상태 기반 모델 로드 가능 여부를 실시간으로 보여주는 대시보드 | Python |
| [local-llm-serve-guard](./local-llm-serve-guard) | VRAM 사용량 기반 동적 어드미션 컨트롤로 로컬 LLM OOM을 방지하는 리버스 프록시 | Python |
| [long-context-consistency](./long-context-consistency) | 장편 텍스트에서 사실을 추출하고 임베딩 유사도 기반으로 잠재적 불일치를 탐지하는 CLI | Python |
| [embedding-migration-guard](./embedding-migration-guard) | 임베딩 모델 교체 전 recall@k 드롭을 예측하여 전체 재인덱싱 없이 마이그레이션 의사결정 지원 | Python |
| [runtime-debug-bridge](./runtime-debug-bridge) | AI 코딩 에이전트가 MCP로 실행 중인 앱의 런타임 컨텍스트를 직접 조회하는 디버깅 브릿지 | Python |

### CI/CD & Infrastructure

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [ci-yaml-generator](./ci-yaml-generator) | 프로젝트 디렉토리를 스캔하여 GitHub Actions CI 워크플로우 YAML을 자동 생성하는 CLI | Node.js |
| [sql-ci-static-guard](./sql-ci-static-guard) | sqlglot AST 기반 SQL 안티패턴 감지 CLI — cross-dialect 지원, pre-commit hook 통합 | Python |
| [deploy-soak-monitor](./deploy-soak-monitor) | 배포 후 자동 soak 윈도우 모니터링 — pod 상태/로그 실시간 감시로 이상 징후를 잡아내는 CLI | Python |
| [log-incident-correlator](./log-incident-correlator) | Drain3 기반 first-seen 로그 패턴 탐지와 배포 이벤트 자동 상관관계 분석 | Python |
| [webhook-chaos-tester](./webhook-chaos-tester) | 웹훅 엔드포인트에 chaos 시나리오(duplicate, delay, reorder)를 실행하여 멱등성 버그를 찾는 CLI | Python |

### Web & SEO

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [web-health-guard](./web-health-guard) | URL 하나로 기술 SEO, AI 크롤러 방어, 팬텀 URL을 한 화면에서 진단하는 웹 도구 | Python |
| [seo-indie-toolkit](./seo-indie-toolkit) | SPA 크롤러 시뮬레이션으로 검색엔진이 놓치는 SEO 인덱싱 문제를 진단 | Node.js |
| [oss-search-guard](./oss-search-guard) | 오픈소스 프로젝트의 검색 결과에서 사칭 사이트를 탐지 | Python |

### Document & Content

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [doc-structure-converter](./doc-structure-converter) | Structure-aware Markdown to PDF converter — 테이블/코드 블록이 페이지 경계에서 잘리지 않음 | Node.js |
| [doc-freshness-monitor](./doc-freshness-monitor) | 코드 심볼 참조 기반으로 문서의 staleness를 감지하는 CLI | Python |
| [rag-doc-cleaner](./rag-doc-cleaner) | PDF의 OCR 노이즈를 자동 감지·제거하여 RAG 파이프라인에 투입할 정제 텍스트를 생성 | Python |
| [slide-lastmile-editor](./slide-lastmile-editor) | Marp 마크다운 슬라이드를 브라우저에서 시각적으로 편집하고 원본 .md와 블록 레벨 양방향 동기화 | Node.js |
| [indie-launch-kit](./indie-launch-kit) | README.md 하나로 랜딩페이지, 체인지로그, 런치 포스트를 CLI 한 줄에 생성 | Node.js |

### Indie / Small Biz

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [indie-ops-dashboard](./indie-ops-dashboard) | 솔로 개발자를 위한 경량 인프라 운영 대시보드 — 서버 리소스 패턴 분석 + 비용 최적화 인사이트 | Python |
| [small-biz-queue-ops](./small-biz-queue-ops) | QR 코드 기반 매장 대기열 관리 시스템 — 실시간 대기 순서 표시, 매장 관리, KDS 뷰 | Node.js |
| [community-keyword-monitor](./community-keyword-monitor) | 멀티플랫폼 커뮤니티(Reddit, RSS)에서 키워드를 모니터링하고 통합 타임라인으로 확인 | Python |
| [local-email-cleanup](./local-email-cleanup) | IMAP 헤더 메타데이터만으로 뉴스레터·마케팅 이메일을 자동 분류하고 정리 제안을 생성하는 CLI | Python |

### IoT & Data

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [iot-cloud-dependency-scanner](./iot-cloud-dependency-scanner) | 홈 네트워크의 IoT 기기를 자동 발견하고 DNS 트래픽 분석으로 클라우드 의존도를 정량화 | Python |
| [local-first-data-guard](./local-first-data-guard) | 브라우저 스토리지 내구성 자동 탐지 + IndexedDB ↔ OPFS 크로스 스토리지 자동 복구 라이브러리 | TypeScript |
| [openapi-form-tester](./openapi-form-tester) | OpenAPI 스펙에서 자동 생성된 폼으로 API를 테스트하고 응답-스펙 드리프트를 시각화 | Node.js |

---

## How it works

이 레포의 프로토타입은 [prototype-pipeline](https://github.com/jinu99/prototype-pipeline)에 의해 자동 생성됩니다.

1. **Crawl** — HN, Reddit, GeekNews, GitHub Trending에서 게시물 수집 (10분마다)
2. **Analyze** — Claude가 수집된 게시물에서 pain point 추출 (3시간마다)
3. **Ideate** — pain point 클러스터링 → 프로토타입 아이디어 생성 (3시간마다)
4. **Select** — 아이디어를 심의하여 구현할 spec 선별 (6시간마다)
5. **Spawn** — Claude가 spec을 읽고 프로토타입을 자동 구현 (6시간마다)

새 프로토타입이 성공적으로 생성되면 자동으로 이 레포에 커밋·푸시됩니다.

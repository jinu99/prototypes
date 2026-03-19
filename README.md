# Prototypes

커뮤니티(HN, Reddit, GeekNews, GitHub Trending)에서 발굴한 개발자 pain point를 자동으로 프로토타이핑하는 파이프라인의 산출물.

> crawl → analyze → ideate → select → spawn

각 프로토타입은 독립 실행 가능한 단위로, 자동 생성 후 이 레포에 커밋됩니다.

## Architecture

```
Community Sources                 Pipeline (cron-automated)                    Output
─────────────────    ──────────────────────────────────────────    ──────────────────

  HN ─────────┐     ┌──────────┐    ┌──────────┐                 pain-points/
  Reddit ─────┼────▶│  Crawl   │───▶│ Analyze  │────────────────▶  2026-03-16-hn.jsonl
  GeekNews ───┤     │  (bash)  │    │ (claude) │                   2026-03-16-reddit.jsonl
  GH Trend ───┘     │  */10min │    │  /3hour  │                   ...
                     └──────────┘    └────┬─────┘
                                          │
                                          ▼
                                    ┌──────────┐                  ideas/
                                    │  Ideate  │─────────────────▶  ai-code-change-tracker.md
                                    │ (claude) │                    local-agent-mesh.md
                                    │  /3hour  │                    ...
                                    └────┬─────┘
                                         │
                                         ▼
                                    ┌──────────┐                  specs/
                                    │  Select  │─────────────────▶  ai-code-change-tracker.md
                                    │ (claude) │  approve/reject    small-biz-queue-ops.md
                                    │  /6hour  │                    ...
                                    └────┬─────┘
                                         │
                                         ▼
                                    ┌──────────┐                  prototypes/  ← this repo
                                    │  Spawn   │─────────────────▶  ai-code-change-tracker/
                                    │ (claude) │  git commit+push   small-biz-queue-ops/
                                    │  /6hour  │                    ...
                                    └──────────┘
```

## Demo: Pipeline in Action

**1. Crawl** — 커뮤니티 게시물을 10분마다 수집

```json
{"id":"1rupekm","source":"reddit","pain_point":"AI 코딩 도구로 생성된 코드의 downstream 영향 추적이 불가능","signal_strength":4,"tags":["ai-coding","devtools"]}
```

**2. Analyze** — Claude가 pain point를 추출·분류 (signal_strength 1-5)

```
483개 게시물 → 88개 pain points 추출 (중복 제거 후)
├── Reddit:  30 (sig3: 26, sig2: 4)
├── HN:      36 (sig3: 29, sig2: 7)
├── GeekNews: 5 (sig3: 4, sig2: 1)
└── GitHub:  17 (sig4: 5, sig3: 11, sig2: 1)
```

**3. Ideate** — pain point 클러스터링 → 아이디어 생성

```markdown
# AI 코드 변경 영향 추적기
> tree-sitter AST + git diff로 코드 변경의 downstream 영향 범위를 추적

## Pain Points 근거
| 출처 | Signal | Pain Point |
|------|--------|------------|
| reddit | 5 | 바이브코딩으로 만든 앱의 품질·보안이 심각하게 우려 |
| hn     | 4 | AI 코딩 도구 과사용 시 인지적 부채 발생 |
| geeknews | 4 | AI 시대에 테스트 코드 없으면 안정성 유지 불가 |
```

**4. Select** — 3인 가상 심의위원이 승인/기각 결정

```json
{"slug":"ai-code-change-tracker","status":"approved","scores":{"authenticity":4.3,"prototypability":4.0,"freshness":3.7,"learning":4.7}}
```

**5. Spawn** — Claude가 spec 기반으로 프로토타입 자동 구현

```
# STATUS: SUCCESS
- [x] git diff 파싱 → tree-sitter로 변경된 함수/클래스 식별
- [x] 변경된 심볼의 1-hop downstream 영향 트리 시각화 (CLI)
- [x] spec 문서와 실제 코드 구현체 매핑
- [x] "구현됨 / 미구현 / 코드에만 존재" 상태 출력
```

---

### AI Agent & LLM Infra

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [agent-first-architecture-transition-cost-asymmetry-and-escalation-quality](./agent-first-architecture-transition-cost-asymmetry-and-escalation-quality) | Agent의 confidence 기반 에스컬레이션이 Workflow의 규칙 기반 에스컬레이션보다 품질이 높다는 가설을 시뮬레이션으로 검증한다. | Python |
| [agentic-coding-workspace](./agentic-coding-workspace) | 셀 기반 인터페이스에서 AI 에이전트 플랜을 사전 검토·수정하고 셀 단위로 재실행하는 코딩 워크스페이스 프로토타입 | Node.js |
| [agent-platformization-control-plane-and-tool-composition-infra](./agent-platformization-control-plane-and-tool-composition-infra) | (설명 없음) | Python |
| [agent-token-waste-analyzer](./agent-token-waste-analyzer) | Claude Code 세션 로그를 분석하여 토큰 낭비 패턴을 식별하고 최적화 제안을 제공하는 터미널 대시보드 CLI | Python |
| [ai-code-context-bridge](./ai-code-context-bridge) | Mermaid 아키텍처 다이어그램을 파싱하여 AI 코딩 에이전트에게 파일별 구조화된 컨텍스트를 제공하는 MCP 서버 & CLI | Python |
| [local-agent-mesh](./local-agent-mesh) | 소형/대형 LLM 간 복잡도 기반 스마트 라우팅 + self-delegation CLI 도구 | Python |
| [local-agent-resource-planner](./local-agent-resource-planner) | GGUF 메타데이터 기반 멀티 모델 VRAM 예측 및 리소스 플래닝 도구 | Python |
| [local-coding-agent-stabilizer](./local-coding-agent-stabilizer) | OpenAI-호환 프록시로 로컬 LLM 코딩 에이전트의 파괴적 파일 편집을 실시간 감지·차단하는 미들웨어 | Python |
| [runtime-debug-bridge](./runtime-debug-bridge) | AI 코딩 에이전트가 MCP를 통해 실행 중인 앱의 런타임 컨텍스트(stdout, stderr, HTTP 트래픽, 프로세스 상태)를 직접 조회할 수 있는 디버깅 브릿지 | Python |

### AI Code Quality & DevTools

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [ai-agent-secret-scrubber](./ai-agent-secret-scrubber) | AI 에이전트 출력 스트림에서 시크릿을 실시간 탐지·마스킹하는 쉘 래퍼 | Python |
| [ai-code-change-tracker](./ai-code-change-tracker) | tree-sitter AST 파싱 + git diff 분석으로 코드 변경의 downstream 영향 범위를 추적하고, spec 문서와의 괴리를 자동 탐지하는 CLI 도구 | Python |
| [ai-code-perf-verifier](./ai-code-perf-verifier) | Git diff에서 변경된 Python 함수를 자동 식별하고, 변경 전/후 성능을 비교하여 머지 전 성능 회귀를 탐지하는 CLI 도구 | Python |
| [ai-code-smell-linter](./ai-code-smell-linter) | tree-sitter AST 기반으로 AI 생성 코드의 구조적 위험 패턴을 탐지하는 CLI 린터 | Python |
| [sql-ci-static-guard](./sql-ci-static-guard) | sqlglot AST 기반 SQL 안티패턴 감지 CLI — cross-dialect 지원, pre-commit hook 통합 | Python |
| [vibe-code-decay-detector](./vibe-code-decay-detector) | Git 히스토리 기반 아키텍처 침식 탐지 CLI — 의존성 결합도, 순환 의존성, churn rate 추적 및 commit-revert 패턴 감지 | Python |
| [vibe-code-prod-audit](./vibe-code-prod-audit) | tree-sitter 기반 바이브코딩 FastAPI 프로젝트 프로덕션 준비도 감사 CLI 도구 | Python |

### LLM Ops & Debugging

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [embedding-migration-guard](./embedding-migration-guard) | CLI 도구로 임베딩 모델 교체 전 recall@k 드롭을 예측하여, 전체 재인덱싱 없이 마이그레이션 의사결정을 내릴 수 있게 합니다. | Python |
| [llm-context-debugger](./llm-context-debugger) | OpenAI Chat Completions API 프록시로 컨텍스트 윈도우의 토큰 구성을 실시간 분석·시각화 | Python |
| [local-llm-qual-probe](./local-llm-qual-probe) | 소형 로컬 LLM의 실패 패턴(JSON 깨짐, 멀티턴 붕괴, 과잉 출력)을 한 줄 명령으로 감지하는 CLI 도구 | Python |
| [local-llm-resource-monitor](./local-llm-resource-monitor) | KV 캐시 포함 VRAM 추정과 GPU 상태 기반 모델 로드 가능 여부를 실시간으로 보여주는 대시보드 | Python |
| [local-llm-serve-guard](./local-llm-serve-guard) | VRAM 사용량 기반 동적 어드미션 컨트롤로 로컬 LLM OOM을 방지하는 OpenAI-호환 리버스 프록시 | Python |
| [long-context-consistency](./long-context-consistency) | 장편 텍스트에서 사실을 추출하고, 임베딩 유사도 기반으로 잠재적 불일치를 탐지하는 CLI 도구 | Python |

### CI/CD & Infrastructure

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [ci-yaml-generator](./ci-yaml-generator) | 프로젝트 디렉토리를 스캔하여 GitHub Actions CI 워크플로우 YAML을 자동 생성하는 CLI 도구 | Node.js |
| [deploy-soak-monitor](./deploy-soak-monitor) | 배포 후 자동 soak 윈도우 모니터링 — pod 상태/로그 실시간 감시로 이상 징후를 잡아내는 CLI 도구 | Python |
| [log-incident-correlator](./log-incident-correlator) | Drain3 기반 first-seen 로그 패턴 탐지와 배포 이벤트 자동 상관관계 분석 프로토타입 | Python |
| [webhook-chaos-tester](./webhook-chaos-tester) | CLI tool that runs chaos scenarios (duplicate, delay, reorder) against webhook endpoints to find idempotency and error-handling bugs. | Python |

### Web & SEO

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [oss-search-guard](./oss-search-guard) | Detect impersonation sites in search results for open-source projects. | Python |
| [seo-indie-toolkit](./seo-indie-toolkit) | SPA 크롤러 시뮬레이션으로 검색엔진이 놓치는 SEO 인덱싱 문제를 진단하는 도구 | Node.js |
| [web-health-guard](./web-health-guard) | URL 하나로 기술 SEO, AI 크롤러 방어, 팬텀 URL을 한 화면에서 진단하는 웹 도구 | Python |

### Document & Content

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [doc-freshness-monitor](./doc-freshness-monitor) | 코드 심볼 참조 기반으로 문서의 staleness를 감지하는 CLI 도구 | Python |
| [doc-structure-converter](./doc-structure-converter) | Structure-aware Markdown to PDF converter that prevents tables and code blocks from splitting across page boundaries. | Node.js |
| [indie-launch-kit](./indie-launch-kit) | README.md 하나로 랜딩페이지, 체인지로그, 런치 포스트를 CLI 한 줄에 생성 | Node.js |
| [rag-doc-cleaner](./rag-doc-cleaner) | PDF 문서의 OCR 노이즈(워터마크, 반복 헤더/푸터, 아티팩트)를 자동 감지·제거하여 RAG 파이프라인에 투입할 정제 텍스트를 생성합니다. | Python |
| [slide-lastmile-editor](./slide-lastmile-editor) | Marp 마크다운 슬라이드를 브라우저에서 시각적으로 편집하고, 원본 .md 파일과 블록 레벨 양방향 동기화 | Node.js |

### Indie / Small Biz

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [community-keyword-monitor](./community-keyword-monitor) | 멀티플랫폼 커뮤니티(Reddit, RSS)에서 키워드를 모니터링하고 통합 타임라인으로 확인하는 대시보드 | Python |
| [indie-ops-dashboard](./indie-ops-dashboard) | 솔로 개발자를 위한 경량 인프라 운영 대시보드 — 서버 리소스 패턴 분석 + 비용 최적화 인사이트 | Python |
| [indie-prod-monitor](./indie-prod-monitor) | Simhash 기반 경량 로그 클러스터링 + 헬스체크 + 하트비트 — 제로 설정 단일 바이너리 | Other |
| [indie-revenue-attribution](./indie-revenue-attribution) | 인디 개발자를 위한 채널별 매출 어트리뷰션 대시보드 — UTM-to-payment 매칭으로 진짜 CAC와 ROI를 한눈에 | Python |
| [local-email-cleanup](./local-email-cleanup) | IMAP 헤더 메타데이터만으로 뉴스레터·마케팅·알림 이메일을 자동 분류하고 정리 제안을 생성하는 CLI 도구 | Python |
| [small-biz-queue-ops](./small-biz-queue-ops) | QR 코드 기반 매장 대기열 관리 시스템 — 실시간 대기 순서 표시, 매장 관리, KDS 뷰 | Node.js |

### IoT & Data

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [iot-cloud-dependency-scanner](./iot-cloud-dependency-scanner) | 홈 네트워크의 IoT 기기를 자동 발견하고 DNS 트래픽 분석으로 클라우드 의존도를 정량화하여, 실행 가능한 로컬 대안을 제시하는 진단 도구 | Python |
| [local-first-data-guard](./local-first-data-guard) | 브라우저 스토리지 내구성 자동 탐지 + IndexedDB ↔ OPFS 크로스 스토리지 자동 복구 라이브러리 | TypeScript |
| [openapi-form-tester](./openapi-form-tester) | OpenAPI 스펙에서 자동 생성된 폼으로 API를 테스트하고 응답-스펙 드리프트를 즉시 시각화하는 로컬 웹 도구 | Node.js |

### Other

| Prototype | Description | Stack |
|-----------|-------------|-------|
| [docs](./docs) | (설명 없음) | Other |
| [email-workflow](./email-workflow) | IMAP EXAMINE 모드로 이메일을 읽고, 로컬 LLM(Ollama) 또는 키워드 규칙으로 분류하는 CLI 도구 | Python |
| [local-feed-relevance-engine](./local-feed-relevance-engine) | 로컬 임베딩(all-MiniLM-L6-v2)으로 RSS 피드 기사의 관심도를 스코어링하고, 읽기/스킵 피드백으로 개인화하는 엔진 | Python |
| [lora-streaming-merge](./lora-streaming-merge) | 16GB RAM 환경에서 safetensors lazy loading을 활용한 텐서 단위 스트리밍 LoRA 머지 CLI | Python |
| [oncall-gap-predetector](./oncall-gap-predetector) | Docker Compose + Prometheus config 정적 분석으로 모니터링 사각지대를 자동 탐지하는 CLI 도구 | Python |
| [proactive-alert-digest](./proactive-alert-digest) | YAML 설정만으로 멀티소스 모니터링 → "오늘 아침에 뭘 봐야 하는지" 한 장짜리 다이제스트 생성 | Python |

---

**Total: 49 prototypes** | Auto-updated by prototype-pipeline

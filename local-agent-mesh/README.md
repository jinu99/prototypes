# Local Agent Mesh

> 소형/대형 LLM 간 복잡도 기반 스마트 라우팅 + self-delegation CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (main.py)                           │
│                    ask "prompt" / demo                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AgentMesh (mesh.py)                            │
│                  오케스트레이션 파이프라인                            │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ ComplexityRouter  │    │   ModelClient     │                   │
│  │   (router.py)     │    │   (models.py)     │                   │
│  │                   │    │                   │                   │
│  │ TF-IDF Vectorizer │    │ Ollama REST API   │                   │
│  │ + LogisticRegress │    │ (mock fallback)   │                   │
│  │ + Keyword Heurist │    └────────┬──────────┘                   │
│  └────────┬─────────┘             │                              │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    처리 흐름 (Process)                       │ │
│  │                                                            │ │
│  │  Prompt ──▶ 복잡도 분류 ──┬──▶ COMPLEX ──▶ 대형 모델 생성   │ │
│  │                          │                    │            │ │
│  │                          │                    ▼            │ │
│  │                          │              최종 응답 반환      │ │
│  │                          │                                 │ │
│  │                          └──▶ SIMPLE ──▶ 소형 모델 생성     │ │
│  │                                              │             │ │
│  │                                              ▼             │ │
│  │                                   ┌───────────────────┐    │ │
│  │                                   │ Self-Evaluation    │    │ │
│  │                                   │ (confidence.py)    │    │ │
│  │                                   │                    │    │ │
│  │                                   │ • Hedging 언어 감지 │    │ │
│  │                                   │ • 응답 길이 평가    │    │ │
│  │                                   │ • 완성도 마커 체크  │    │ │
│  │                                   │ • 코드 블록 품질    │    │ │
│  │                                   └────────┬──────────┘    │ │
│  │                                            │               │ │
│  │                              ┌─────────────┴──────────┐    │ │
│  │                              │                        │    │ │
│  │                     confidence ≥ 0.6          confidence    │ │
│  │                              │                 < 0.6       │ │
│  │                              ▼                    │        │ │
│  │                        응답 ACCEPT                ▼        │ │
│  │                                          ⚡ ESCALATE       │ │
│  │                                         대형 모델 재생성    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Display (display.py)                          │
│              ANSI 터미널 출력 — Pipeline 시각화                    │
└─────────────────────────────────────────────────────────────────┘
```

**데이터 흐름 요약:**

1. **입력** → CLI에서 prompt 수신
2. **라우팅** → TF-IDF + keyword heuristic + 길이 분석으로 복잡도 score 산출 (threshold: 0.5)
3. **생성** → Ollama REST API로 모델 호출 (미설치 시 deterministic mock fallback)
4. **평가** → simple 라우팅 시에만 self-evaluation 수행 (4가지 heuristic signal 종합)
5. **에스컬레이션** → confidence < 0.6이면 대형 모델로 재생성
6. **출력** → Pipeline trace + 최종 응답을 ANSI 컬러로 렌더링

## Demo

**단일 요청 처리:**

```bash
$ uv run python main.py ask "What is Python and why is it popular?"

════════════════════════════════════════════════════════════
  LOCAL AGENT MESH
════════════════════════════════════════════════════════════

📝 Prompt: What is Python and why is it popular?

─── Pipeline ───
  🔀 ROUTE [qwen2.5:0.5b] — simple (score: 0.12)  (2ms)
  🤖 GENERATE [qwen2.5:0.5b] — 34 tokens  (112ms)
  🔍 SELF_EVAL [qwen2.5:0.5b] — confidence: 0.88  (1ms)
────────────────────────────────────

  Complexity: SIMPLE (score: 0.12)
  Routed to: qwen2.5:0.5b
  Confidence: 0.88 (heuristic)

  ✓ ACCEPTED — Final model: qwen2.5:0.5b

  Total time: 115ms

─── Response ───

Python is a high-level, interpreted programming language known
for its readable syntax and versatility...

════════════════════════════════════════════════════════════
```

**에스컬레이션 발생 시나리오:**

```bash
$ uv run python main.py ask "Why do some technology startups succeed while the vast majority fail?" -v

─── Pipeline ───
  🔀 ROUTE [qwen2.5:0.5b] — simple (score: 0.38)  (2ms)
  🤖 GENERATE [qwen2.5:0.5b] — 29 tokens  (105ms)
  🔍 SELF_EVAL [qwen2.5:0.5b] — confidence: 0.48  (1ms)
  ⚡ ESCALATE [qwen2.5:7b] — confidence 0.48 < threshold 0.6  (820ms)

  Complexity: SIMPLE (score: 0.38)
  Confidence: 0.48 (heuristic)

  ⚡ ESCALATED → Re-generated with qwen2.5:7b
```

**전체 데모 실행 (5개 시나리오):**

```bash
$ uv run python main.py demo

============================================================
  LOCAL AGENT MESH — DEMO  [MOCK MODE]
  Small: qwen2.5:0.5b | Large: qwen2.5:7b
  Confidence threshold: 0.6
============================================================

▶ Scenario 1/5: Simple summary (should stay on small model)
  ...✓ ACCEPTED

▶ Scenario 2/5: Simple Q&A (should stay on small model)
  ...✓ ACCEPTED

▶ Scenario 3/5: Complex code (should route directly to large model)
  ...✓ ACCEPTED (direct to large)

▶ Scenario 4/5: Reasoning task — escalation expected
  ...⚡ ESCALATED → qwen2.5:7b

▶ Scenario 5/5: Complex reasoning (should route to large model)
  ...✓ ACCEPTED (direct to large)

============================================================
  DEMO SUMMARY
============================================================
  Total scenarios:         5
  Small model accepted:    2
  Escalated to large:      1
  Direct to large:         2
  Large model calls saved: 2/5 (40%)
============================================================
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 단일 요청
uv run python main.py ask "Summarize the benefits of renewable energy"

# 전체 데모 (5개 시나리오)
uv run python main.py demo

# 상세 출력
uv run python main.py demo -v

# 옵션
uv run python main.py --help
```

## 아키텍처

```
요청 → [복잡도 분류기] → simple → [소형 모델] → [self-eval]
           │                                        │
           │                              confidence ≥ 0.6 → 응답 반환
           │                              confidence < 0.6 → [대형 모델] → 응답 반환
           │
           └──→ complex → [대형 모델] → 응답 반환
```

**핵심 메커니즘:**

1. **복잡도 라우팅** (`router.py`): TF-IDF + 키워드 heuristic으로 요청 복잡도 분류
2. **모델 생성** (`models.py`): Ollama REST API 클라이언트 (미설치 시 mock fallback)
3. **Self-evaluation** (`confidence.py`): hedging 언어, 응답 길이, 완성도 기반 신뢰도 평가
4. **오케스트레이션** (`mesh.py`): 라우팅 → 생성 → 평가 → 에스컬레이션 파이프라인

## 구조

```
local-agent-mesh/
├── main.py              # CLI 진입점 (ask, demo 커맨드)
├── agent_mesh/
│   ├── __init__.py
│   ├── models.py        # Ollama 클라이언트 + mock fallback
│   ├── router.py        # TF-IDF 복잡도 분류기
│   ├── confidence.py    # Self-evaluation 신뢰도 평가
│   ├── mesh.py          # 오케스트레이션 파이프라인
│   └── display.py       # ANSI 터미널 출력
├── pyproject.toml
├── BUILD_LOG.md         # 빌드 일지
├── STATUS.md            # 검증 결과
└── README.md
```

## 데모 시나리오

| # | 유형 | 라우팅 | 결과 |
|---|------|--------|------|
| 1 | 간단한 요약 | simple → small | 소형 모델에서 처리 완료 |
| 2 | 간단한 Q&A | simple → small | 소형 모델에서 처리 완료 |
| 3 | 복잡한 코드 | complex → large | 대형 모델로 직행 |
| 4 | 추론 과제 | simple → small → **escalate** | 소형 시도 → 자신감 부족 → 대형 에스컬레이션 |
| 5 | 복잡한 설계 | complex → large | 대형 모델로 직행 |

## Ollama 연동

Ollama가 로컬에서 실행 중이면 자동으로 감지하여 실제 모델을 사용합니다:

```bash
# Ollama 설치 후
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:7b
ollama serve

# 실제 모델로 실행
uv run python main.py demo
```

## 원본
prototype-pipeline spec: local-agent-mesh

---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Local Agent Mesh

> 소형/대형 LLM 간 복잡도 기반 스마트 라우팅 + self-delegation CLI 도구

**카테고리**: AI/LLM Orchestration
**스택**: Python, scikit-learn, Ollama REST API, uv
**날짜**: 2026-03-03

<!--
요즘 로컬 LLM 돌리는 사람이 꽤 많아졌다. Ollama 깔면 모델 여러 개 쉽게 쓸 수 있는데, 문제는 어떤 질문을 어떤 모델에 보내야 하는지를 사람이 매번 판단해야 한다는 거다. 간단한 질문도 큰 모델로 보내고, GPU 시간을 낭비한다. 이걸 자동화할 수 있는지가 이 프로토타입의 핵심 질문이다.
-->

---

# Background

- Ollama 등으로 **로컬에서 여러 LLM을 동시 운용**하는 개발자가 빠르게 늘고 있다
- 그런데 모델 간 작업 분배에 **표준화된 방법이 없다**
  - 간단한 요약/분류 작업까지 대형 모델로 보내 GPU 자원과 시간을 낭비
  - 에이전트가 **자신의 한계를 인식해 더 큰 모델에 위임**하는 메커니즘이 부재
- MCP는 도구 호출에는 효과적이지만 에이전트 간 통신에는 설계상 부적합
- Google A2A 같은 새 프로토콜은 클라우드/엔터프라이즈 중심이라 로컬 환경에 바로 적용하기 어렵다

<!--
로컬 LLM 생태계가 빠르게 커지고 있다. Ollama 하나로 qwen, llama, mistral 같은 모델을 노트북에서 바로 돌릴 수 있게 됐다. 근데 모델이 여러 개 있어도 "이 질문은 어디로 보내지?"라는 판단은 여전히 사람 몫이다. MCP나 A2A 같은 프로토콜이 나오고 있지만, 하나는 도구 호출 전용이고 하나는 엔터프라이즈용이라 로컬 환경에서 바로 쓰기 어렵다. 결국 로컬 멀티 모델 환경에는 아직 오케스트레이션 공백이 있다.
-->

---

# Pain Point

커뮤니티에서 반복적으로 나오는 고통들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/LocalLLaMA | ⭐⭐ | 서로 다른 LLM 간 **통신 프로토콜이 표준화되지 않아** 수동 HTTP 연결에 의존 |
| 2 | Hacker News | ⭐⭐⭐ | MCP가 도구 호출에는 잘 동작하지만 **에이전트 간 통신에는 설계상 부적합** |
| 3 | r/LocalLLaMA | ⭐⭐⭐ | 간단한 요청까지 비싼 프론티어 모델로 보내 **API 비용/GPU 시간이 과다** |

결국 이건 두 가지 문제다:
1. **라우팅 문제** — 어떤 질문을 어떤 모델에 보낼 것인가
2. **위임 문제** — 모델이 스스로 "나는 이걸 못하겠다"고 판단할 수 있는가

<!--
커뮤니티에서 이런 얘기가 계속 나온다. 로컬 LLM 여러 개 띄워놓으면 좋은데, 어떤 모델에 뭘 보내야 할지 모르겠다는 거다. 간단한 요약까지 70B 모델로 보내면 GPU가 아깝고, 그렇다고 소형 모델이 복잡한 코드를 짜면 품질이 떨어진다. 결국 두 가지 문제로 수렴한다. 하나는 라우팅, 즉 적합한 모델을 자동으로 고르는 것. 다른 하나는 위임, 소형 모델이 자기 응답을 보고 "이건 내 능력 밖이다"라고 인정하는 것. 이 두 개를 같이 풀어야 의미가 있다.
-->

---

# Solution

**한 줄 요약**: 요청 복잡도를 자동 분류하고, 소형 모델이 스스로 한계를 인식해 대형 모델에 에스컬레이션하는 경량 CLI

### 기존 솔루션과 뭐가 다른가

| 기존 도구 | 한계 | 우리 접근 |
|-----------|------|----------|
| RouteLLM / LiteLLM | 클라우드 API 중심, 라우팅만 | **로컬 전용** + self-delegation 결합 |
| Google A2A | 엔터프라이즈/클라우드 중심 | **CLI 경량 도구**, 로컬에서 바로 동작 |
| LangGraph / CrewAI | 무거운 프레임워크 | **프레임워크 비종속**, scikit-learn 하나로 충분 |

**검증 목표**: 스마트 라우팅 + self-delegation으로 대형 모델 호출을 유의미하게 줄일 수 있는가

<!--
접근법은 꽤 단순하다. 요청이 들어오면 TF-IDF 기반 분류기가 복잡도를 판별해서 적합한 모델로 라우팅한다. 여기까지는 RouteLLM이랑 비슷한데, 차이점은 소형 모델이 응답을 생성한 후에 self-evaluation을 한다는 거다. confidence가 낮으면 자동으로 대형 모델에 에스컬레이션한다. 기존 도구들이 라우팅 또는 오케스트레이션 중 하나만 해결하는 반면, 이건 둘 다 경량 CLI 하나에 넣었다. 프레임워크 종속도 없다.
-->

---

# Architecture

```
요청 → [복잡도 분류기] → simple → [소형 모델] → [self-eval]
           │                                        │
           │                              confidence ≥ 0.6 → 응답 반환
           │                              confidence < 0.6 → [대형 모델] → 응답 반환
           │
           └──→ complex → [대형 모델] → 응답 반환
```

| 모듈 | 역할 |
|------|------|
| `router.py` | TF-IDF + 키워드 heuristic으로 복잡도 score 산출 (threshold: 0.5) |
| `models.py` | Ollama REST API 클라이언트. 미설치 시 deterministic mock fallback |
| `confidence.py` | hedging 언어 감지, 응답 길이, 완성도 마커 등 4가지 signal로 confidence 평가 |
| `mesh.py` | 라우팅 → 생성 → 평가 → 에스컬레이션 파이프라인 오케스트레이션 |

<!--
아키텍처는 네 개 모듈로 구성된다. router가 TF-IDF와 키워드 heuristic을 조합해서 복잡도 점수를 매긴다. 0.5 이상이면 complex로 분류해서 대형 모델로 직행하고, 미만이면 소형 모델이 먼저 처리한다. 소형 모델이 응답을 생성하면 confidence.py가 네 가지 signal을 종합해서 자신감을 평가한다. hedging 언어가 있는지, 응답이 너무 짧은지, 미완성 마커가 있는지, 코드 블록이 온전한지. 이 점수가 0.6 미만이면 대형 모델로 에스컬레이션한다. mesh.py가 이 전체 흐름을 오케스트레이션한다.
-->

---

# Demo

**소형 모델에서 처리 완료 (간단한 질문)**
```
📝 Prompt: What is Python and why is it popular?
─── Pipeline ───
  🔀 ROUTE [qwen2.5:0.5b] — simple (score: 0.12)  (2ms)
  🤖 GENERATE [qwen2.5:0.5b] — 34 tokens  (112ms)
  🔍 SELF_EVAL [qwen2.5:0.5b] — confidence: 0.88  (1ms)
  ✓ ACCEPTED — Final model: qwen2.5:0.5b    Total: 115ms
```

**에스컬레이션 발생 (소형 모델이 한계 인식)**
```
📝 Prompt: Why do some technology startups succeed while the vast majority fail?
─── Pipeline ───
  🔀 ROUTE [qwen2.5:0.5b] — simple (score: 0.38)  (2ms)
  🤖 GENERATE [qwen2.5:0.5b] — 29 tokens  (105ms)
  🔍 SELF_EVAL [qwen2.5:0.5b] — confidence: 0.48  (1ms)
  ⚡ ESCALATE [qwen2.5:7b] — confidence 0.48 < threshold 0.6
```

<!--
데모를 보면 두 가지 시나리오가 명확하게 구분된다. "Python이 뭐야"라는 간단한 질문은 소형 모델이 confidence 0.88로 처리하고 끝난다. 115밀리초. 반면에 "스타트업이 왜 성공하고 실패하는가"라는 질문은 소형 모델이 시도는 하는데, self-eval에서 confidence 0.48이 나온다. 임계값 0.6보다 낮으니까 자동으로 대형 모델로 에스컬레이션된다. 이 과정이 파이프라인에 투명하게 표시된다는 게 핵심이다. 사용자가 왜 이 모델이 선택됐는지 다 볼 수 있다.
-->

---

# Key Decisions & Lessons

### 기술 판단

1. **TF-IDF + Logistic Regression 선택** — 복잡도 분류에 LLM을 쓰지 않고 scikit-learn만 사용. 외부 서비스 의존 없이 2ms 안에 분류 완료. 24개 학습 예제로도 충분히 동작

2. **Heuristic 기반 confidence 평가** — 실제 Ollama 없이도 동작하도록 hedging 언어 감지 + 응답 길이 + 완성도 마커 등 4가지 signal 조합. Ollama가 있으면 self-evaluation prompt 방식으로 자동 전환

3. **Mock fallback 설계** — Ollama REST API와 동일한 인터페이스를 유지하면서 mock 구현. 설치 없이 데모 가능하면서 실제 모델 연동 시 코드 변경 zero

### 심의 점수
| 항목 | 점수 |
|------|------|
| 문제 진정성 | 3.7/5 |
| 프로토타입 적합성 | 2.7/5 |
| 신선도 | 3.3/5 |
| **학습 가치** | **4.7/5** |

<!--
기술 판단 세 가지가 꽤 중요했다. 첫째, 복잡도 분류에 LLM을 안 쓰고 TF-IDF를 쓴 건 의도적이다. 라우터가 느리면 라우팅의 의미가 없다. 24개 학습 데이터로 2ms 안에 분류가 끝난다. 둘째, confidence 평가를 heuristic으로 만든 건 Ollama 없는 환경에서도 동작하게 하려는 목적이었다. 실제로는 self-evaluation prompt가 더 정확하겠지만, 프로토타입 단계에서는 이걸로 충분하다. 셋째, mock fallback을 실제 API와 동일한 인터페이스로 만들어서 전환 비용을 zero로 뒀다. 심의에서 학습 가치가 4.7로 가장 높았는데, 만들어보니 납득이 간다. 라우팅과 self-evaluation을 직접 구현하면서 배우는 게 꽤 있었다.
-->

---

# Results & Future

### 성과

- 완료 기준 **5/5 통과** — 라우팅, self-evaluation, 에스컬레이션, 투명한 표시, 데모 시나리오
- 5개 데모 시나리오: 소형 모델 처리 2건 + 에스컬레이션 1건 + 대형 직행 2건
- 대형 모델 호출 절감: **5건 중 2건(40%)** 소형 모델에서 처리 완료

### 한계

- Mock 기반이라 실제 모델의 품질 차이를 정량적으로 입증하지 못함
- 학습 데이터 24개로 분류기의 일반화 성능이 제한적
- 단일 요청 처리만 지원, 대화 맥락(multi-turn) 미고려

### 프로덕트가 되려면

- Ollama 실제 연동 + 대형/소형 모델 간 응답 품질 A/B 비교
- 라우팅 분류기를 소형 LLM 기반으로 교체 (semantic understanding 확보)
- 에이전트 메시 프로토콜 구현 (JSON-RPC 기반 에이전트 간 통신)
- multi-turn 대화에서 복잡도가 변하는 경우의 동적 라우팅

<!--
결과적으로 완료 기준은 다 통과했다. 5개 시나리오에서 40%를 소형 모델이 처리했다는 건, 라우팅과 self-delegation이 동작한다는 증거다. 솔직히 아쉬운 점도 있다. mock 기반이라 "진짜 소형 모델이 잘 판단하는가"에 대한 정량적 답은 못 냈다. 분류기 학습 데이터도 24개라 실제 환경에서는 더 필요하다. 프로덕트로 가려면 실제 Ollama 연동 후 품질 비교가 먼저고, 분류기를 소형 LLM 기반으로 바꿔서 semantic understanding을 확보해야 한다. 그리고 에이전트 메시 프로토콜, 즉 에이전트 간 통신까지 가야 진짜 "mesh"라고 부를 수 있을 거다.
-->

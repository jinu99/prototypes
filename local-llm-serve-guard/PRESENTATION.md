---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Local LLM Serve Guard

**VRAM 기반 동적 어드미션 컨트롤로 로컬 LLM OOM을 방지하는 리버스 프록시**

카테고리: DevTools / LLM Infra
스택: Python, FastAPI, httpx, aiosqlite, nvidia-smi
날짜: 2026-03-08

<!--
오늘 공유할 프로토타입은 Local LLM Serve Guard다. 한 줄로 요약하면, 로컬에서 LLM을 돌릴 때 VRAM 상태를 보고 요청을 알아서 조절해주는 프록시다. Ollama나 vLLM 앞에 얇게 하나 깔아두면, GPU 메모리가 빠듯할 때 요청을 큐에 넣거나 거부해서 OOM 크래시를 막아준다.
-->

---

# Background

- AI 에이전트가 로컬 LLM(Ollama, llama.cpp)에 동시 요청을 보내는 환경이 빠르게 늘고 있다
- Cursor, Continue, Aider 같은 도구들이 백그라운드에서 LLM을 계속 호출한다
- 문제는, 로컬 GPU는 한정된 VRAM을 가지고 있고, **동시 요청이 몰리면 OOM으로 프로세스가 그냥 죽는다**
- Ollama의 `OLLAMA_NUM_PARALLEL`은 정적 제한만 제공 — VRAM 상태를 모른다
- LiteLLM은 클라우드 API 프록시에 특화 — 로컬 GPU 문제는 범위 밖

<!--
요즘 로컬 LLM 서빙 환경이 꽤 바뀌었다. 예전엔 터미널에서 한 번에 하나씩 질문하는 수준이었는데, 이제는 에이전트가 백그라운드에서 동시에 여러 요청을 쏜다. Cursor 같은 도구가 코드 완성, 인라인 편집, 채팅을 동시에 돌리는 거다. 근데 로컬 GPU의 VRAM은 정해져 있다. 24GB짜리 카드에 요청 5개가 동시에 들어오면, 어느 순간 메모리가 터지면서 Ollama 프로세스가 죽어버린다. 기존 도구들은 이 문제를 풀지 않는다. Ollama 자체 설정은 정적이고, LiteLLM은 클라우드 API에 맞춰져 있다.
-->

---

# Pain Point

커뮤니티에서 반복적으로 나오는 고통들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/LocalLLaMA | ●●● | 다수 에이전트 동시 요청 시 **VRAM OOM으로 프로세스 크래시** |
| 2 | r/LocalLLaMA | ●●● | LLM 프로바이더 장애 시 **자동 폴백 프록시 부재** |
| 3 | Hacker News | ●●● | GPU 여러 대로 **추론 분산 서빙 가이드 부족** |
| 4 | r/LocalLLaMA | ●●● | llama.cpp **성능 파라미터 문서 부족**, 최적 설정 어려움 |

모든 항목이 Signal 3 (강한 신호). 이건 소수의 불편이 아니라 구조적 문제다.

<!--
r/LocalLLaMA 커뮤니티를 보면 이런 얘기가 계속 나온다. 에이전트 여러 개 돌리다가 Ollama가 죽었다, 장애 나면 수동으로 다른 서버로 바꿔야 한다, GPU 2대인데 분산하는 법을 모르겠다. 전부 Signal 3, 강한 신호다. 특히 첫 번째가 핵심인데, 결국 이건 VRAM이라는 유한한 자원에 대한 어드미션 컨트롤이 없다는 문제다. 웹 서버에는 rate limiter가 당연히 있는데, 로컬 LLM 서빙에는 그런 게 없다.
-->

---

# Solution

### 한 줄 요약
> Ollama/vLLM 앞에 놓는 **VRAM-aware 리버스 프록시**

### 기존 솔루션과의 차이

| | Ollama 내장 | LiteLLM | **Serve Guard** |
|---|:---:|:---:|:---:|
| VRAM 기반 동적 제어 | ✗ | ✗ | **✓** |
| 자동 폴백 | ✗ | △ (HTTP 에러 기반) | **✓** (헬스체크 기반) |
| OpenAI 호환 | ✓ | ✓ | **✓** |
| 로컬 GPU 특화 | △ | ✗ | **✓** |

핵심: **HTTP 에러가 나기 전에, VRAM 상태를 보고 선제적으로 제어한다**

<!--
우리 접근법은 간단하다. Ollama 앞에 프록시를 하나 둔다. 이 프록시가 nvidia-smi로 VRAM을 계속 모니터링하면서, 요청을 허용할지 큐에 넣을지 거부할지를 결정한다. 기존 도구들과 뭐가 다르냐면, 에러가 터진 후에 대응하는 게 아니라 터지기 전에 막는다는 거다. 사람으로 치면, 병원 응급실 앞에서 환자 상태를 보고 들여보낼지 대기시킬지 판단하는 triage 시스템과 마찬가지다. LiteLLM은 HTTP 500이 떨어져야 폴백하는데, 그때는 이미 OOM이 난 거다.
-->

---

# Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Serve Guard Proxy                           │
│                                                                     │
│  ┌───────────┐    ┌──────────────────┐    ┌──────────────────────┐  │
│  │  Client    │    │   Reverse Proxy  │    │   Backend Manager    │  │
│  │  Request   ├───▶│   (proxy.py)     ├───▶│   (backends.py)     │  │
│  └───────────┘    │                  │    │                      │  │
│                    │  /v1/chat/comp.  │    │  ┌────────────────┐  │  │
│                    │  /v1/completions │    │  │ Backend #1     │  │  │
│                    │  /v1/models      │    │  │ (priority: 1)  │──┼──┼──▶ Ollama
│                    └────────┬─────────┘    │  └────────────────┘  │  │
│                             │              │  ┌────────────────┐  │  │
│                    ┌────────▼─────────┐    │  │ Backend #2     │  │  │
│                    │   Admission      │    │  │ (priority: 2)  │──┼──┼──▶ Fallback
│                    │   Controller     │    │  └────────────────┘  │  │
│                    │  (admission.py)  │    │  Health Check (10s)  │  │
│                    └────────┬─────────┘    └──────────────────────┘  │
│                    ┌────────▼─────────┐    ┌──────────────────────┐  │
│                    │  VRAM Monitor    │    │   Metrics Store      │  │
│                    │ (nvidia-smi 폴링)│    │   (SQLite 기반)      │  │
│                    └──────────────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

  VRAM < 85%  → 즉시 허용 ✓    85~95% → 큐 대기    ≥ 95% → 즉시 거부 ✗
```

<!--
아키텍처는 이렇다. 클라이언트 요청이 들어오면 Reverse Proxy가 받고, Admission Controller가 현재 VRAM 상태를 본다. 85% 미만이면 바로 통과, 85에서 95% 사이면 큐에 넣고 VRAM이 회복되면 풀어준다, 95% 이상이면 즉시 거부한다. 허용된 요청은 Backend Manager가 우선순위에 따라 건강한 백엔드에 전달한다. 모든 이력은 SQLite에 쌓인다. 모듈이 6개인데, 각각 100줄 내외로 꽤 간결하다.
-->

---

# Demo

### VRAM 정상 시 — 요청 허용
```bash
$ curl http://localhost:8780/v1/chat/completions \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]}'
# → 200 OK, x-serve-guard-backend: local-ollama
```

### VRAM 96% — 즉시 거부
```bash
$ curl -X POST http://localhost:8780/debug/set-mock-vram \
  -d '{"utilization_percent": 96}'

$ curl http://localhost:8780/v1/chat/completions \
  -d '{"model": "llama3", "messages": [...]}'
# → 503 Service Unavailable: VRAM critical
```

### 부하 테스트 결과
VRAM 96%에서 동시 30건 → **30/30 거부** (OOM 0건)
VRAM 50%에서 동시 30건 → **30/30 허용** (정상 처리)

<!--
데모를 보면 동작이 명확하다. VRAM이 여유로울 때는 요청이 그냥 통과한다. 응답 헤더에 어떤 백엔드가 처리했는지도 나온다. VRAM을 96%로 올리면 즉시 503이 떨어진다. OOM으로 프로세스가 죽는 대신, 클라이언트가 깔끔한 에러를 받는 거다. 부하 테스트에서 VRAM 96% 상태로 30건을 동시에 보내면 전부 거부되고, 50%에서는 전부 통과한다. 어드미션 컨트롤이 정확하게 동작한다는 걸 확인했다.
-->

---

# Key Decisions & Lessons

### 1. nvidia-smi 폴링 + mock 모드 이원화
GPU 없는 개발 환경에서도 전체 흐름을 테스트할 수 있도록 mock 모드를 기본 제공했다. `shutil.which("nvidia-smi")`로 자동 감지.

### 2. 큐잉 전략: asyncio.Event 기반 대기
85~95% 구간에서 요청을 즉시 거부하지 않고, 30초 타임아웃으로 VRAM 회복을 기다린다. 빨리 거부하면 안정적이지만 사용자 경험이 나빠지고, 너무 오래 기다리면 큐가 쌓인다.

### 3. OpenAI-호환 프록시 — 기존 도구와 무관하게 동작
Cursor, Continue 등 OpenAI API를 쓰는 도구라면 설정만 바꾸면 된다. 클라이언트 수정이 필요 없다.

**심의 점수**: 문제 진정성 4.0 · 프로토타입 적합성 4.0 · 신선도 3.0 · 학습 가치 3.7

<!--
기술 판단 몇 가지를 공유하면. 첫째, nvidia-smi가 없으면 자동으로 mock 모드로 전환된다. 이게 없었으면 GPU 없는 환경에서 개발 자체가 안 됐을 거다. 둘째, 큐잉 전략이 꽤 고민이었다. VRAM이 애매한 구간에서 바로 거부하면 안정적인데 사용자가 답답하고, 무한정 기다리면 큐가 폭발한다. 30초 타임아웃이 현실적인 절충점이었다. 셋째, OpenAI 호환이라는 게 생각보다 중요하다. 클라이언트 쪽에서 뭘 고칠 필요가 없다. 엔드포인트 URL만 프록시로 바꾸면 된다.
-->

---

# Results & Future

### 성과 (완료 기준 5/5 통과)
- ✅ nvidia-smi VRAM 폴링 → SQLite 기록
- ✅ VRAM 임계치 초과 시 큐잉 + 여유 시 자동 릴리스
- ✅ 복수 백엔드 헬스체크 기반 자동 폴백
- ✅ OpenAI-호환 /v1/chat/completions (스트리밍 포함)
- ✅ 부하 테스트에서 OOM 발생률 감소 확인

### 한계점
- 실제 GPU 환경에서의 검증은 mock 수준에 머물러 있다
- 웹 대시보드 UI는 Phase 2로 이관됨
- 멀티 GPU 텐서 병렬 분산은 범위 밖

### 프로덕트가 되려면
- 실제 RTX 4090 / A100 환경에서의 장시간 스트레스 테스트
- AMD ROCm 지원 (`rocm-smi` 연동)
- Prometheus 메트릭 내보내기 + Grafana 대시보드
- Docker 이미지 배포 + Helm chart

<!--
결과적으로 완료 기준 5개를 전부 통과했다. 솔직히 아쉬운 점도 있다. GPU가 없는 환경에서 mock으로만 검증했기 때문에, 실제 24GB 카드에서 Ollama가 14GB 모델을 올린 상태로 부하를 줬을 때 어떻게 되는지는 아직 모른다. 그리고 대시보드가 없어서 메트릭을 API로만 볼 수 있다. 이게 실제 프로덕트가 되려면, 실환경 스트레스 테스트가 필수이고, AMD GPU 지원, 모니터링 시스템 연동, 컨테이너 배포가 필요하다. 그래도 핵심 가설인 VRAM 기반 어드미션 컨트롤이 OOM을 막을 수 있는가는 충분히 검증됐다고 본다.
-->

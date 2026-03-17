---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Local Coding Agent Stabilizer

> 로컬 LLM 코딩 에이전트의 파괴적 파일 편집을 실시간 감지·차단하는 OpenAI-호환 프록시 미들웨어

**카테고리**: Developer Tools / AI Safety
**스택**: Python, FastAPI, SQLite, SSE Streaming
**날짜**: 2026-03-15

<!--
로컬 LLM으로 코딩 에이전트를 돌리면 파일을 날려먹는 문제가 있다. 이걸 프록시 레벨에서 잡아주는 미들웨어를 만들었다. 오늘은 왜 이걸 만들었고, 어떻게 동작하는지 얘기하겠다.
-->

---

## Background

- 클라우드 AI 코딩 도구(Claude Code, Cursor 등)에 대한 **벤더 종속 리스크**가 현실화
  - 이유 불명 계정 밴, 서비스 중단, 가격 인상
- 로컬 LLM 기반 코딩 에이전트(Aider+Ollama, continue.dev 등)로의 **전환 수요 급증**
- 그런데 로컬 모델은 클라우드 모델만큼 안정적이지 않다
  - 양자화된 모델이 도구 호출을 잘못하고, 파일을 통째로 날리고, 무한 루프에 빠진다
- 기존 에이전트 프레임워크에는 이런 **런타임 안전장치가 없다**

<!--
요즘 로컬 LLM으로 코딩하려는 수요가 꽤 많다. 클라우드 서비스가 갑자기 계정을 밴하거나, 가격을 올리거나, 서비스가 중단되는 경험을 하면 당연히 로컬로 눈이 간다. 문제는 로컬 모델이 아직 도구 호출을 안정적으로 못 한다는 거다. Qwen이든 CodeLlama든, 양자화하면 tool calling 품질이 확 떨어진다. 파일을 삭제하라고 안 했는데 삭제하고, 같은 편집을 무한 반복하고. 기존 에이전트 프레임워크는 이런 걸 런타임에 잡아주는 계층이 없다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 고통들:

| # | 출처 | Signal | 내용 |
|---|------|:------:|------|
| 1 | r/LocalLLaMA | ⬤⬤⬤ | 클라우드 AI 코딩 도구 계정 밴으로 업무 중단, 셀프호스팅 대안 부재 |
| 2 | r/LocalLLaMA | ⬤⬤⬤ | 로컬 AI 코딩 도구가 느리고, 멈추고, **파일 내용을 삭제** |
| 3 | r/LocalLLaMA | ⬤⬤⬤ | 로컬 양자화 LLM이 tool calling 시 **무한 루프**에 빠짐 |
| 4 | GitHub Trending | ⬤⬤⬤ | 터미널 전용 에이전트의 IDE GUI 통합 어려움 |

> 4개 signal 모두 강도 3/3. 실제 사용자가 겪고 있는 문제.

<!--
레딧 LocalLLaMA 서브레딧을 보면 이런 얘기가 계속 나온다. continue.dev가 파일 내용을 날렸다, Aider가 같은 편집을 반복한다, 양자화 모델이 도구를 우회한다. signal strength가 전부 3으로 나왔는데, 이건 실제로 겪는 사람이 많다는 뜻이다. 결국 로컬 LLM 코딩이 실용적이려면 이 신뢰성 문제를 풀어야 한다.
-->

---

## Solution

**한 줄 요약**: 코딩 에이전트와 LLM 사이에 프록시를 끼워서, 파괴적 도구 호출을 실행 전에 차단

### 기존 솔루션과의 차이

| 기존 | 우리 접근 |
|------|-----------|
| Cline/Aider: 프레임워크 내부 안전장치 | **프레임워크 외부** 미들웨어 — 어떤 에이전트든 적용 가능 |
| LangChain: 범용 미들웨어, 코딩 특화 없음 | **diff 분석** 기반 파일 편집 특화 감지 |
| 블로그 패턴: ad-hoc 구현 필요 | **턴키 프록시** — `OPENAI_API_BASE` 하나만 바꾸면 됨 |

<!--
접근법은 간단하다. 에이전트와 LLM 백엔드 사이에 프록시를 하나 끼운다. OpenAI-호환 API를 그대로 패스스루하되, 응답에 포함된 도구 호출을 분석해서 파괴적이면 차단한다. 핵심은 에이전트 프레임워크에 종속되지 않는다는 거다. Aider든 continue.dev든, 환경변수 하나만 바꾸면 바로 적용된다. 사람으로 치면, 의사가 처방을 내릴 때 약사가 한 번 더 확인하는 것과 마찬가지다.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Coding Agent (Aider etc.)                    │
│        OPENAI_API_BASE=http://localhost:8400/v1          │
└────────────────────────┬────────────────────────────────┘
                         │ OpenAI-compatible API Request
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 proxy.py (FastAPI :8400)                  │
│                                                          │
│   analyzer.py          loop_detector.py                  │
│   ├ File deletion       ├ Same tool 3x consecutive       │
│   ├ Empty file write    └ Per-session call tracking       │
│   ├ 80%+ code loss                                       │
│   └ Dangerous shell cmd db.py (SQLite)                   │
│                         ├ sessions / tool_calls tables   │
│   On block → ⚠️ BLOCKED └ Queried from dashboard.html   │
│   On pass  → Forward original                            │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│           LLM Backend (Ollama :11434 / Mock)             │
└─────────────────────────────────────────────────────────┘
```

<!--
구조를 보면, 에이전트가 LLM에 보내는 요청이 프록시를 거친다. 프록시 안에 두 개의 분석 모듈이 있다. analyzer.py는 도구 호출의 내용을 보고 파괴적인지 판단한다. 파일 삭제, 빈 파일 쓰기, 80% 이상 코드 소실, 위험한 쉘 명령어. loop_detector.py는 같은 도구가 3번 연속 호출되면 루프로 판정한다. 모든 이벤트는 SQLite에 기록되고, 대시보드에서 조회할 수 있다.
-->

---

## Demo

Mock 모드로 실행 — Ollama 없이도 모든 시나리오 테스트 가능:

```
🧪 Running Stabilizer Test Scenarios

=== Test 1: Normal tool call ===
  Blocked: False                                    ✅ PASS

=== Test 2: File deletion ===
  ⚠️ BLOCKED: File deletion detected: /src/main.py  ✅ PASS

=== Test 3: Empty file write ===
  ⚠️ BLOCKED: Empty file write detected: /src/utils.py  ✅ PASS

=== Test 4: Massive deletion (>80%) ===
  ⚠️ BLOCKED: Excessive deletion — 99% content removed  ✅ PASS

=== Test 5: Loop detection ===
  ⚠️ BLOCKED: tool 'edit_file' called 3x consecutively  ✅ PASS

=== Test 6: Dashboard APIs ===
  Stats: {"total_sessions":5, "total_blocked":5}     ✅ PASS

Results: 6/6 passed
```

<!--
데모는 mock 모드로 돌린다. Ollama가 없어도 모든 감지 시나리오를 테스트할 수 있게 만들었다. 정상적인 도구 호출은 통과하고, 파일 삭제, 빈 파일 쓰기, 대규모 삭제, 루프는 전부 차단된다. 6개 시나리오 전부 통과. 실제 Aider 연동도 환경변수 하나만 바꾸면 되는데, Ollama가 없어서 mock으로 대체했다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 이유 |
|------|------|
| FastAPI + httpx | SSE 스트리밍 프록시에 적합. async 기반이라 응답 지연 최소화 |
| 패턴 매칭 vs AST 분석 | AST는 프로토타입 범위 초과. 도구명 + 인자 기반 패턴 매칭으로 충분히 유효 |
| Mock 모드 포함 | Ollama 미설치 환경에서도 데모 가능 — 발표·검증에 필수 |

### 심의 점수

| 항목 | 점수 |
|------|:----:|
| 문제 진정성 (Authenticity) | 4.3/5 |
| 프로토타입 적합성 (Prototypability) | 4.0/5 |
| 신선도 (Freshness) | 3.0/5 |
| 학습 가치 (Learning Value) | 3.7/5 |
| 심의 결과 | 만장일치 승인 (3:0) |

<!--
스택 선택에서 가장 고민한 건 분석 방식이었다. AST 레벨에서 시맨틱 diff를 하면 더 정확하겠지만, 프로토타입 범위를 넘어선다. 도구 호출의 이름과 인자만 봐도 파일 삭제, 빈 쓰기, 대규모 삭제는 충분히 잡을 수 있다. 빨리 하면 틀리고, 정밀하게 하면 범위를 넘긴다. 이 둘의 균형을 패턴 매칭으로 잡았다. 그리고 mock 모드는 솔직히 처음엔 안 넣으려 했는데, Ollama 없이 데모를 보여줄 방법이 없어서 결국 넣었다. 결과적으로 이게 검증 과정을 훨씬 편하게 만들었다.
-->

---

## Results & Future

### 성과 (5/5 완료 기준 통과)

- [x] OpenAI-호환 프록시 SSE 스트리밍 패스스루
- [x] 파괴적 편집 3종 감지·차단 (삭제 / 빈 쓰기 / 80%+ 소실)
- [x] 동일 도구 연속 3회 루프 감지·세션 중단
- [x] SQLite 로그 + HTML 대시보드 조회
- [x] Aider+Ollama 데모 시나리오 (mock 검증 + 라이브 가이드)

### 한계점
- AST 레벨 시맨틱 분석 없음 — 구조적으로 의미 있는 삭제는 못 잡는다
- 프롬프트 자동 리프레이즈 미구현 — 차단만 하고 대안을 제시하지 않는다
- Ollama 실제 연동 테스트 미완 — mock 기반 검증에 의존

### 프로덕트가 되려면
- 차단 후 **자동 복구** (프롬프트 리프레이즈 → 재시도)
- **AST diff** 기반 정밀 분석 (언어별 파서 연동)
- **IDE 플러그인** 통합 (VSCode, JetBrains)
- 멀티 프로바이더 라우팅 + 모델 품질 기반 자동 전환

<!--
5개 완료 기준 전부 통과했다. 솔직히 아쉬운 건 AST 분석이 빠져 있다는 거다. 패턴 매칭으로 명백한 파괴는 잡지만, 구조적으로 의미 있는 코드를 슬쩍 날리는 건 못 잡는다. 그리고 차단만 하고 끝이라 사용자 경험이 좀 뚝뚝 끊긴다. 프로덕트가 되려면 차단 후에 프롬프트를 바꿔서 다시 시도하는 자동 복구가 있어야 한다. 결국 이 프로토타입이 검증한 건, 프록시 레벨에서 파괴적 편집을 잡는 게 기술적으로 가능하다는 거다. 이 위에 더 정밀한 분석과 자동 복구를 쌓으면 로컬 AI 코딩의 신뢰성을 꽤 끌어올릴 수 있다.
-->

---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Local LLM Quality Probe

> 소형 로컬 LLM의 실패 패턴을 한 줄 명령으로 감지하는 CLI 도구

**카테고리**: Developer Tools / LLM Ops
**스택**: Python, uv, OpenAI SDK, Rich
**날짜**: 2026-03-07

<!--
오늘은 로컬 LLM을 실무에 쓸 때 생기는 문제를 미리 잡아내는 도구를 하나 만들어 본 이야기를 해보겠다.
한 줄 명령으로 소형 로컬 모델의 품질을 진단하는 CLI, Local LLM Quality Probe다.
-->

---

## Background

- 로컬 소형 LLM(4B~9B)을 실무에 적용하려는 개발자가 급증
- Ollama, llama.cpp, vLLM 등 로컬 추론 인프라가 성숙해짐
- 그런데 이 모델들이 **에러 없이 조용히 실패**한다
  - JSON 응답이 깨지고
  - 3턴 지나면 의미 없는 텍스트를 반복하고
  - thinking 모드를 꺼도 토큰을 10배 쓴다
- 에러 로그가 없으니 원인 파악에 하루 이상 소모

<!--
요즘 로컬 LLM이 꽤 쓸 만해졌다. Ollama 한 줄이면 모델이 올라가니까, 직접 서빙해서 쓰려는 팀이 많아지고 있다.
근데 문제가 있다. 이 모델들이 조용히 실패한다. HTTP 200이 오고, 응답도 오는데, 그 응답이 틀렸다.
JSON을 달라고 했는데 닫는 괄호가 빠져 있거나, 대화 3턴 지나면 같은 말을 반복한다.
에러 로그가 없으니까 원인을 찾는 데 하루를 날리는 경우가 생긴다. 결국 이건 모델 출력 품질의 사전 검증 문제다.
-->

---

## Pain Points

커뮤니티에서 반복되는 고통들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/LocalLLaMA | ●●● | 소형 LLM(4B~9B)이 JSON 구조화 출력을 제대로 못 만든다 |
| 2 | r/LocalLLaMA | ●●● | Qwen 3.5 소형 모델이 2-3턴 후 의미 없는 텍스트를 반복 출력 |
| 3 | r/LocalLLaMA | ●●● | 로컬 LLM의 불필요한 thinking과 장황한 응답을 끄기 어렵다 |
| 4 | GeekNews | ●●● | AI 모델 적용 후 성능 안 나올 때 원인 파악이 어렵다 |

<!--
이건 내가 만들어낸 문제가 아니다. r/LocalLLaMA 커뮤니티에서 계속 나오는 이야기다.
JSON 출력이 깨진다, 멀티턴 대화가 붕괴된다, thinking을 꺼도 토큰을 쏟아낸다.
4개 출처 모두 signal strength가 높다. 사람들이 실제로 겪고 있고, 해결책을 찾고 있다는 뜻이다.
공통점이 있다. 모델이 실패하는 건 어쩔 수 없는데, 그 실패를 미리 알 방법이 없다는 거다.
-->

---

## Solution

**한 줄 요약**: 설정 없이 `llm-qual-probe http://localhost:11434` 한 줄로 소형 LLM의 알려진 실패 패턴을 즉시 진단

### 기존 도구와의 차이

| 도구 | 접근 | 한계 |
|------|------|------|
| PromptFoo | 범용 LLM 테스트 | YAML 설정 직접 작성 필요 |
| DeepEval | 50+ 메트릭 평가 | CI/CD용, 빠른 진단에 부적합 |
| LiteLLM Health Check | 인프라 가용성 | 출력 품질 미검사 |

**우리 접근**: pre-built 테스트 스위트로 **설정 제로, 실행 즉시**

<!--
기존에 PromptFoo나 DeepEval 같은 도구가 있다. 근데 이것들은 범용이다. YAML 설정을 작성하고, 테스트 케이스를 직접 만들어야 한다.
우리가 원하는 건 그게 아니다. 모델을 올려놓고 "이 모델 써도 되나?" 한 번에 확인하고 싶은 거다.
그래서 접근이 다르다. 소형 LLM의 알려진 실패 패턴만 모아서 pre-built 테스트로 만들었다. 설정 파일 없이 한 줄이면 끝난다.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                            │
│  argparse: endpoint, --model, --mock, --probes, --output        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ probe selection & execution
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  structured.py   │ │ multiturn.py │ │  efficiency.py   │
│ JSON/YAML parsing│ │ 7-turn×2 cases│ │ thinking on/off  │
│ → success/schema │ │ → repeat/forget│ │ → token compare  │
└────────┬─────────┘ └──────┬───────┘ └────────┬─────────┘
         └──────────────────┼───────────────────┘
                            ▼
              ┌──────────────────────────┐
              │  LLMClient (client.py)   │
              │  OpenAI-compatible wrapper │
              │  + built-in mock mode     │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │  Reporter (reporter.py)  │
              │  Rich terminal + JSON file │
              └──────────────────────────┘
```

<!--
구조는 단순하다. CLI가 진입점이고, 3개의 probe가 각각 독립적으로 실행된다.
structured는 JSON과 YAML 파싱을 테스트하고, multiturn은 7턴짜리 대화 2개를 자동으로 돌린다. efficiency는 thinking on/off 토큰 차이를 측정한다.
이 probe들이 전부 같은 LLMClient를 통해 OpenAI-호환 API를 호출한다. Ollama든 vLLM이든 상관없다.
mock 모드를 내장해서 실제 LLM 서버 없이도 전체 흐름을 테스트할 수 있게 했다.
-->

---

## Demo

```
$ uv run llm-qual-probe http://localhost:11434 --mock

         Probe Results
┌────────────────────┬────────┬──────────────────────────────┐
│ Probe              │ Status │ Key Metric                   │
├────────────────────┼────────┼──────────────────────────────┤
│ structured_output  │ PASS   │ Parse: 87.5% | Schema: 75%  │
│ multiturn_stability│ PASS   │ Stability: 100% (14/14 turns)│
│ output_efficiency  │ WARN   │ Thinking overhead: 80%       │
└────────────────────┴────────┴──────────────────────────────┘

Structured Output Details
  Tests: 8 | Parse OK: 7 | Schema OK: 6
  Extra fields (not in schema): 5

Output Efficiency Details
  Thinking ON tokens: 198
  Thinking OFF tokens: 110
  Overhead: 80%

╭────────────────╮
│ Overall: WARN  │
╰────────────────╯
```

<!--
실제 실행 결과를 보면, PASS, WARN, FAIL로 한눈에 상태가 보인다.
structured output은 8개 테스트 중 7개를 파싱했고, 스키마 준수율은 75%. 나머지 25%는 extra field가 끼어든 경우다.
멀티턴은 14턴 전부 안정적이었고, 효율성 쪽에서 WARN이 떴다. thinking을 켰을 때 토큰이 80% 더 나왔다.
Overall이 WARN이면 "쓸 수는 있는데 주의해라"라는 뜻이다. FAIL이 뜨면 해당 용도에는 쓰지 말라는 거다.
-->

---

## Key Decisions & Lessons

### 기술 판단

1. **Mock 모드 내장** — `--mock` 플래그로 LLM 서버 없이 전체 파이프라인 테스트 가능. 실패 패턴(JSON 깨짐, 타입 오류)을 랜덤 시뮬레이션

2. **멀티턴 mock의 함정** — 초기 mock이 3개 고정 응답만 반환 → 반복 감지가 오탐(stability 35.7%). 턴별 문맥 인식 응답으로 개선 후 92.9%

3. **Thinking 감지 실수** — thinking on/off 토큰이 동일하게 나옴. "reasoning" 키워드가 양쪽 프롬프트에 포함되어 있었다. 감지 키워드를 "show your reasoning"으로 변경하여 해결 (162 vs 43 토큰)

### 심의 점수
- 문제 진정성: **4.3/5** | 프로토타입 적합성: **4.3/5**
- 신선도: 3.5/5 | 학습 가치: 3.7/5 | 패널 만장일치 승인

<!--
만들면서 배운 것 몇 가지. mock 모드를 넣은 건 좋은 판단이었다. 프로토타입에서 실제 LLM 서버를 항상 띄워놓을 수 없으니까.
근데 mock을 너무 단순하게 만들면 오히려 문제가 된다. 처음에 고정 응답 3개로 mock을 만들었더니, 반복 감지 로직이 정상 응답을 반복이라고 잡았다.
결국 mock도 문맥을 이해해야 한다는 교훈을 얻었다.
thinking 감지도 마찬가지다. "reasoning"이라는 단어가 양쪽 프롬프트에 다 들어가 있어서 토큰 수가 같게 나왔다.
사소한 실수인데, 실제로 겪어봐야 알 수 있는 종류다.
-->

---

## Results & Future

### 성과 (4/4 완료 기준 통과)
- ✅ 한 줄 명령으로 구조화 출력 테스트 + 파싱 성공률 출력
- ✅ 14턴 자동 대화에서 붕괴 시점 감지
- ✅ thinking on/off 토큰 비교 효율성 리포트
- ✅ JSON 내보내기 + 터미널 PASS/WARN/FAIL 요약

### 한계
- 현재 pre-built 테스트만 지원, 커스텀 테스트 불가
- 모델 간 비교 기능 없음 (A vs B 랭킹)
- 실제 production 워크로드와의 상관관계 미검증

### 프로덕트가 되려면
- 커스텀 probe 플러그인 시스템
- CI/CD 통합 (exit code 기반 게이팅)
- 모델별 결과 히스토리 + 비교 대시보드
- 실제 다양한 소형 모델(Llama, Qwen, Phi)에 대한 검증 데이터 축적

<!--
완료 기준 4개를 전부 통과했다. 솔직히 프로토타입 치고는 꽤 잘 나왔다.
한계는 명확하다. 지금은 pre-built 테스트만 돌리니까, 사용자가 자기 도메인에 맞는 테스트를 추가할 수 없다.
프로덕트로 가려면 플러그인 시스템이 필요하고, CI에서 모델 교체 시 자동으로 품질 게이트를 걸 수 있어야 한다.
결국 이 도구의 본질은 "이 모델 써도 되나?"라는 질문에 30초 안에 답을 주는 것이다. 그 방향은 맞았다고 본다.
-->

# Local LLM Quality Probe

> 소형 로컬 LLM의 실패 패턴(JSON 깨짐, 멀티턴 붕괴, 과잉 출력)을 한 줄 명령으로 감지하는 CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                            │
│  argparse: endpoint, --model, --mock, --probes, --output        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ probe 선택 & 실행
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│   structured.py  │ │ multiturn.py │ │  efficiency.py   │
│                  │ │              │ │                  │
│ JSON/YAML 프롬프트│ │ 7턴×2 시나리오│ │ thinking on/off  │
│ → 파싱 성공률     │ │ → 반복 감지   │ │ + system 변형 3종 │
│ → 스키마 준수율   │ │ → 컨텍스트    │ │ → 토큰 사용량    │
│ → 필드 환각률     │ │   망각 감지   │ │   비교           │
└────────┬─────────┘ └──────┬───────┘ └────────┬─────────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            ▼
              ┌──────────────────────────┐
              │    LLMClient (client.py) │
              │                          │
              │ OpenAI-호환 API wrapper   │
              │ mock 모드: 실패 패턴 시뮬 │
              └────────────┬─────────────┘
                           │
              ┌────────────┴─────────────┐
              ▼                          ▼
    ┌──────────────────┐     ┌───────────────────┐
    │  로컬 LLM 서버    │     │   Mock 응답 생성    │
    │ (Ollama, vLLM 등) │     │ (JSON 깨짐, 타입   │
    │  /v1/chat/...     │     │  오류 등 랜덤 시뮬) │
    └──────────────────┘     └───────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │   Reporter (reporter.py) │
              │                          │
              │ Rich 터미널 테이블 출력    │
              │ + JSON 리포트 파일 저장    │
              └──────────────────────────┘
```

## Demo

```bash
# mock 모드로 전체 프로브 실행
$ uv run llm-qual-probe http://localhost:11434 --mock

Detected model: mock-model

Running LLM Quality Probe against mock-model

Running Structured Output probe...
  PASS

Running Multi-turn Stability probe...
  PASS

Running Output Efficiency probe...
  WARN

╭──────────────────────────────────────────────╮
│ LLM Quality Probe Report                     │
│ Model: mock-model                            │
╰──────────────────────────────────────────────╯

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

Multi-turn Stability Details
  No collapse detected across 14 turns

Output Efficiency Details
  Thinking ON tokens: 198
  Thinking OFF tokens: 110
  Overhead: 80%
  Most efficient config: thinking_off
  Least efficient config: thinking_on

╭────────────────╮
│ Overall: WARN  │
╰────────────────╯

JSON report saved to: report.json
```

```bash
# 특정 프로브만 실행
$ uv run llm-qual-probe http://localhost:11434 --mock -p structured

Running LLM Quality Probe against mock-model

Running Structured Output probe...
  PASS
```

```bash
# 실제 Ollama 서버 대상 실행 (모델 자동 감지)
$ uv run llm-qual-probe http://localhost:11434
Detected model: llama3.2:3b

Running LLM Quality Probe against llama3.2:3b
...
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실제 LLM 서버 대상 실행 (Ollama, llama.cpp, vLLM 등)
uv run llm-qual-probe http://localhost:11434

# mock 모드 (LLM 서버 없이 테스트)
uv run llm-qual-probe http://localhost:11434 --mock

# 특정 프로브만 실행
uv run llm-qual-probe http://localhost:11434 --mock -p structured,multiturn

# 모델 지정 + JSON 리포트 경로 지정
uv run llm-qual-probe http://localhost:11434 -m llama3.2 -o results.json
```

## 프로브

| 프로브 | 설명 |
|--------|------|
| `structured` | JSON/YAML 파싱 성공률, 스키마 준수율, 필드 환각률 측정 |
| `multiturn` | 7턴x2 자동 대화, 반복 출력 및 컨텍스트 망각 감지 |
| `efficiency` | thinking on/off 및 시스템 프롬프트 변형별 토큰 사용량 비교 |

## 구조

```
llm_qual_probe/
  cli.py           # CLI 엔트리포인트
  client.py        # OpenAI-호환 API 클라이언트 + mock 모드
  reporter.py      # Rich 터미널 리포트 + JSON 내보내기
  probes/
    structured.py  # 구조화 출력 진단
    multiturn.py   # 멀티턴 안정성 테스트
    efficiency.py  # 출력 효율성 검사
```

## 원본
prototype-pipeline spec: local-llm-qual-probe

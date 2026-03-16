# Local Agent VRAM Resource Planner

> GGUF 메타데이터 기반 멀티 모델 VRAM 예측 및 리소스 플래닝 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         입력 (Input)                            │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │  GGUF 파일   │    │  Sample Profile (내장 모델 프리셋)   │   │
│  │  (바이너리)  │    │  Llama-7B, Mixtral-8x7B, Phi-2 ...  │   │
│  └──────┬───────┘    └──────────────┬───────────────────────┘   │
└─────────┼───────────────────────────┼───────────────────────────┘
          │                           │
          ▼                           ▼
┌──────────────────┐    ┌──────────────────────────┐
│  gguf_parser.py  │    │  model_info_from_profile  │
│  ─────────────── │    │  ──────────────────────── │
│  Magic 검증      │    │  프리셋 → model_info     │
│  메타데이터 파싱 │    │  dict 변환               │
│  모델 구조 추출  │    └────────────┬─────────────┘
└────────┬─────────┘                 │
         │        ┌──────────────────┘
         ▼        ▼
┌────────────────────────────────────────────┐
│           vram_calculator.py               │
│  ──────────────────────────────────────    │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Weights  │ │ KV Cache │ │Activation │  │
│  │ 가중치×  │ │ KV heads │ │ batch ×   │  │
│  │ bpw / 8  │ │ × ctx ×  │ │ hidden ×  │  │
│  │          │ │ head_dim │ │ FP32      │  │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       └─────┬──────┘─────────────┘         │
│             ▼                              │
│  total = weights + kv + act + overhead     │
│                                            │
│  ┌─────────────────────────────────┐       │
│  │ MoE offloading (선택적)         │       │
│  │ Expert 별 VRAM/RAM 분배 시나리오│       │
│  └─────────────────────────────────┘       │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│             planner.py                     │
│  ──────────────────────────────────────    │
│  • plan_single_model  → 단일 모델 추정    │
│  • plan_multi_model   → 다중 모델 합산    │
│  • plan_grid_search   → 모델×양자화×ctx   │
│  •                      조합 필터링       │
│  • validate_against_llamacpp (검증)       │
└──────────────────┬─────────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌─────────────────┐  ┌───────────────┐
│   server.py     │  │   main.py     │
│  ───────────    │  │  ──────────   │
│  HTTP API:      │  │  CLI 모드:    │
│  /api/models    │  │  테이블 출력  │
│  /api/estimate  │  │  검증 결과    │
│  /api/multi     │  │  그리드 서치  │
│  /api/grid      │  └───────┬───────┘
│  /api/validate  │          │
│  /api/upload    │          ▼
│       │         │  ┌───────────────┐
│       ▼         │  │   Terminal    │
│  ┌──────────┐   │  │   stdout     │
│  │index.html│   │  └───────────────┘
│  │Web UI    │   │
│  └──────────┘   │
└─────────────────┘
```

## Demo

### CLI 모드

```bash
$ uv run main.py --cli
```

```
============================================================
 Local Agent VRAM Resource Planner — CLI Mode
============================================================

--- Single Model Estimates (ctx=4096) ---

  Llama 2 7B Q4_K_M
    Total: 5,422 MB | Weights: 4,531 | KV: 512 | Act: 228 | OH: 150
  Llama 2 13B Q4_K_M
    Total: 9,093 MB | Weights: 7,939 | KV: 800 | Act: 203 | OH: 150
  Mixtral 8x7B Q4_K_M [MoE]
    Total: 26,880 MB | Weights: 25,870 | KV: 128 | Act: 731 | OH: 150
  Phi-2 Q8_0
    Total: 3,356 MB | Weights: 2,910 | KV: 320 | Act: 126 | OH: 150

--- Multi-Model: Llama-7B + Phi-2 (24GB budget) ---

  Total VRAM: 8,928 MB
  Feasible: True
  Headroom: 15,648 MB

--- llama.cpp Reference Validation ---

  [PASS] Llama 2 7B Q4_K_M ctx=2048: est=4,910 ref=5,500 err=10.7%
  [PASS] Llama 2 7B Q4_K_M ctx=4096: est=5,422 ref=6,000 err=9.6%
  [PASS] Llama 2 7B Q8_0  ctx=4096: est=8,925 ref=9,200 err=3.0%
  [PASS] Llama 2 13B Q4_K_M ctx=2048: est=8,693 ref=9,000 err=3.4%

--- Grid Search: 8GB VRAM Budget ---

  12 feasible combinations found
    Phi-2 Q8_0 Q4_0 ctx=512:    1,620 MB
    Phi-2 Q8_0 Q4_K_M ctx=512:  1,648 MB
    ...
```

### 웹 UI 모드

```bash
$ uv run main.py
# → http://localhost:8000 에서 웹 UI 접속
```

**주요 API endpoints:**

| Endpoint | Method | 설명 |
|---|---|---|
| `/api/models` | GET | 사용 가능한 모델 목록 조회 |
| `/api/estimate?model=llama-7b-q4km&context=4096` | GET | 단일 모델 VRAM 추정 |
| `/api/multi` | POST | 다중 모델 동시 실행 VRAM 계산 |
| `/api/grid?budget=8192` | GET | VRAM 예산 내 실행 가능 조합 검색 |
| `/api/validate` | GET | llama.cpp 레퍼런스 대비 검증 |
| `/api/upload-gguf` | POST | GGUF 파일 업로드 후 분석 |
| `/api/quant-options` | GET | 양자화 옵션 및 context 길이 목록 |

## 실행 방법

```bash
# 의존성 설치
uv sync

# 웹 서버 실행 (http://localhost:8000)
uv run main.py

# CLI 모드
uv run main.py --cli

# 커스텀 포트
uv run main.py --port 3000
```

## 기능

- **GGUF 파서**: 바이너리 GGUF 파일에서 모델 구조 메타데이터 추출
- **VRAM 계산기**: 가중치 + KV 캐시 + 활성화 + 오버헤드 수식 기반 추정
- **멀티 모델 플래너**: 2+ 모델 동시 실행 시 총 VRAM 산출 및 실현 가능성 판단
- **그리드 서치**: 모델×양자화×컨텍스트 조합 중 VRAM 예산 내 실행 가능한 것 필터링
- **MoE 오프로딩**: Expert 수 별 VRAM/RAM 분배 시나리오 표시
- **llama.cpp 검증**: 커뮤니티 레퍼런스 값 대비 오차율 확인 (7/7 pass, ≤20%)

## 구조

```
local-agent-resource-planner/
├── main.py              # 엔트리포인트 (웹/CLI 모드)
├── gguf_parser.py       # GGUF 바이너리 파서 + 샘플 프로파일
├── vram_calculator.py   # VRAM 추정 수식 엔진
├── planner.py           # 멀티 모델 플래닝 + 그리드 서치
├── server.py            # HTTP API 서버
├── index.html           # 웹 UI (단일 HTML + vanilla JS)
├── create_test_gguf.py  # 테스트용 GGUF 파일 생성기
├── test_browser.py      # Playwright 브라우저 테스트
├── test_models/         # 생성된 테스트 GGUF 파일
├── BUILD_LOG.md         # 빌드 일지
└── STATUS.md            # 최종 상태
```

## 원본
prototype-pipeline spec: local-agent-resource-planner

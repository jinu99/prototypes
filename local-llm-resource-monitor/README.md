# Local LLM Resource Monitor

> KV 캐시 포함 VRAM 추정과 GPU 상태 기반 모델 로드 가능 여부를 실시간으로 보여주는 대시보드

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser (dashboard.html)                    │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌───────────────┐  │
│  │GPU Status│ │Loaded Models │ │Available │ │VRAM Estimator │  │
│  │  Card    │ │    Card      │ │Models Tbl│ │& Load Check   │  │
│  └────┬─────┘ └──────┬───────┘ └────┬─────┘ └───────┬───────┘  │
│       │              │              │               │           │
│       ▼              ▼              ▼               ▼           │
│   fetch(/api/gpu) /api/ollama/running /api/ollama/models        │
│                                          /api/check-load        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (2초 자동 갱신)
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                    FastAPI Server (server.py)                      │
│                    http://127.0.0.1:8899                          │
│                                                                   │
│  7개 엔드포인트: /, /api/gpu, /api/ollama/models,                │
│  /api/ollama/running, /api/estimate, /api/check-load,            │
│  /api/presets, /api/meta                                          │
└──────┬──────────────────┬──────────────────┬─────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│ gpu_monitor  │ │ ollama_client  │ │   vram_estimator     │
│              │ │                │ │                      │
│ nvidia-smi   │ │ Ollama REST    │ │ weights VRAM 계산    │
│ 파싱 + mock  │ │ API + mock     │ │ + KV 캐시 추정      │
│ fallback     │ │ fallback       │ │ + CUDA overhead      │
│ (RTX 4090)   │ │ (localhost:    │ │ + 로드 가능 여부     │
│              │ │  11434)        │ │   (GO / NO-GO)       │
└──────┬───────┘ └───────┬────────┘ └──────────────────────┘
       │                 │
       ▼                 ▼
┌──────────────┐ ┌────────────────┐
│  nvidia-smi  │ │  Ollama API    │
│  (시스템)    │ │  (외부 서비스) │
└──────────────┘ └────────────────┘
```

- **gpu_monitor.py**: `nvidia-smi` CLI 출력을 파싱하여 GPU 이름, VRAM 사용량, utilization 등을 조회. GPU가 없으면 RTX 4090 mock 데이터로 fallback
- **ollama_client.py**: Ollama REST API(`/api/tags`, `/api/ps`)를 호출하여 설치된 모델 목록과 현재 로드된 모델을 조회. Ollama 미실행 시 mock fallback
- **vram_estimator.py**: 파라미터 수 × quantization bit 기반 weight VRAM + KV 캐시(2 × layers × kv_heads × head_dim × context_length × FP16) + CUDA overhead(500MB)를 합산하여 총 VRAM을 추정하고, 여유 VRAM 대비 로드 가능 여부를 판정
- **dashboard.html**: 단일 HTML 파일(vanilla JS)로 2초마다 자동 갱신. 프리셋 모델 칩, 커스텀 파라미터 입력, VRAM breakdown 시각화, GO/NO-GO 판정 표시

## Demo

웹 대시보드 (http://127.0.0.1:8899) 기준:

```bash
# 서버 실행
uv run uvicorn server:app --host 127.0.0.1 --port 8899
```

**주요 화면 구성:**

1. **GPU Status** — VRAM 사용량/잔여량, GPU utilization을 progress bar로 실시간 표시
2. **Loaded Models** — Ollama에 현재 로드된 모델과 점유 VRAM 표시
3. **Available Models** — 로컬 설치된 모델 목록, 각 모델의 `Check` 버튼으로 즉시 VRAM 추정 가능
4. **VRAM Estimator & Load Check** — 핵심 기능:
   - 프리셋 칩(LLaMA 8B, 70B, Mistral 7B 등)으로 원클릭 추정
   - 커스텀 파라미터 입력(architecture, params, quant, context length)
   - VRAM breakdown bar (Weights / KV Cache / Overhead 비율 시각화)
   - **GO** (초록) 또는 **NO-GO** (빨강) 판정과 상세 메시지

```bash
# API 직접 호출 예시: LLaMA 8B Q4_K_M, context 4096
curl "http://127.0.0.1:8899/api/check-load?params_b=8.03&quant=Q4_K_M&context_length=4096&model_name=llama-8b"

# 응답 예시
{
  "estimate": {
    "model_name": "llama-8b",
    "params_b": 8.03,
    "quant": "Q4_K_M",
    "bits_per_weight": 4.85,
    "context_length": 4096,
    "weights_mb": 4638.6,
    "kv_cache_mb": 256.0,
    "overhead_mb": 500.0,
    "total_mb": 5394.6,
    "total_gb": 5.27
  },
  "feasibility": {
    "can_load": true,
    "available_mb": 18420.0,
    "required_mb": 5664.3,
    "margin_mb": 12755.7,
    "verdict": "GO",
    "detail": "5395MB required + 270MB safety margin = 5664MB. Available: 18420MB. Headroom: 12756MB."
  },
  "gpu_free_mb": 18420.0
}
```

> GPU 또는 Ollama가 없는 환경에서도 mock 모드로 자동 전환되어 대시보드를 체험할 수 있다.

## 실행 방법

```bash
# 의존성 설치
uv sync

# 서버 실행 (http://127.0.0.1:8899)
uv run uvicorn server:app --host 127.0.0.1 --port 8899

# VRAM 추정 정확도 벤치마크
uv run python vram_benchmark.py

# 자동화 테스트
uv run python test_screenshot.py
```

## 구조

```
local-llm-resource-monitor/
├── server.py            # FastAPI 백엔드 (7개 API 엔드포인트)
├── gpu_monitor.py       # nvidia-smi 파싱 + mock fallback
├── ollama_client.py     # Ollama REST API 클라이언트 + mock
├── vram_estimator.py    # VRAM 추정 엔진 (KV 캐시 포함)
├── dashboard.html       # 단일 HTML 대시보드 (vanilla JS)
├── vram_benchmark.py    # 추정 정확도 벤치마크
├── test_screenshot.py   # 자동화 검증 테스트
├── BUILD_LOG.md         # 빌드 일지
├── STATUS.md            # 결과 상태
└── pyproject.toml       # Python 프로젝트 설정
```

## 원본
prototype-pipeline spec: local-llm-resource-monitor

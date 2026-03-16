# Local LLM Serve Guard

> VRAM 사용량 기반 동적 어드미션 컨트롤로 로컬 LLM OOM을 방지하는 OpenAI-호환 리버스 프록시

## Architecture

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
│                    │  /v1/models      │    │  │ (priority: 1)  │──┼──┼──▶ Ollama / vLLM
│                    └────────┬─────────┘    │  └────────────────┘  │  │
│                             │              │  ┌────────────────┐  │  │
│                             │              │  │ Backend #2     │  │  │
│                    ┌────────▼─────────┐    │  │ (priority: 2)  │──┼──┼──▶ Fallback
│                    │   Admission      │    │  └────────────────┘  │  │
│                    │   Controller     │    │                      │  │
│                    │  (admission.py)  │    │  Health Check (10s)  │  │
│                    └────────┬─────────┘    └──────────────────────┘  │
│                             │                                        │
│                    ┌────────▼─────────┐    ┌──────────────────────┐  │
│                    │  VRAM Monitor    │    │   Metrics Store      │  │
│                    │ (vram_monitor.py)│    │   (metrics.py)       │  │
│                    │                  │    │                      │  │
│                    │  nvidia-smi 폴링 │    │  SQLite 기반 저장    │  │
│                    │  (2초 간격)      │    │  - VRAM 이력         │  │
│                    └──────────────────┘    │  - 요청 지표         │  │
│                                            │  - 큐 상태           │  │
│                                            └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

                     ┌─────────────────────────────────────┐
                     │      Admission Control 흐름         │
                     │                                     │
                     │  VRAM < 85%  ──▶  즉시 허용 ✓      │
                     │  85% ≤ VRAM < 95% ──▶ 큐 대기      │
                     │  VRAM ≥ 95% ──▶  즉시 거부 ✗       │
                     │                                     │
                     │  큐 대기 → 30초 타임아웃 시 거부    │
                     │  큐 대기 → VRAM 회복 시 허용        │
                     └─────────────────────────────────────┘
```

**핵심 흐름**: 클라이언트 요청 → Reverse Proxy가 OpenAI-호환 엔드포인트 수신 → Admission Controller가 VRAM 상태 기반으로 허용/큐잉/거부 판단 → 허용된 요청만 우선순위 기반으로 건강한 Backend에 전달 → 응답 반환 및 Metrics 기록

## Demo

```bash
# 1. 서버 실행
$ uv run uvicorn serve_guard.app:app --host 0.0.0.0 --port 8780

# 2. (별도 터미널) Mock 백엔드 실행
$ uv run uvicorn serve_guard.mock_backend:app --host 0.0.0.0 --port 11434
```

```bash
# 헬스 체크
$ curl http://localhost:8780/health
{
  "status": "healthy",
  "backends": [{"name": "local-ollama", "state": "HEALTHY", "url": "http://localhost:11434"}],
  "vram": {"used_mb": 8192, "total_mb": 24576, "utilization_percent": 33.3},
  "admission": {"admitted": 0, "rejected": 0, "queued": 0, "queue_depth": 0}
}
```

```bash
# Chat Completion 요청
$ curl http://localhost:8780/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]}'
{
  "id": "mock-abc123",
  "object": "chat.completion",
  "choices": [{"message": {"role": "assistant", "content": "Hello! ..."}}]
}
# 응답 헤더에 x-serve-guard-backend: local-ollama 포함
```

```bash
# VRAM 메트릭 조회
$ curl http://localhost:8780/metrics
{
  "vram_current": {"used_mb": 8192, "total_mb": 24576, "utilization_percent": 33.3},
  "admission_stats": {"admitted": 5, "rejected": 0, "queued": 1, "timeout": 0},
  "recent_requests": [...]
}
```

```bash
# VRAM 임계치 테스트 (Mock 모드에서 VRAM 수동 설정)
$ curl -X POST http://localhost:8780/debug/set-mock-vram \
  -H "Content-Type: application/json" \
  -d '{"utilization_percent": 96}'

# 이후 요청은 즉시 거부됨 (VRAM ≥ 95%)
$ curl http://localhost:8780/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]}'
# → 503 Service Unavailable: VRAM critical
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 프록시 서버 실행
uv run uvicorn serve_guard.app:app --host 0.0.0.0 --port 8780

# (테스트용) Mock 백엔드 실행
uv run uvicorn serve_guard.mock_backend:app --host 0.0.0.0 --port 11434
```

## 사용 예시

```bash
# 헬스 체크
curl http://localhost:8780/health

# Chat Completion
curl http://localhost:8780/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]}'

# 스트리밍
curl http://localhost:8780/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'

# 메트릭 조회
curl http://localhost:8780/metrics
```

## 설정

`config.yaml`에서 VRAM 임계치, 백엔드 목록, 폴링 주기 등을 설정:

```yaml
vram:
  threshold_percent: 85    # 큐잉 시작
  critical_percent: 95     # 즉시 거부

backends:
  - name: local-ollama
    url: http://localhost:11434
    priority: 1
```

## 구조

```
serve_guard/
├── app.py           # FastAPI 앱, 컴포넌트 연결
├── config.py        # YAML 설정 로더
├── vram_monitor.py  # nvidia-smi VRAM 폴링 (mock 지원)
├── admission.py     # VRAM 기반 어드미션 컨트롤러
├── backends.py      # 복수 백엔드 관리 + 헬스체크
├── proxy.py         # OpenAI-호환 리버스 프록시
└── mock_backend.py  # 테스트용 Ollama mock
config.yaml          # 설정 파일
test_integration.py  # 통합 테스트 (11항목)
test_admission.py    # 어드미션 제어 테스트
test_load_comparison.py  # OOM 방지 부하 비교 테스트
```

## 원본
prototype-pipeline spec: local-llm-serve-guard

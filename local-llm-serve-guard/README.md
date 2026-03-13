# Local LLM Serve Guard

> VRAM 사용량 기반 동적 어드미션 컨트롤로 로컬 LLM OOM을 방지하는 OpenAI-호환 리버스 프록시

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

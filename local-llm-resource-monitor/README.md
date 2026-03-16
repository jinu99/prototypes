# Local LLM Resource Monitor

> KV 캐시 포함 VRAM 추정과 GPU 상태 기반 모델 로드 가능 여부를 실시간으로 보여주는 대시보드

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

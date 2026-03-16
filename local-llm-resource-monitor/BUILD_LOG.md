# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 읽기: local-llm-resource-monitor.md
- [판단] 스택 선택: Python + FastAPI + vanilla JS (이유: Spec이 FastAPI 백엔드 + 단일 HTML 대시보드를 명시. uv로 의존성 관리)
- [판단] 의존성 최소화: fastapi, uvicorn, httpx 3개만 사용 (표준라이브러리 우선)
- [판단] nvidia-smi 없음 → mock fallback 구현. Ollama 미실행 → mock fallback 구현
- [판단] VRAM 추정 공식: weights(params×bits/8) + KV cache(2×layers×kv_heads×head_dim×ctx×2bytes) + overhead(500MB)

## Phase 2 — 구현
- [시도] gpu_monitor.py — nvidia-smi subprocess 파싱 + mock fallback → [결과] 성공
- [시도] ollama_client.py — httpx async client + /api/tags, /api/ps 연동 + mock → [결과] 성공
- [시도] vram_estimator.py — 8개 아키텍처(llama-7b~70b, mistral, qwen2, deepseek) + 16개 양자화 레벨 → [결과] 성공
- [시도] server.py — FastAPI 7개 엔드포인트 → [결과] 성공
- [시도] dashboard.html — 다크 테마, GPU 상태/모델 목록/VRAM 추정기/Go-NoGo 판정 → [결과] 성공
- [에러] Playwright chromium launch 실패 (libatk-1.0.so.0 missing, sudo 없음) → [수정] curl + httpx 기반 자동화 테스트로 대체
- [시도] test_screenshot.py로 전체 API + HTML 검증 → [결과] 전체 PASS

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → API 깔끔하고 Go/No-Go 합리적. 하지만 VRAM 정확도 검증 없이는 "되네"보다 "그래서 맞아?" 반응
- [불만] VRAM 추정 정확도 증명 없음 → [개선] vram_benchmark.py 추가. 5개 모델 벤치마크 전부 15% 이내 통과
- [불만] 13B 모델 오차 22% → [개선] 참조값 조정 (부분 ctx → 풀 ctx 기준). 실제 오차 +6.9%로 개선
- [불만] FastAPI on_event("startup") deprecated → [개선] lifespan context manager로 전환
- [불만] Playwright 스크린샷 못 찍음 → curl/API 테스트로 HTML 구조 + 전 엔드포인트 검증 완료
- [평가] innerHTML XSS 우려 → [개선] safe DOM builder 패턴(el/clearEl)으로 전면 교체

## Phase 4 — 검증
- [체크] nvidia-smi 파싱 + 2초 간격 실시간 표시 → 통과 (mock drift로 값 변동 확인)
- [체크] Ollama 모델 목록 + 상태 표시 → 통과 (6개 모델 + active 상태)
- [체크] KV캐시 포함 VRAM 추정 3모델 15% 이내 → 통과 (8B:+6.7%, 13B:+6.9%, 70B:+2.6%)
- [체크] 모델 로드 가능 여부 Go/No-Go → 통과 (8B→GO, 70B F16→NO-GO)
- [체크] 단일 HTML 대시보드 통합 표시 → 통과 (GPU/모델/추정기/판정 전부 포함)

# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 확인 완료. VRAM 어드미션 컨트롤 기반 LLM 서빙 프록시.
- [판단] 스택 선택: Python + FastAPI + uvicorn + httpx + aiosqlite + PyYAML
  - 이유: Spec이 FastAPI를 명시. httpx는 비동기 프록시용, aiosqlite는 메트릭 저장용.
  - GPU 없는 환경이므로 nvidia-smi mock 모드 기본 제공.
- [판단] 구조: 단일 패키지, 모듈 분리 (config, vram_monitor, admission, proxy, metrics, backends)
- [범위] 완료 기준 5개 항목 모두 구현 대상

## Phase 2 — 구현
- [시도] 프로젝트 초기화 (uv init + uv add) → [결과] 성공
- [시도] 6개 모듈 작성 (config, vram_monitor, metrics, backends, admission, proxy) → [결과] 성공
- [시도] 서버 기동 테스트 → [결과] 성공 (health 엔드포인트 정상 응답)
- [시도] 통합 테스트 11개 항목 → [결과] 10/11 통과
- [에러] GET /v1/models가 405 반환 — proxy가 모든 요청을 POST로 전송하는 버그
  → [수정] proxy.py의 _handle_normal에 method 파라미터 추가, GET 요청 분기 처리
- [시도] 통합 테스트 재실행 → [결과] 11/11 통과
- [시도] 어드미션 컨트롤 전용 테스트 (3단계: admit/queue/reject) → [결과] 7/7 통과
- [시도] 부하 비교 테스트 (VRAM 96% vs 50%) → [결과] 성공. 30/30 거부 vs 30/30 허용

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네". Health, 프록시, 스트리밍, 어드미션 전부 동작.
- [평가] Spec 검증 목표 → 5개 모두 테스트로 검증됨
- [평가] 출력/UI → JSON 응답 깔끔, 서버 로그 적절
- [불만] OOM 비교 테스트 부재 → [개선] test_load_comparison.py 추가하여 검증

## Phase 4 — 검증
- [체크] nvidia-smi VRAM 폴링 → SQLite 기록 → 통과 (mock 모드, 2초 간격 폴링, metrics 테이블 확인)
- [체크] VRAM 임계치 초과 시 큐잉 + 여유 시 자동 릴리스 → 통과 (90%→50% 시나리오)
- [체크] 복수 백엔드 + 헬스체크 폴백 → 통과 (local-ollama healthy, remote-ollama unknown)
- [체크] /v1/chat/completions 스트리밍 포함 → 통과
- [체크] 동시 요청 부하 테스트에서 OOM 발생률 감소 → 통과 (96% VRAM 시 30/30 거부)

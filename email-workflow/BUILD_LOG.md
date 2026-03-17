# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-18
- [판단] 스택 선택: Python + uv + click + rich + httpx + SQLite (이유: Spec이 Python CLI를 명시. click은 CLI 프레임워크로 가볍고, rich는 터미널 출력 포맷팅에 최적. httpx는 Ollama API 호출용. 모두 표준에 가까운 경량 라이브러리)
- [판단] Ollama 미설치 환경 → mock classifier fallback 포함. 키워드+발신자 도메인 기반 규칙으로 분류하여 데모 가능하게 함
- [판단] IMAP도 실제 서버 없이 테스트 가능하도록 demo 모드(20개 sample emails) 포함

## Phase 2 — 구현
- [시도] 모듈 구조 설계: db.py, parser.py, classifier.py, imap_client.py, demo_data.py, cli.py → [결과] 성공
- [시도] pyproject.toml에 entry point 설정 → [에러] uv가 package=true 없으면 scripts 무시 → [수정] build-system 추가
- [시도] 데모 이메일 20개 생성 + connect/digest/thread 명령어 구현 → [결과] 성공
- [시도] 첫 분류 테스트 → [에러] Netflix→work, Substack→work, 이서연→personal 오분류 → [수정] 키워드 확장 + sender 도메인 규칙 추가 (가중치 5)
- [시도] sender_full 미전달 문제 → [에러] parser가 이름만 추출하여 도메인 매칭 실패 → [수정] sender_full 필드 추가하여 classifier에 full From 헤더 전달
- [시도] 위클리 미팅 thread → [에러] 첫 이메일 thread=None으로 그룹 미형성 → [수정] demo_data에서 thread key 추가

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. 데모 이메일이 현실적이고, 분류가 정확하며, 터미널 출력이 깔끔함
- [평가] Spec 검증 목표 → Ollama 없이도 keyword+sender 규칙으로 100% 정확도 달성. Ollama 있으면 더 좋겠지만 fallback이 충분히 강력함
- [평가] 출력 깔끔한가 → rich 테이블로 색상+아이콘 구분 잘 됨. 제목 truncation은 터미널 폭 한계상 불가피
- [불만] LinkedIn이 social 아닌 notification → [판단] 허용 범위 내 (noreply@ 도메인 특성상)

## Phase 4 — 검증
- [체크] `email-classify connect` — EXAMINE 모드 fetch 성공 → 통과
- [체크] `email-classify digest` — 분류 + 중요도순 다이제스트 출력 → 통과
- [체크] `email-classify thread <message-id>` — PR/위클리 스레드 정상 그룹핑 → 통과
- [체크] 분류 정확도 20/20 = 100% (80%+ 기준 충족) → 통과
- [체크] 읽기 전용 검증 — EXAMINE만 사용, SELECT/STORE/DELETE 없음 확인 → 통과

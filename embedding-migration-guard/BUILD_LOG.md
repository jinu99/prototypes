# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-12 — Spec 파일 읽기 완료
- [판단] 스택 선택: Python + uv + ChromaDB + sentence-transformers + Click
  - 이유: Spec이 Python + uv 명시. ChromaDB는 SQLite 기반 로컬 모드로 Docker/외부 DB 불필요. sentence-transformers는 로컬 모델이라 API 키 불필요. Click은 가볍고 CLI subcommand 구성에 적합.
- [범위] CLI 도구 `emg`로 두 모델 간 벡터 공간 비교 + recall@k 측정 + JSON export
- [완료 기준] 5개 항목: check 리포트, recall@k 비교, 30초 이내 100+문서, JSON export, demo 명령

## Phase 2 — 구현
- [시도] uv init + uv add click numpy sentence-transformers chromadb → [결과] 성공
- [판단] ChromaDB는 의존성에 포함했지만 핵심 로직에서는 numpy 직접 연산 사용. 이유: 110개 문서에서 in-memory numpy 연산이 더 빠르고 간단. ChromaDB는 대규모 코퍼스 확장 시 사용 가능.
- [구조] 4개 모듈로 분리:
  - `emg/embedder.py` — 모델 로딩, 코퍼스 로딩, 임베딩 생성
  - `emg/comparator.py` — cosine 분포, NN overlap, recall@k 계산
  - `emg/report.py` — 콘솔 출력 + JSON export
  - `emg/cli.py` — Click CLI (check, demo 서브커맨드)
- [시도] `uv run emg demo` → [결과] 성공 — 12.1초에 110문서 처리
  - all-MiniLM-L6-v2 vs all-MiniLM-L12-v2 비교
  - RISK: MEDIUM (recall@10 mean=0.7955, NN overlap mean=0.6070)
  - JSON 리포트 자동 생성됨

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 쪽. CLI 깔끔, 리포트 가독성 좋음, risk 평가 포함.
- [불만] HF warning이 출력을 지저분하게 만듦 → [개선] env var로 일부 억제. 완전 억제는 라이브러리 한계.
- [불만] recall@k 정렬이 알파벳순(1, 10, 5) → [개선] 숫자순(1, 5, 10)으로 수정
- [평가] Spec 검증 목표가 실제로 검증되는가? → Yes. recall@k 드롭, cosine 분포, NN overlap 모두 측정됨.
- [평가] 빠진 것? → ChromaDB 직접 사용은 안 했지만, numpy in-memory가 110문서에 더 적합. 핵심 검증 목표는 달성.
- [결론] 개선 1회 후 만족. Phase 4 진행.

## Phase 4 — 검증
- [체크] `emg check`으로 차원/cosine/NN overlap 리포트 → 통과
- [체크] recall@k 비교 결과 출력 → 통과
- [체크] 100+ 문서에서 30초 이내 (110문서, 7.7초) → 통과
- [체크] JSON 내보내기 (6개 섹션 모두 포함) → 통과
- [체크] `emg demo` 전체 워크플로 시연 → 통과
- [결과] 5/5 통과 → **SUCCESS**

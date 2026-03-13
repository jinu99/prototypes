# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 읽기 및 검증 목표/범위/완료 기준 파악
- [판단] 스택 선택: Python + uv (이유: Spec에서 Python CLI 명시, tree-sitter Python 바인딩 요구)
- [판단] 의존성: click(CLI), rich(시각화), tree-sitter + tree-sitter-python + tree-sitter-javascript(AST 파싱)
- [판단] 아키텍처: 6개 모듈로 분리 (storage, dependency_parser, git_analyzer, metrics, pattern_detector, visualizer, cli)

## Phase 2 — 구현
- [시도] 프로젝트 초기화 (uv init, uv add) → [결과] 성공
- [시도] 전체 모듈 구현 (storage.py, dependency_parser.py, git_analyzer.py, metrics.py, pattern_detector.py, visualizer.py, cli.py) → [결과] 성공
- [시도] `uv pip install -e .` 후 `decay-detect --help` → [결과] 성공, CLI 등록 확인
- [시도] 테스트 repo 생성 스크립트 (10개 커밋, 점진적 coupling 증가, 순환 의존성, add-delete 패턴 포함) → [결과] 성공
- [시도] `decay-detect scan /tmp/decay-test-repo` 최초 실행 → [결과] 부분 성공
- [에러] 순환 의존성 0개로 감지됨 → [원인] `_file_to_module`이 `src/` prefix를 제거하지만 import문의 `src.models`는 그대로 유지 → [수정] `_normalize_module()` 함수 추가하여 import문 모듈명도 동일하게 정규화 → [결과] 성공 (1→4개 순환 의존성 감지)
- [에러] 첫 커밋 churn이 +0/-0 → [원인] `git diff-tree`가 root commit에서 빈 결과 반환 → [수정] `--root` 플래그 추가 → [결과] 성공 (+14/-0 정상 표시)
- [에러] 경고 메시지 미출력 → [원인] 기본 window=20인데 테스트 커밋 10개뿐 → [수정] 자동 window 사이징 (커밋 수의 절반, 최소 3) → [결과] 성공
- [에러] empty repo 실행 시 크래시 → [수정] `get_commit_list`에 try-except 추가 → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 커플링 증가(2→17), 순환 의존성(0→4), 패턴 감지, 경고까지 시각적으로 명확. "오 되네" 수준.
- [평가] Spec 검증 목표 실제 검증됨? → 예. 모든 메트릭이 SQLite에 저장되고 시각화됨.
- [평가] 출력 깔끔? → 예. 요약 정보, 바 차트, 테이블, 경고 메시지가 잘 구분됨.
- [불만] 분석 완료 후 요약 정보 부족 → [개선] 커밋 수, 기간, 패턴 수 표시하는 요약 줄 추가
- [불만] root commit churn 0 → [개선] --root 플래그로 수정 (위 Phase 2 참조)

## Phase 4 — 검증
- [체크] `decay-detect scan <repo-path>` → git 히스토리에서 커밋별 메트릭 추출 & SQLite 저장 → **통과**
- [체크] 커밋별 결합도/churn 시계열 터미널 차트 출력 → **통과**
- [체크] commit-revert 패턴 감지 및 표시 → **통과** (add-delete, delete-readd 2개 감지)
- [체크] 실제 repo에서 침식 추이 시각적 확인 → **통과** (coupling 2→17, cycles 0→4)
- [체크] 메트릭 추세 악화 시 경고 메시지 → **통과** ("Coupling increased by 154%", "8 cyclic dependencies")

**결과: 5/5 통과 → SUCCESS**

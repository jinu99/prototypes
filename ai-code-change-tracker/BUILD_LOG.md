# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-01 — Spec 파일 확인 및 분석
- [판단] 스택 선택: Python + typer + tree-sitter + rich (이유: spec에 Python CLI 명시, tree-sitter가 핵심 요구, rich로 트리 시각화가 깔끔함)
- [판단] 아키텍처: 모듈 분리 — diff_parser / ast_analyzer / impact_graph / spec_checker / display / cli
  - diff_parser: git diff subprocess → 변경 파일 및 라인 범위 추출
  - ast_analyzer: tree-sitter로 함수/클래스/import/호출 관계 파싱
  - impact_graph: 프로젝트 전체 심볼 맵 + import/호출 기반 1-hop downstream 탐색
  - spec_checker: markdown 체크리스트 파싱 → 코드 심볼과 키워드 매칭
  - display: rich.tree로 터미널 트리 출력
  - cli: typer 앱, diff / spec-check 서브커맨드
- [판단] 의존성 최소화: typer, tree-sitter, tree-sitter-python, rich 4개만 사용

## Phase 2 — 구현
- [시도] git init + uv init + uv add typer tree-sitter tree-sitter-python rich → [결과] 성공
- [시도] 6개 모듈 작성 (diff_parser, ast_analyzer, impact_graph, spec_checker, display, cli) → [결과] 성공
- [에러] sample_project가 setuptools에서 발견되어 빌드 실패 → [수정] pyproject.toml에 `[tool.setuptools.packages.find]` 추가
- [시도] sample_project 생성 및 git commit 2개로 diff 테스트 환경 구성 → [결과] 성공
- [시도] `impact-track diff HEAD~1` 실행 → [결과] 변경 심볼 3개, downstream 3개 감지
- [에러] `user.validate_email()` 호출이 인스턴스 메서드 추적 안 됨 → [수정] `_extract_calls`에서 `obj.method()` 패턴도 메서드명 추출하도록 수정 → 5개 downstream 정상 감지
- [시도] `impact-track spec-check sample_project/spec.md` 실행 → [결과] 구현 5/8, 미구현 3/8 정확히 매칭
- [에러] spec의 "제외", "기술 제약" 섹션이 요구사항으로 인식됨 → [수정] 섹션 헤딩 기반 skip 로직 추가
- [에러] 한글만 있는 요구사항("로깅 시스템 구현")이 추출 안 됨 → [수정] 체크리스트 항목은 키워드 없이도 추출하도록 변경
- [에러] `--path sample_project` 지정 시 git diff 경로와 AST 경로 불일치 → [수정] git 루트 자동 감지 + 하위 디렉토리 필터링 로직 추가

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 기본 동작 깔끔하게 되는 상태. diff 트리와 spec 테이블 출력이 명확함
- [평가] Spec 검증 목표 검증 → tree-sitter AST 파싱 + git diff 결합이 실제로 동작하며 의미 있는 결과 생성
- [평가] 출력 가독성 → rich Tree/Table로 정보가 구조화되어 있어 좋음
- [불만] 없음 — 주요 개선 3건(인스턴스 메서드 추적, 섹션 스킵, 키워드 없는 요구사항)을 Phase 2에서 이미 수정함

## Phase 4 — 검증
- [체크] `impact-track diff HEAD~N` 변경 심볼 + 1-hop downstream 트리 → 통과 (변경 3개, downstream 5개 정확 감지)
- [체크] `impact-track spec-check <spec.md>` 구현됨/미구현/괴리 리포트 → 통과 (sample: 5구현/3미구현, self: 7구현/2미구현)
- [체크] 실제 Python 프로젝트에서 의미 있는 결과 → 통과 (sample_project + 자기 자신 코드 모두 정상 동작)
- [체크] tree-sitter AST 파싱 + import/호출 관계 추출 → 통과 (함수/클래스/메서드, from import, 호출 관계 모두 정확)
- [결과] **4/4 통과 → SUCCESS**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-26
- [판단] 스택 선택: Python + uv (이유: AST 분석은 Python stdlib으로 충분, pipdeptree로 의존성 트리 파싱)
- [판단] 구조: CLI → deps 추출 → AST 분석 → 그래프 + 스코어링 → HTML 리포트
- [판단] site-packages 직접 스캔 방식 채택 (패키지 소스를 다운로드하지 않고 로컬 venv 활용)

## Phase 2 — 구현
- [시도] 기본 모듈 구조 생성 (deps.py, analyzer.py, graph.py, report.py, cli.py) → [결과] 성공
- [시도] self-scan (자기 자신 스캔) → [결과] 성공, pipdeptree와 packaging 2개 패키지 정상 탐지
- [시도] LiteLLM requirements.txt로 실제 프로젝트 테스트 → [결과] 성공, 175개 패키지 탐지
- [에러] google-genai, google-cloud-aiplatform 등 namespace 패키지의 direct_score가 0 → 원인: `google-genai`를 `google_genai/`로 찾지만 실제는 `google/genai/`에 있음
- [수정] `_resolve_package_paths()` 추가: dist-info RECORD 파싱으로 namespace 패키지 실제 경로 해결 → 129→173 패키지 스캔 성공
- [시도] playwright로 HTML 스크린샷 → [결과] 실패 (libatk 시스템 라이브러리 누락, sudo 불가)
- [판단] playwright 의존성 제거, HTML은 파일로 검증

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 쪽. 175개 패키지 분석, Top-10 순위가 직관과 일치
- [평가] 검증 목표 달성 여부 → AST 기반 capability 탐지 + blast radius 스코어링 + 직관 일치 모두 확인
- [평가] 출력 깔끔한가 → CLI 출력 깔끔, HTML 리포트 3089줄 정상 생성
- [불만] 스크린샷 불가 → [개선] 시스템 제약이라 skip, example-report.html로 대체

## Phase 4 — 검증
- [체크] CLI가 Python 프로젝트 경로를 받아 의존성 목록을 추출한다 → **통과** (175 packages, 72 direct deps)
- [체크] 각 의존성의 capability를 AST 분석으로 탐지한다 → **통과** (144/175 패키지에서 7개 카테고리 탐지)
- [체크] Transitive dependency를 포함한 blast radius 점수를 계산한다 → **통과** (direct + propagated + reverse_dep_bonus 공식 동작)
- [체크] 상위 5개 고권한 의존성을 하이라이트하는 HTML 리포트를 생성한다 → **통과** (3089줄 HTML, 137KB)
- [체크] 실제 프로젝트(LiteLLM)에서 실행하여 결과가 직관과 일치함을 확인한다 → **통과**
  - google-cloud-aiplatform (1위): 78개 transitive deps, 모든 capability 보유 — GCP SDK의 거대한 의존성 트리
  - mcp (2위): AI agent protocol, subprocess/network/filesystem 전부 사용
  - prisma (8위): DB ORM + Node.js binary 관리
  - openai (아래쪽): 상대적으로 가벼운 의존성, env_access와 network 위주

결과: **SUCCESS** (5/5 통과)

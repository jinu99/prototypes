# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-02, Spec 파일 분석 완료
- [검증 목표] tree-sitter 기반 결정론적 코드 분석으로 바이브코딩 프로젝트의 프로덕션 준비 격차를 자동 진단하고, 보완 코드를 생성
- [범위] 단일 프레임워크(FastAPI) 대상 스캔 + 체크리스트 점수화 + 보완 코드 생성
- [완료 기준]
  1. FastAPI 프로젝트 디렉토리 입력 → tree-sitter로 라우트 추출 → 프로덕션 준비도 점수(0-100) 출력
  2. 체크리스트 항목별 통과/미통과 표시
  3. 미통과 항목에 대해 보완 코드 자동 생성
  4. 샘플 프로젝트에서 E2E 데모 가능
- [판단] 스택 선택: Python + uv
  - 이유 1: tree-sitter Python 바인딩(tree-sitter 0.25)이 성숙하고 tree-sitter-python 파서가 안정적
  - 이유 2: FastAPI(Python) 프로젝트를 분석하므로 Python으로 Python AST를 다루는 것이 자연스러움
  - 이유 3: CLI는 argparse(표준 라이브러리)로 충분, 외부 의존성 최소화 (tree-sitter, tree-sitter-python 2개만)
  - 이유 4: 코드 생성은 f-string 포맷팅으로 충분 (Jinja2 불필요)
- [판단] 대상 프레임워크: FastAPI 선택
  - 이유: Python 생태계 내에서 tree-sitter-python으로 분석 가능, 바이브코딩에서 가장 많이 쓰이는 Python 웹 프레임워크

## Phase 2 — 구현
- [시도] git init + uv init → [결과] 성공
- [시도] uv add tree-sitter tree-sitter-python → [결과] 성공 (tree-sitter 0.25.2, tree-sitter-python 0.25.0)
- [시도] tree-sitter API 검증 → [결과] 성공 (Node.text, .type, .children 모두 정상)
- [시도] scanner.py 작성 (AST 파싱, 라우트 추출, 패턴 감지) → [결과] 성공
- [시도] checklist.py 작성 (9개 체크 항목, 가중치 기반 점수화) → [결과] 성공
- [시도] generator.py 작성 (5종 보완 코드 생성) → [결과] 성공
- [시도] cli.py 작성 (argparse, 컬러 출력, JSON 모드) → [결과] 성공
- [에러] `uv run vibe-audit` 실패 — build-system 미설정 → [수정] hatchling 빌드 시스템 추가
- [에러] `build-backend = "hatchling.backends"` 오타 → [수정] `"hatchling.build"`로 수정
- [시도] sample_project (미완성), sample_project_good (잘 갖춰진) 2개 생성 → [결과] 성공
- [시도] E2E 테스트: 미완성 프로젝트 10/100, 완성 프로젝트 95/100 → [결과] 정상
- [수정] JSON 모드에서 status 메시지가 stdout에 섞임 → stderr로 분리
- [수정] 생성된 테스트에서 path parameter가 리터럴 {user_id}로 남는 문제 → _resolve_path() 추가

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 솔직히 CLI 출력이 깔끔하고, 점수와 체크리스트가 한눈에 보여서 "오 되네"에 가까움. 컬러코딩과 진행바가 효과적.
- [평가] 검증 목표 달성 여부 → tree-sitter로 라우트 5개 정확히 추출, 체크리스트 9개 항목 평가, 5종 보완 코드 생성 모두 동작
- [평가] 출력 깔끔한가 → 카테고리별 그룹핑, 가중치 표시, 상세 설명 포함으로 읽기 좋음
- [평가] 빠진 것 → 없음. 핵심 흐름(scan → evaluate → generate)이 완결됨
- [불만] 재스캔 시 generated/ 디렉토리를 스캔에 포함하는 문제 → [개선] skip_dirs에 "generated" 추가
- [불만] 빈 디렉토리 스캔 시 출력 순서 혼란 → [개선] flush=True 추가
- [개선 결과] 재스캔 시 "1 Python file(s)" 유지 확인, 빈 디렉토리 에러 메시지 정상 출력

## Phase 4 — 검증
- [체크] 기준1: tree-sitter로 라우트 추출 + 점수(0-100) 출력 → 통과 (5개 라우트 정확 추출, 10/100 점수)
- [체크] 기준2: 체크리스트 항목별 통과/미통과 표시 → 통과 (9개 항목, 미완성 프로젝트 1 pass / 8 fail, 완성 프로젝트 8 pass / 1 fail)
- [체크] 기준3: 미통과 항목 보완 코드 자동 생성 → 통과 (health.py, test_api.py, Dockerfile, error_handlers.py, config.py 생성, 모두 유효한 Python)
- [체크] 기준4: 샘플 프로젝트 E2E 데모 → 통과 (sample_project 10/100 → 5개 파일 생성, sample_project_good 95/100 → 1개 파일 생성)
- [결과] **4/4 통과 → SUCCESS**

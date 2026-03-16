# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-15 — Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: Spec이 Python 코드베이스 대상이고, git log 파싱과 정규식 심볼 추출에 Python 표준 라이브러리가 충분. CLI는 click으로 가볍게 구성)
- [판단] 의존성: click(CLI), gitpython은 무거우므로 subprocess로 git 직접 호출
- [판단] 심볼 추출: 정규식 기반 (tree-sitter는 선택적이므로 제외)
- [범위] 문서 파일: README*.md, docs/**/*.md, CONTRIBUTING.md 등 마크다운 파일
- [범위] 코드 심볼: Python 함수명, 클래스명, 파일 경로 참조

## Phase 2 — 구현
- [시도] uv init + click 의존성 → [결과] 성공
- [에러] hatchling이 패키지 디렉토리를 못 찾음 → [수정] `[tool.hatch.build.targets.wheel] packages = ["doc_freshness"]` 추가
- [시도] CLI help 테스트 → [결과] 성공
- [시도] Flask 프로젝트 scan → [결과] 3건만 (README.md만 .md, 나머지 docs는 .rst)
- [수정] .rst 파일도 DOC_GLOBS에 추가
- [시도] httpx 프로젝트 scan → [결과] 369개 심볼 참조 추출 성공
- [시도] httpx check --threshold 50 → [결과] 17건 경고, exit code 1 반환 성공
- [시도] JSON 출력 → [결과] 성공
- [구조] 5개 모듈: symbol_extractor, git_tracker, scorer, reporter, cli

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 대체로 "오 되네". httpx에서 93점(close 함수), Flask에서 97점(redirect/url_for) 등 실제 의미 있는 stale 경고 생성
- [평가] Spec 검증 목표 → 충족. staleness score가 실제 "코드는 바뀌었는데 문서는 안 바뀐" 상황을 정확히 감지
- [평가] 출력 → 마크다운 테이블 깔끔, JSON도 정상 동작
- [불만] 코드 블록 내부 심볼이 추출됨 (code block tracking 미비) → [개선] in_code_block 상태 추적 추가
- [불만] `g`, `it` 등 1-2글자 일반 심볼이 false positive → [개선] MIN_SYMBOL_LEN=2 + GENERIC_SYMBOLS 필터 추가
- [불만] .rst 파일 미지원 → [개선] DOC_GLOBS에 .rst 패턴 추가 (Phase 2에서 이미 수정)

## Phase 4 — 검증
- [체크] `doc-freshness scan` 매핑 테이블 출력 → 통과 (httpx: 314개 심볼, Flask: 다수)
- [체크] staleness score 0-100 산출 → 통과 (httpx: 0-93 범위, 23건 > 0)
- [체크] `--threshold 50` 경고 + exit code 1 → 통과 (httpx: 11건 경고, exit code 1)
- [체크] JSON/Markdown 포맷 리포트 → 통과 (둘 다 정상 출력)
- [체크] 오픈소스 프로젝트에서 의미 있는 stale 경고 3건+ → 통과 (httpx: 11건, Flask: 40건)
- [결과] 5/5 항목 통과 → **SUCCESS**

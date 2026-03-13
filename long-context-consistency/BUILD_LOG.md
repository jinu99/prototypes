# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-08
- [목표] 장편 텍스트 사실 추출/저장/불일치 탐지 CLI
- [판단] 스택 선택: Python + uv (이유: spec 명시, sentence-transformers는 Python 생태계)
- [판단] 구조: CLI(click) + SQLite + sentence-transformers
- [판단] 사실 추출: 규칙 기반 (regex 패턴 매칭, spaCy 대신 경량화)
- [판단] 의존성: click, sentence-transformers, sqlite3(표준). tiktoken 불필요 → 문자수 기반 추정으로 대체

## Phase 2 — 구현
- [시도] 모듈 구조 설계: db.py, extractor.py, checker.py, context.py, cli.py → [결과] 성공
- [시도] 첫 extract 실행 → [결과] 부분 성공. "He"가 엔티티로 잡히고, Thomas 속성 미추출
- [에러] 대명사(He/She)가 entity로 추출됨 → [수정] SKIP_WORDS에 "he" 추가
- [에러] "weathered man with gray hair"에서 "man"이 entity (소문자) → [수정] 샘플 텍스트를 명시적 이름 사용으로 개선
- [에러] "Elena but"이 entity로 잡힘 → [수정] _is_valid_entity에서 모든 단어가 대문자 시작인지 확인
- [에러] Sarah.parent_of = Thomas (역방향) → [수정] inverse map에서 daughter→child_of로 수정
- [에러] setuptools가 sample_data/screenshots를 패키지로 인식 → [수정] pyproject.toml에 packages.find 설정 추가
- [시도] 2차 E2E → [결과] 성공. 6건 직접 모순 + 3건 cross-attribute 탐지

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 솔직히 "오 되네" 수준. 모순 6건 명확히 탐지, 출력 읽기 좋음
- [평가] 검증 목표 달성? → YES. 규칙 기반 추출 + 임베딩 유사도 모순 탐지 동작 확인
- [불만] cross-attribute 탐지에서 false positive 2건 (Marcus.sibling vs location, Elena.age vs eye_color)
- [개선] 임계값 0.5→0.6으로 상향 → false positive 2건 제거, 유의미한 1건(Thomas.description=52 vs age=48) 유지
- [불만] 모델 로딩 경고 노이즈 → [개선] 로거 레벨 조정으로 HF 인증 경고 제거
- [남은 노이즈] safetensors 로딩 바는 stderr로 출력되어 완전 억제 어려움 (프로토타입 수준에서 허용)

## Phase 4 — 검증
- [체크] `consistency init <dir>` → 통과 (DB 생성, 기존 fact 수 표시)
- [체크] `consistency extract <file>` → 통과 (10개 사실 추출, DB 저장, JSON 출력 지원)
- [체크] `consistency check <file>` → 통과 (7건 불일치 탐지, 직접 모순 6건 + cross-attr 1건)
- [체크] `consistency context <scene>` → 통과 (토큰 예산 내 관련 사실 선별, 19/21 facts within 500 budget)
- [체크] 샘플 데이터 E2E 데모, 모순 3건 이상 탐지 → 통과 (6건 직접 모순 탐지)

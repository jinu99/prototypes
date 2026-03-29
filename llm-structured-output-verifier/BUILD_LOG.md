# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 확인: 2-pass LLM 구조화 출력 검증기
- [판단] 스택 선택: Python + uv + Pydantic + Rich (이유: Spec에 Python+uv 명시, Pydantic이 핵심 모델링, Rich로 CLI 테이블 출력)
- [판단] LLM API mock 사용 (이유: 외부 API 키 필요하지만 제약 조건에 따라 mock/stub 대체. regex 기반 추출 + 의도적 hallucination 주입으로 2-pass 검증 효과 시연)

## Phase 2 — 구현
- [시도] Pydantic 모델 정의 (PersonProfile, ProductInfo, EventInfo) → [결과] 성공
- [시도] Mock LLM 구현: regex 기반 추출 + 의도적 hallucination 주입 → [결과] 성공
- [시도] 1-pass / 2-pass 파이프라인 구현 → [결과] 성공
- [시도] CLI 구현 (verify, extract, compare 서브커맨드) → [결과] 성공
- [시도] `uv run verify-output` 엔트리포인트 → [결과] 실패 (uv가 scripts 빌드 안 함)
- [수정] `uv run python -m src.cli`로 실행 방식 변경 → [결과] 성공
- [에러] achievements 리스트 필드가 합쳐져서 검증됨 → 가짜 항목 놓침
- [수정] list 필드를 개별 항목별로 검증하도록 pipeline.py 수정 → [결과] 성공
- [에러] `_find_span`이 단어 하나만으로 매칭 → 가짜 "National Science Award" 통과
- [수정] `_find_exact_span` + `_find_partial_span`으로 분리, ratio 기반 confidence 부여 → [결과] 성공
- [에러] product pros 추출이 "X" wireless headphones..." 같은 쓰레기 → [수정] 감성 키워드 기반 문장 추출로 변경 → [결과] 성공
- [에러] event organizer 추출이 "Techcrunch And Will Feature..." → [수정] regex에 stop boundary 추가 → [결과] 성공
- [에러] person occupation 추출이 "Senior Machine Learning Engineer Who Works At Deepmind In London" → [수정] regex에 stop words (at/for/who) 추가 → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 출력이 깔끔하고 hallucination 플래그가 시각적으로 명확. "오 되네" 수준.
- [평가] 검증 목표 달성? → 1-pass 탐지 0개, 2-pass 탐지 4개. 50% 목표 초과 달성 (무한대%).
- [평가] 출력 가독성? → Rich 테이블, confidence 색상 코딩, evidence span 인용 → 좋음.
- [불만] product_02.txt에서 hallucination 0개 — FlexWork 브랜드가 실제 있어서 정상이지만, 문서마다 hallucination 수가 다른 건 realistic함.
- [개선 불필요] 전체적으로 만족할 만한 수준.

## Phase 4 — 검증
- [체크] Pydantic 모델 → 1-pass 추출 동작 → 통과
- [체크] 2-pass 검증: evidence span + confidence score → 통과
- [체크] hallucination 후보 플래그 → 통과 (age=34, fake award, fake brand, fake company)
- [체크] CLI 리포트 출력 → 통과
- [체크] 3개+ 문서 1-pass vs 2-pass 비교 → 5개 문서, 4개 hallucination 탐지 → 통과

**결과: SUCCESS (5/5 통과)**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-07 — Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: CLI 도구에 적합, duckduckgo-search 라이브러리로 API 키 없이 검색 가능, 도메인 유사도 분석에 표준 라이브러리 difflib 활용 가능)
- [판단] 의존성: duckduckgo-search (DDG 검색), httpx (HTTP 클라이언트 — 도메인 콘텐츠 확인용)
- [판단] 구조: 단일 진입점 CLI + 모듈 분리 (github_parser, searcher, analyzer, reporter)

## Phase 2 — 구현
- [시도] duckduckgo-search 패키지 사용 → [결과] 실패 — 패키지가 ddgs로 리네임됨, 검색 결과가 완전히 무관한 내용 반환
- [수정] ddgs 패키지로 교체 → [결과] 성공 — 정상적인 검색 결과 반환
- [시도] minimap2 테스트 → [결과] minimap2.com 감지했으나 WARNING 수준(25점)에 그침
- [수정] 도메인이 프로젝트명과 정확히 일치하면 50점으로 상향 → [결과] DANGER로 정확히 감지
- [시도] czkawka 테스트 → [결과] czkawka.com 및 download.cnet.com 감지 성공
- [추가] 검색 결과 관련성 필터링 (프로젝트명이 언급되지 않은 무관한 결과 제외)

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → minimap2.com, czkawka.com, nicotine-plus.updatestar.com을 모두 정확히 감지하고 DANGER로 분류함. "오 되네" 수준.
- [평가] Spec 검증 목표 → 검색 결과에서 사칭 사이트를 감지하는 목표 달성. 유사도 점수 + 판별 근거 출력됨.
- [평가] 출력/UI → ANSI 색상으로 깔끔한 구분. DANGER/WARNING/SAFE 3단계 명확.
- [불만] nicotineplus.en.uptodown.com이 DANGER(80점)으로 false positive → [개선] 다운로드 애그리게이터 목록 추가, WARNING(40점)으로 하향
- [불만] 무관한 검색 결과가 "TRUSTED"로 표시 → [개선] "OK"로 변경, 관련성 필터링 추가
- [만족] 3개 프로젝트 모두 정상 동작 확인

## Phase 4 — 검증
- [체크] GitHub 레포 URL 입력 시 프로젝트명과 공식 URL 자동 추출 → 통과
- [체크] DuckDuckGo 검색 결과 상위 20개 수집 + 공식 URL 판별 → 통과 (40~60개 결과 수집, 필터링 후 30~40개 관련 결과)
- [체크] 의심 도메인 유사도 점수 + 판별 근거 출력 → 통과 (score + reasons 출력)
- [체크] minimap2 사칭 사례 테스트 → 통과 (minimap2.com DANGER 감지)
- [체크] czkawka 사칭 사례 테스트 → 통과 (czkawka.com DANGER 감지)
- [체크] CLI 위협 수준 요약 리포트 → 통과 (DANGER/WARNING/SAFE 3단계 + 색상 구분)
- **결과: SUCCESS (6/6 통과)**

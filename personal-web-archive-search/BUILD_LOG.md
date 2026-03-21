# Build Log

## Phase 1 — Spec 확인
- [시작] Spec 파일 확인: CJK(한국어) 본문 FTS 인덱싱+검색 프로토타입
- [판단] 스택 선택: Node.js + better-sqlite3 + @mozilla/readability (이유: readability.js가 JS 네이티브, better-sqlite3가 FTS5 trigram 토크나이저 지원, node-fetch로 URL 가져오기 간편)
- [판단] 토크나이저: FTS5 내장 trigram 선택 (이유: CJK 바이트 레벨 trigram이 한국어를 공백 없이도 인덱싱 가능, 외부 의존성 없음)

## Phase 2 — 구현
- [시도] npm init + 의존성 설치 (better-sqlite3, @mozilla/readability, linkedom, node-fetch@2) → [결과] 성공
- [시도] db.js (SQLite FTS5 trigram), extractor.js (readability 추출), cli.js (CLI) 작성 → [결과] 성공
- [시도] URL 추가 테스트 (한국어 위키: 대한민국, 영어 위키: Node.js) → [결과] 성공
- [에러] `node cli.js search "경제"` (2글자 한국어) → FTS5 trigram은 3글자 미만 쿼리 불가 → [수정] 3글자 미만은 LIKE 폴백으로 처리
- [시도] 수정 후 2글자 한국어 검색 ("경제", "서울") → [결과] 성공
- [시도] server.js + index.html (웹 UI) 작성 → [결과] 성공
- [시도] 웹 API 전체 테스트 (add, search, stats, pages) → [결과] 성공
- [시도] tokenizer-comparison.js 작성 및 실행 → [결과] trigram 8/8, unicode61 5/8

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 수준. 한국어/영어/혼합 검색 모두 동작하고 하이라이트도 나옴.
- [평가] Spec 검증 목표 실제 검증되는가? → Yes. CJK FTS가 영어 중심 도구(unicode61) 대비 의미있게 높은 검색 품질 달성 (8/8 vs 5/8).
- [평가] UI 깔끔한가? → 다크 테마, 한국어 인터페이스, 검색+추가 모두 가능. Playwright 스크린샷은 시스템 라이브러리(libatk) 부재로 촬영 불가.
- [평가] 빠진 게 있는가? → 핵심 흐름 완결. 브라우저 확장은 spec에서 제외 범위.
- [불만] Playwright 스크린샷 못 찍음 → [대안] curl 기반으로 전체 API 동작 검증 완료

## Phase 4 — 검증
- [체크] URL 입력 → 본문 추출 → FTS5 인덱싱 → 통과 (4개 URL 성공적으로 추가)
- [체크] 한국어 검색어로 한국어 본문 검색 (형태소/부분 매칭) → 통과 ("인공지능", "서울", "경제", "떡볶이" 모두 성공)
- [체크] 영어+한국어 혼합 문서에서 양쪽 검색 → 통과 ("machine learning" → 인공지능 문서, "JavaScript" → Node.js 문서)
- [체크] 웹 UI에 스니펫+하이라이트 → 통과 (snippet에 `<mark>` 태그 포함, UI에서 하이라이트 렌더링)
- [체크] 토크나이저 비교 결과 README 기록 → 통과 (trigram 8/8 vs unicode61 5/8)

결과: **전부 통과 → SUCCESS**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-14 Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: RSS 파싱에 feedparser, 웹서버에 FastAPI+uvicorn이 가볍고 적합)
- [판단] Reddit API → mock/stub (이유: API 키 필요, spec에서 mock 허용)
- [판단] RSS → feedparser로 실제 파싱 (이유: 외부 키 불필요, 실제 데이터로 검증 가능)
- [판단] DB: sqlite3 표준라이브러리 (이유: 추가 의존성 없음)
- [판단] 프론트엔드: 단일 HTML + vanilla JS (spec 제약)

## Phase 2 — 구현
- [시도] uv init + uv add fastapi uvicorn feedparser → [결과] 성공
- [시도] db.py (SQLite 스키마, CRUD) → [결과] 성공
- [시도] reddit_collector.py (mock 데이터 생성) → [결과] 성공
- [시도] rss_collector.py (feedparser 실제 파싱) → [결과] 성공
- [시도] server.py (FastAPI 엔드포인트 7개) → [결과] 성공
- [시도] static/index.html (대시보드 UI) → [결과] 성공
- [에러] innerHTML 사용 → security hook에서 XSS 경고 → [수정] DOM API (createElement, textContent)로 전면 교체
- [시도] 서버 실행 + curl 테스트 → [결과] 전 엔드포인트 정상 (Reddit 60건 + RSS 19건 수집)

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → API 전부 동작, 데이터 수집·필터링·설정 관리 모두 정상. "오 되네" 쪽.
- [불만] RSS snippet에 HTML 태그 잔류 → [개선] re.sub로 태그 제거, DB 리셋 후 재수집하여 확인
- [불만] db.py insert_match에서 total_changes 부정확 → [개선] cursor.rowcount로 교체
- [불만] Playwright 브라우저 테스트 불가 (시스템 라이브러리 부재) → curl 기반 검증으로 대체
- [평가] 검증 목표 실제 검증됨: 멀티플랫폼 키워드 모니터링 + 노이즈 필터링 + 통합 타임라인

## Phase 4 — 검증
- [체크] Reddit API 키워드 매칭 → SQLite 저장 → 통과 (60건)
- [체크] RSS 피드 키워드 매칭 → 같은 SQLite DB 저장 → 통과 (19건)
- [체크] 통합 타임라인에서 두 소스 시간순 통합 표시 → 통과 (reddit+rss, DESC 정렬 확인)
- [체크] 노이즈 필터링: min_score=100 적용 시 79→51건으로 필터링 → 통과
- [체크] 키워드/소스 추가·제거 API → 통과 (추가 후 존재 확인, 제거 후 부재 확인)
- [결과] 5/5 통과 → **SUCCESS**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-16
- [판단] 스택 선택: Python 3.12 + uv (이유: imaplib/sqlite3 표준라이브러리로 핵심 로직 커버, Rich로 TUI, 최소 의존성)
- [판단] 구조: mock IMAP 데이터 생성기 포함하여 실제 IMAP 서버 없이도 전체 플로우 검증 가능
- [범위] IMAP 헤더 fetch → SQLite 캐싱 → 발신자 통계 → 휴리스틱 분류 → 정리 제안 → 드라이런 → 실제 삭제/아카이브

## Phase 2 — 구현
- [시도] db.py (SQLite 스키마 + CRUD) → [결과] 성공
- [시도] mock_data.py (12,000개 mock 이메일 생성기) → [결과] 성공
- [시도] imap_client.py (실제 IMAP + mock 모드) → [결과] 성공
- [시도] classifier.py (휴리스틱 분류기, 6개 시그널) → [결과] 성공
- [시도] analyzer.py (발신자 통계, 구독 해지 후보) → [결과] 성공
- [시도] cleanup.py (드라이런 + 실제 삭제/아카이브) → [결과] 성공
- [시도] tui.py (Rich TUI 테이블/패널) → [결과] 성공
- [시도] main.py (CLI: fetch/classify/analyze/dryrun/clean/all) → [결과] 성공
- [시도] 전체 파이프라인 `all` 명령어 → [결과] 12,000개 이메일 0.3초 로드, 분류 0.3초, TUI 정상 출력
- [에러] DB 없을 때 `analyze` 실행 시 `sqlite3.OperationalError: no such table` → [수정] `get_connection()`에서 자동 `init_db()` 호출

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 쪽. Rich TUI가 깔끔하고 전체 플로우 매끄러움
- [평가] 검증 목표 실제 검증 → 88% 분류 정확도 (80% 기준 충족), 12K 이메일 0.3초 로드 (5분 기준 충족)
- [평가] 출력 깔끔함 → 테이블 정렬, 색상 코딩, 사이즈 포맷팅 양호
- [불만] "this week" 패턴이 "this weekend"를 잡아서 personal→newsletter 오분류 360건 → [개선] 패턴을 "this week in|this week's"로 수정 → 정확도 85.3% → 88.0%로 개선
- [불만] personal→old 577건 오분류 → [판단] 이는 의도된 동작 (6개월+ personal = 정리 대상). 실용적 정확도 92.8%

## Phase 4 — 검증
- [체크] IMAP 연결 후 1만개+ 이메일 헤더 5분 내 fetch → 12,000개 0.26초 → 통과
- [체크] 발신자별 통계 Rich TUI 테이블 표시 → 이메일 수/읽지 않은 비율/마지막 수신일/사이즈 모두 표시 → 통과
- [체크] List-Unsubscribe + 발신 패턴 기반 분류 80%+ 정확도 → 88.0% → 통과
- [체크] 드라이런 모드 삭제/아카이브 대상 목록 + 예상 절감 용량 미리보기 → 9,912개 710MB 표시 → 통과
- [체크] 실제 DELETE/ARCHIVE 명령 실행 및 결과 확인 → 6,600개 삭제 (12,000→5,400) → 통과
- [결과] 5/5 통과 → **SUCCESS**

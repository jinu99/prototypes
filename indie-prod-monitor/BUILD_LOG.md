# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-19 — Spec 읽기 완료
- [범위] stdin/HTTP 로그 수신 → simhash 클러스터링 → 새 에러 알림 + 헬스체크 + 하트비트
- [판단] 스택 선택: Go + modernc.org/sqlite (이유: spec에 명시된 기술 제약. CGo-free 단일 바이너리)
- [판단] HTTP 프레임워크: 표준 라이브러리 net/http (이유: 외부 의존성 최소화, 라우팅 복잡도 낮음)
- [판단] Simhash: 직접 구현 (이유: 알고리즘 단순, 외부 라이브러리 불필요)
- [판단] 알림: stdout mock + ntfy HTTP POST (이유: 외부 API 키 불필요, ntfy는 인증 없이 사용 가능)
- [판단] 설정: YAML/TOML 대신 CLI 플래그 + 환경변수 (이유: 제로 설정 지향)

## Phase 2 — 구현
- [시도] Go 설치 → sudo 불가 → 유저 디렉토리에 설치 → 성공
- [시도] go mod init + modernc.org/sqlite → Go 1.25 자동 전환 (modernc.org/sqlite 최신 버전 요구) → 성공
- [시도] 첫 빌드 → 성공
- [시도] stdin 파이프 테스트 → [에러] uint64 high bit set 오류 (SQLite 드라이버가 uint64 상위 비트 미지원)
- [수정] hash를 int64로 캐스팅하여 저장/로드 → 재빌드 → 성공
- [시도] stdin 파이프 재테스트 → 7줄 입력, 5클러스터 생성 (유사 로그 2건 기존 클러스터에 매칭) → 성공
- [시도] HTTP 엔드포인트 테스트 (ingest, healthcheck, heartbeat, status) → 모두 정상 동작
- [결과] "database timeout 30s"와 "45s"가 같은 클러스터로 묶임 → simhash 클러스터링 정상

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 쪽. 파이프 연결 즉시 동작, 새 에러 즉시 감지
- [불만] INFO/DEBUG 로그도 새 클러스터로 알림됨 → [개선] --level 플래그 추가, 기본값 warn
- [불만] timestamp가 simhash에 영향 → [개선] stripTimestamps로 로그 레벨 키워드 앞의 내용 제거
- [불만] heartbeat RecordBeat이 미등록 이름에 silent fail → [개선] auto-create 로직 추가
- [불만] 단일 문자 토큰이 noise → [개선] 2자 이상만 토큰으로 사용
- [재테스트] 9줄 → 5클러스터, INFO/DEBUG 필터링 정상, 중복 매칭 정상
- [추가개선] SQLite WAL 모드 + busy_timeout 추가 (concurrent access 에러 해결)

## Phase 4 — 검증
- [체크] stdin 파이프 로그 수신 + simhash 클러스터링 → 통과 (5줄→4클러스터, 유사 에러 매칭)
- [체크] 새 에러 클러스터 등장 시 알림 → 통과 ([ALERT:new_cluster] stdout mock 동작)
- [체크] HTTP 헬스체크 등록 + 주기적 ping + 실패 알림 → 통과 (broken URL → fail + alert)
- [체크] 크론잡 하트비트 + 미수신 알림 → 통과 (5s 간격, 30s 후 overdue 감지 + alert)
- [체크] 단일 Go 바이너리 빌드 → 통과 (15MB, CGo-free, modernc.org/sqlite)
- [결과] 5/5 통과 → SUCCESS

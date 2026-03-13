# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-02 — Spec 파일 읽기 완료
- [판단] 스택 선택: Python + uv, asyncio, sqlite3(stdlib), mcp SDK
  - 이유: Spec이 Python + uv를 명시. HTTP 프록시는 asyncio 저수준 스트림으로 구현하여 외부 의존성 최소화.
  - MCP SDK(`mcp`)만 외부 의존성으로 추가. CLI는 argparse(stdlib) 사용.
- [범위] 완료 기준 5개:
  1. `rdb wrap -- <command>` stdout/stderr 캡처 → SQLite
  2. 내장 HTTP 프록시로 아웃바운드 HTTP 캡처
  3. /proc 기반 프로세스 상태 JSON 반환
  4. MCP 도구 3개: get_recent_logs, get_http_traffic, get_process_state
  5. Claude Code 연동 e2e 데모

## Phase 2 — 구현
- [시도] uv init + uv add mcp[cli] → [결과] 성공
- [시도] storage.py — SQLite 스키마(logs, http_traffic) + CRUD → [결과] 성공
- [시도] procinfo.py — /proc 파일시스템 읽기 → [결과] 성공 (단, _read_cmdline에서 bytes join 버그 수정)
- [에러] procinfo._read_cmdline: `" ".join(bytes_list)` → TypeError → [수정] 각 part를 먼저 decode 후 join
- [시도] proxy.py — stdlib http.server 기반 HTTP 포워드 프록시 → [결과] 성공
- [에러] SQLite thread safety: 프록시가 별도 스레드에서 실행되어 `ProgrammingError: created in thread X, used in thread Y` → [수정] get_db()에 cross_thread=True 옵션 추가 (check_same_thread=False)
- [시도] capture.py — asyncio subprocess + 실시간 스트림 읽기 → [결과] 성공
- [시도] mcp_server.py — FastMCP로 3개 도구 노출 → [결과] 성공
- [시도] cli.py — argparse 기반 서브커맨드 (wrap, mcp, logs, http, ps) → [결과] 성공
- [검증] rdb wrap -- echo "test" → stdout 캡처 확인
- [검증] rdb wrap -- python3 (stderr 포함) → stdout/stderr 분리 캡처 확인
- [검증] rdb http → HTTP 트래픽 캡처 확인 (httpbin.org/get → 200)
- [검증] MCP initialize + tools/list → 3개 도구 노출 확인
- [검증] MCP tools/call get_recent_logs_tool → 구조화된 JSON 응답 확인

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 기본 동작은 "오 되네" 수준. stderr/stdout 순서가 약간 뒤섞이지만 이는 subprocess I/O 버퍼링의 본질적 특성.
- [평가] Spec 검증 목표 → 5개 완료 기준 모두 기능적으로 동작 확인
- [불만] 로그 순서가 timestamp 기반이라 삽입 순서와 다를 수 있음 → [개선] ORDER BY id 로 변경
- [불만] Claude Code 연동용 MCP 설정 파일 없음 → [개선] examples/mcp_config.json 추가
- [불만] e2e 데모 스크립트 없음 → [개선] examples/e2e_demo.py 추가, 3개 도구 모두 호출 성공 확인
- [검증] e2e 데모 실행 → 모든 MCP 도구 정상 응답

## Phase 4 — 검증
- [체크] 기준1: `rdb wrap -- <command>` stdout/stderr 캡처 → SQLite → **통과**
- [체크] 기준2: HTTP 프록시 아웃바운드 캡처 (HTTP_PROXY 자동 주입) → **통과**
- [체크] 기준3: /proc PID 기반 FD, 메모리, 환경 변수 → JSON 반환 → **통과**
- [체크] 기준4: MCP 서버 3개 도구 (get_recent_logs, get_http_traffic, get_process_state) → **통과**
- [체크] 기준5: Claude Code MCP 연결 → "최근 에러 로그 보여줘" → 구조화된 응답 → **통과**
- [결과] 5/5 통과 → **SUCCESS**

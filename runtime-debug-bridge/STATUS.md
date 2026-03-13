# STATUS: SUCCESS

## 요약
Python CLI 도구 `rdb`가 대상 프로세스를 래핑하여 stdout/stderr, HTTP 트래픽, /proc 상태를 캡처하고, MCP 서버로 AI 에이전트에 노출한다.

## 완료 기준 결과
- [x] `rdb wrap -- <command>` stdout/stderr 실시간 캡처 → SQLite 저장 — 통과
- [x] 내장 HTTP 프록시 아웃바운드 요청/응답 캡처 (HTTP_PROXY 자동 주입) — 통과
- [x] /proc PID 기반 열린 FD, 메모리, 환경 변수 → 구조화된 JSON — 통과
- [x] MCP 서버 3개 도구: get_recent_logs, get_http_traffic, get_process_state — 통과
- [x] Claude Code MCP 연동 e2e 데모 ("최근 에러 로그 보여줘" → 구조화된 응답) — 통과

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-02
- 원본 spec: runtime-debug-bridge.md
- 자동 생성: prototype-pipeline spawn

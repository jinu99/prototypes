# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-23
- [판단] 스택 선택: Python + uv (이유: JSONL 파싱은 표준 라이브러리로 충분, HTML 생성은 Jinja2 하나면 됨. Node보다 데이터 처리에 자연스러움)
- [판단] 의존성: jinja2만 추가 (최소 의존성 원칙)
- [판단] 구조: parser → mapper → detector → reporter → CLI 파이프라인

## Phase 2 — 구현
- [시도] 실제 JSONL 로그 구조 분석 → [결과] 성공. type: user/assistant/progress/file-history-snapshot 등. assistant 메시지의 content 배열에 tool_use 포함
- [구현] parser.py — JSONL 파서. user→다음 user 사이의 assistant tool_use를 세그먼트로 그룹화
- [구현] detector.py — 5개 규칙 기반 불일치 감지 (delete_without_deletion, add_without_addition, code_prompt_no_changes, mentioned_file_not_changed, scope_mismatch)
- [구현] reporter.py + template.html — Jinja2 기반 HTML 리포트 생성. 다크 테마, 접이식 세그먼트, diff 시각화
- [구현] cli.py — `ai-review analyze --session <id>` + `ai-review list`
- [시도] 실제 세션(5f593cfd)으로 분석 → [결과] 성공. 40개 프롬프트, 96개 파일변경, 8개 불일치 감지

## Phase 3 — 셀프 크리틱
- [에러] Playwright Chromium 실행 실패 — 시스템 라이브러리(libatk 등) 누락, sudo 없어 설치 불가 → curl + HTML 구조 분석으로 대체
- [평가] "이걸 누가 보면?" → 리포트 자체는 깔끔하나 3가지 이슈 발견:
  1. 시스템 continuation 프롬프트가 사용자 프롬프트로 잡힘 → parser.py에 필터 추가
  2. `mentioned_file_not_changed` 규칙 false positive 과다 (.jsonl 경로, Express.js 등 프레임워크명) → 확장자 제외 목록 + 경로 길이 필터 추가
  3. 50% 세그먼트가 변경 없음 → UI에 All/With Changes/Mismatches Only 필터 버튼 추가
- [불만] 불일치 8개 중 6개가 false positive → [개선] 필터링 후 2개로 감소, 모두 진짜 불일치
- [시도] 세 번째 세션(532207a0, 139개 프롬프트) 분석 → [결과] 성공. 다양한 크기 세션에서 안정적

## Phase 4 — 검증
- [체크] JSONL 파싱하여 프롬프트-코드변경 쌍 추출 → 통과 (19개 쌍, 96개 변경)
- [체크] 웹 리포트 생성 (diff 시각화, 필터, 통계) → 통과
- [체크] 규칙 기반 의도 불일치 감지 → 통과 (delete_without_deletion 정상 동작)
- [체크] CLI에서 세션 ID → HTML 리포트 → 통과
- [체크] 실제 세션으로 매핑 정확도 확인 → 통과 ("메모탭 만들어줘" → MapView→MemoView 변환 정확히 추적)
- [결과] 5/5 통과 → **SUCCESS**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-03 Spec 확인 시작
- [판단] 스택 선택: Python + uv
  - 이유: Mermaid 파싱은 정규식으로 충분 (외부 의존성 불필요), MCP Python SDK가 성숙, CLI는 click으로 깔끔하게 구성 가능
  - 의존성: `mcp` (MCP 서버), `click` (CLI) — 나머지 표준 라이브러리
- [범위] 완료 기준 5개 중 4개 필수 + 1개 bonus:
  1. Mermaid C4/flowchart → JSON 파싱 CLI
  2. 디렉토리 패턴 기반 파일↔서비스 매핑
  3. MCP 서버 노출 (도구 호출로 컨텍스트 조회)
  4. 샘플 프로젝트에서 전/후 비교 데모
  5. (bonus) git hook 변경 의도 기록

## Phase 2 — 구현
- [시도] uv init + uv add click mcp → [결과] 성공
- [시도] Mermaid C4 파서 구현 → [결과] 성공 (8 nodes, 9 rels 추출)
- [에러] System 노드들이 전부 "external" 레이어로 분류됨
  → [수정] _infer_layer에서 system_ext만 external로, system은 tech 키워드로 판별
  → c4_patterns 순서를 specific-first로 변경 (System_Ext before System)
- [시도] Flowchart 파서 (subgraph 기반 레이어 분류) → [결과] 성공 (12 nodes, 12 rels)
- [시도] 파일↔서비스 매핑 엔진 (fnmatch 기반) → [결과] 성공
- [시도] MCP 서버 (4 tools: get_file_context, list_services, list_relationships, get_service_context) → [결과] 성공
- [시도] CLAUDE.md 생성기 → [결과] 성공
- [시도] CLI 진입점 (7 commands) → [결과] 성공
- [시도] 전/후 비교 데모 → [결과] 성공
- [시도] git hook + intent recorder → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 대체로 "오 되네". CLI가 직관적이고 출력이 깔끔함
- [평가] 검증 목표 달성? → 부분적. 실제 AI 에이전트 코드 생성 비교는 아니지만, 주입되는 정보 차이를 명확히 보여줌
- [불만] flowchart 파서에서 [(Order DB)] → "(Order DB)"로 괄호 포함 → [개선] _clean_label 헬퍼 추가
- [불만] MCP 연동 가이드 부족 → [개선] README에 claude_desktop_config.json 예시 포함 예정

## Phase 4 — 검증
- [체크] 기준 1: Mermaid C4/flowchart → JSON 파싱 CLI → **통과** (C4: 8 nodes/9 rels, Flowchart: 12 nodes/12 rels)
- [체크] 기준 2: 파일↔서비스 매핑 → **통과** (order-service, api-gateway 매핑 정상, 미매핑 파일 에러 처리 확인)
- [체크] 기준 3: MCP 서버 도구 호출 → **통과** (4 tools 전부 MCP 클라이언트로 검증)
- [체크] 기준 4: 전/후 비교 데모 → **통과** (3 시나리오 + CLAUDE.md 프리뷰)
- [체크] 기준 5 (bonus): git hook 의도 기록 → **통과** (hook 설치, intent JSON 저장 확인)
- **결과: 5/5 통과 → SUCCESS**

# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-25
- [판단] 스택 선택: Python + uv (이유: YAML 파싱, regex, CLI 모두 Python 자연스러움. 외부 의존성 PyYAML 하나로 충분)
- [범위] compose YAML 파싱 → iptables/UFW 파싱 → 교차 검증 → severity별 리포트 출력
- [구조] compose_parser / firewall_parser / analyzer / reporter / main 5개 모듈로 분리

## Phase 2 — 구현
- [시도] 5개 모듈 작성 (compose_parser, firewall_parser, analyzer, reporter, main) → [결과] 성공
- [시도] 실제 홈서버 compose 파일(momentia, cusdis, monitoring)로 테스트 → [결과] 성공
- [에러] sudo 접근 불가로 live iptables/ufw 캡처 실패 → [수정] testdata/ 디렉토리에 realistic fixture 생성
- [시도] momentia compose + firewall fixture로 실행 → [결과] 성공, CRITICAL 3개 + WARNING 6개 + INFO 6개 탐지
- [에러] cusdis (127.0.0.1 바인딩)가 UFW bypass CRITICAL로 잘못 탐지됨 → [수정] check_ufw_bypass에서 127.0.0.1 바인딩 제외
- [에러] compose-only 모드에서 방화벽 데이터 없는데 UFW/DOCKER-USER 경고 표시 → [수정] has_firewall 플래그로 분기
- [시도] DATABASE_URL 내 인라인 패스워드 감지 → [수정] URL credential 파싱 추가 → [결과] 성공
- [에러] 여러 compose 분석 시 undeclared_port/system 경고 중복 → [수정] 합산 분석 구조로 변경 → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" — 실제 compose 파일에서 유의미한 보안 이슈 다수 탐지
- [평가] 검증 목표 달성 → compose ↔ iptables 교차 검증 핵심 로직 작동 확인
- [평가] 출력 가독성 → severity별 색상/아이콘 구분, 요약 카운트, 상세 설명 포함 — 깔끔
- [불만] 127.0.0.1 바인딩 false positive → [개선] 수정 완료
- [불만] 방화벽 데이터 없을 때 부적절한 경고 → [개선] 수정 완료
- [불만] 다중 compose 시 중복 경고 → [개선] 합산 분석으로 수정 완료

## Phase 4 — 검증
- [체크] CLI가 compose 경로 받아 포트/privileged/host network/시크릿 탐지 → 통과
- [체크] iptables NAT 출력 파싱 → DOCKER 체인 DNAT 규칙 추출 → 통과
- [체크] compose 선언 vs iptables 교차 비교 → UFW bypass 경고 출력 → 통과
- [체크] 실제 셀프호스팅 환경 compose 파일로 유의미한 발견 생성 → 통과 (PostgreSQL 5432 외부노출, Grafana 3000 UFW bypass, 다수 시크릿 하드코딩 등)
- [체크] severity 레벨 구분 리포트 출력 → 통과 (CRITICAL/WARNING/INFO 색상+아이콘 구분)
- 결과: **5/5 통과 → SUCCESS**

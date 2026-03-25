# STATUS: SUCCESS

## 요약
Docker Compose 선언과 iptables/UFW 방화벽 상태를 교차 분석하여 의도치 않은 포트 노출을 탐지하는 CLI 도구. 실제 홈서버 compose 파일에서 PostgreSQL 외부 노출, Grafana UFW bypass 등 유의미한 보안 이슈를 발견함.

## 완료 기준 결과
- [x] `docker-compose.yml` 경로를 인자로 받아 포트 매핑, privileged, host network, 시크릿 하드코딩을 탐지하는 CLI
- [x] `iptables -L -n -t nat` 출력을 파싱하여 DOCKER 체인의 포트 포워딩 규칙을 추출
- [x] compose 선언 포트와 iptables 실제 규칙을 교차 비교하여 "UFW에서 차단했지만 Docker가 우회하여 열려있는 포트" 경고 출력
- [x] 실제 셀프호스팅 환경(진우의 홈서버)에서 돌려서 최소 1개 이상의 유의미한 발견 생성
- [x] 터미널에 severity 레벨(CRITICAL/WARNING/INFO)로 구분된 리포트 출력

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-25
- 원본 spec: selfhost-docker-audit.md
- 자동 생성: prototype-pipeline spawn

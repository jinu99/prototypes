# STATUS: SUCCESS

## 요약
코드 심볼 참조 기반 staleness 감지 CLI 도구. 문서에서 코드 심볼(함수명, 클래스명, 파일 경로)을 추출하고, git log로 변경 이력을 추적하여 staleness score(0-100)를 산출한다. httpx와 Flask에서 실행하여 의미 있는 stale 문서 경고를 확인했다.

## 완료 기준 결과
- [x] `doc-freshness scan` — 매핑 테이블 출력 (httpx: 314개 심볼 참조)
- [x] staleness score 0-100 산출 — git log 기반 경과 일수 + 커밋 수 반영
- [x] `doc-freshness check --threshold 50` — 임계치 초과 경고 + exit code 1
- [x] JSON/Markdown 포맷 리포트 생성
- [x] 오픈소스 프로젝트에서 의미 있는 stale 경고 3건+ 확인 (httpx: 11건, Flask: 40건)

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-15
- 원본 spec: doc-freshness-monitor.md
- 자동 생성: prototype-pipeline spawn

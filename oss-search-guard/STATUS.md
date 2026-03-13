# STATUS: SUCCESS

## 요약
GitHub 레포 URL 입력 시 DuckDuckGo 검색 결과에서 사칭/가짜 사이트를 감지하는 CLI 도구. minimap2.com, czkawka.com 등 알려진 사칭 사례를 정확히 DANGER로 플래그.

## 완료 기준 결과
- [x] GitHub 레포 URL 입력 시 프로젝트명과 공식 URL을 자동 추출한다
- [x] DuckDuckGo 검색 결과 상위 20개를 수집하고, 공식 URL 여부를 판별한다
- [x] 의심 도메인에 대해 유사도 점수 + 판별 근거를 출력한다
- [x] 알려진 사칭 사례(minimap2, Czkawka 등)로 테스트했을 때 가짜 사이트를 정확히 플래그한다
- [x] CLI에서 위협 수준 요약 리포트를 출력한다

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-07
- 원본 spec: oss-search-guard.md
- 자동 생성: prototype-pipeline spawn

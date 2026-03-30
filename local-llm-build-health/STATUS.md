# STATUS: SUCCESS

## 요약
llama.cpp 릴리스 태그 2개를 자동 빌드·벤치마크하여 tok/s 비교 테이블 출력, SQLite 저장, 시계열 추이 조회, 크래시 감지까지 모든 완료 기준 통과.

## 완료 기준 결과
- [x] `build-health compare v1 v2` 명령으로 llama.cpp 2개 태그를 자동 다운로드·빌드·벤치마크하여 tok/s 비교 테이블 출력
- [x] 벤치마크 결과가 SQLite에 저장되고, `build-health history` 명령으로 시계열 추이 조회 가능
- [x] 빌드 또는 벤치마크 중 크래시(segfault, non-zero exit) 발생 시 명확한 경고 리포트 출력
- [x] README에 설치 방법과 사용 예시 포함

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-30
- 원본 spec: local-llm-build-health.md
- 자동 생성: prototype-pipeline spawn

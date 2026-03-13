# STATUS: SUCCESS

## 요약
Git diff에서 변경된 Python 함수를 AST로 식별하고, 기존 테스트를 벤치마크로 재활용하여 변경 전/후 성능을 비교하는 CLI 도구. 임계값 초과 시 경고 및 exit code 1 반환.

## 완료 기준 결과
- [x] `perf-verify` CLI 명령으로 현재 커밋의 변경 함수 목록 출력
- [x] 변경 전(HEAD~1)/후 코드에 대해 기존 테스트를 반복 실행하여 실행 시간 측정
- [x] before/after 성능 비교 리포트를 터미널에 테이블 형태로 출력
- [x] 임계값(기본 2x) 초과 시 경고 메시지 및 exit code 1 반환
- [x] 샘플 Python 프로젝트로 end-to-end 데모 동작 확인

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-08
- 원본 spec: ai-code-perf-verifier.md
- 자동 생성: prototype-pipeline spawn

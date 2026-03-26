# STATUS: SUCCESS

## 요약
AST 기반 정적 분석으로 Python 프로젝트의 의존성에서 고권한 API 사용을 탐지하고, transitive dependency를 포함한 blast radius 스코어를 계산하여 HTML 리포트를 생성하는 CLI 도구. LiteLLM(175개 패키지)에서 검증 완료.

## 완료 기준 결과
- [x] CLI가 Python 프로젝트 경로를 받아 의존성 목록을 추출한다
- [x] 각 의존성의 capability(네트워크, 파일시스템, 환경변수, 프로세스 실행, DB)를 AST 분석으로 탐지한다
- [x] Transitive dependency를 포함한 blast radius 점수를 계산한다
- [x] 상위 5개 고권한 의존성을 하이라이트하는 HTML 리포트를 생성한다
- [x] 실제 프로젝트(LiteLLM 등)에서 실행하여 결과가 직관과 일치함을 확인한다

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-26
- 원본 spec: high-privilege-dep-scanner.md
- 자동 생성: prototype-pipeline spawn

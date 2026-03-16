# STATUS: SUCCESS

## 요약
tree-sitter AST 기반 다언어(Python/JS/TS) 코드 스멜 린터. AI 생성 코드 특유의 구조적 위험 패턴 5개를 탐지하며, 기존 린터(Pylint/ESLint)가 잡지 못하는 패턴을 실제로 검증함.

## 완료 기준 결과
- [x] `aicslint scan <file>` 명령으로 단일 파일 스캔 후 JSON 결과 출력
- [x] AI 특유 패턴 5개 룰 구현 및 각각에 대한 테스트 코드 샘플로 탐지 시연
- [x] `aicslint diff` 명령으로 `git diff --staged` 기반 변경 코드만 스캔
- [x] 기존 린터(Pylint)가 잡지 못하는 패턴 2개(catch-rethrow, unnecessary abstraction) 비교 시연
- [x] Python + JS/TS 두 언어에서 동일 룰이 동작하는 다언어 데모

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-17
- 원본 spec: ai-code-smell-linter.md
- 자동 생성: prototype-pipeline spawn

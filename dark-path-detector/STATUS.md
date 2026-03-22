# STATUS: SUCCESS

## 요약
tree-sitter 기반 정적 분석으로 JS/TS 코드의 관측성 누락 에러 경로(dark path)를 탐지하는 CLI 도구. Express/Fastify 등 실제 오픈소스에서 precision 100%로 유효한 dark path를 찾아냄.

## 완료 기준 결과
- [x] CLI로 JS/TS 프로젝트 디렉토리를 스캔하여 dark path 목록을 출력한다
- [x] catch 블록 + 에러 콜백 파라미터 무시 패턴을 감지한다
- [x] 프로젝트 전체 dark path coverage 지표(%)를 산출한다
- [x] 실제 오픈소스 프로젝트(express, fastify)에 돌려서 결과의 유효성을 검증한다 (precision 100%, 목표 70% 이상)
- [x] `// @dark-path-ignore` 주석이 있는 경로는 결과에서 제외한다

## 실행 방법
```bash
npm install
node bin/cli.js <directory>
```

## 소요 정보
- 생성일: 2026-03-22
- 원본 spec: dark-path-detector.md
- 자동 생성: prototype-pipeline spawn

# STATUS: SUCCESS

## 요약
README.md를 파싱하여 3개 테마의 정적 HTML 랜딩페이지, 체인지로그, 런치 포스트 초안을 CLI 한 줄로 생성하는 Node.js 도구. 3개 서로 다른 README로 테스트 완료.

## 완료 기준 결과
- [x] `npx indie-launch-kit build`로 README.md → 정적 HTML 랜딩페이지 생성 (3개 테마 중 선택 가능) — 통과
- [x] README의 구조를 자동 파싱하여 Hero/Features/Install/CTA 섹션에 매핑 — 통과
- [x] conventional commits git log → 체인지로그 HTML 페이지 생성 — 통과
- [x] 프로젝트 메타데이터 기반 Product Hunt / Reddit / HN 런치 포스트 초안 텍스트 생성 — 통과
- [x] 실제 오픈소스 README 3개로 테스트하여 생성 결과물의 품질 확인 — 통과

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-15
- 원본 spec: indie-launch-kit.md
- 자동 생성: prototype-pipeline spawn

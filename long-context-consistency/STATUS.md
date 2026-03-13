# STATUS: SUCCESS

## 요약
장편 텍스트에서 규칙 기반으로 사실을 추출하고, sentence-transformers 임베딩으로 잠재적 불일치를 탐지하는 CLI 도구. 샘플 소설 데이터에서 의도적 모순 6건을 모두 정확히 탐지.

## 완료 기준 결과
- [x] `consistency init <dir>` — 통과: SQLite 사실 DB 생성
- [x] `consistency extract <file>` — 통과: 규칙 기반 사실 추출 + JSON 출력
- [x] `consistency check <file>` — 통과: 임베딩 유사도 기반 불일치 탐지 (직접 모순 6건 + cross-attr 1건)
- [x] `consistency context <scene>` — 통과: 토큰 예산 내 관련 사실 선별
- [x] 샘플 소설 데이터로 E2E 데모, 모순 3건 이상 탐지 — 통과 (6건)

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-08
- 원본 spec: long-context-consistency.md
- 자동 생성: prototype-pipeline spawn

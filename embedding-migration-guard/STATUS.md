# STATUS: SUCCESS

## 요약
임베딩 모델 교체 전 CLI 한 줄(`emg check`)로 recall@k 드롭을 예측하는 프로토타입. 두 sentence-transformers 모델 간 벡터 공간 비교(차원, cosine 분포, NN overlap)와 recall@k 측정을 수행하고, 리스크 등급(LOW/MEDIUM/HIGH)을 자동 판정한다.

## 완료 기준 결과
- [x] `emg check` 명령으로 두 모델 간 벡터 공간 차이 리포트 출력 (차원, cosine 분포, nearest-neighbor overlap) — 통과
- [x] 샘플 쿼리셋 기반 recall@k 비교 결과 출력 (old model vs new model) — 통과
- [x] 100개 이상 문서 코퍼스에서 30초 이내 검증 완료 — 통과 (110문서, 7.7초)
- [x] 검증 결과를 JSON으로 내보내기 (CI 파이프라인 연동용) — 통과
- [x] 내장 샘플 코퍼스로 `emg demo` 실행 시 전체 워크플로 시연 가능 — 통과

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-12
- 원본 spec: embedding-migration-guard.md
- 자동 생성: prototype-pipeline spawn

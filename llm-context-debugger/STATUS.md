# STATUS: SUCCESS

## 요약
OpenAI Chat Completions API 로컬 프록시로 컨텍스트 윈도우 구성을 실시간 분석·시각화하는 디버거. mock 모드 포함.

## 완료 기준 결과
- [x] 로컬 프록시가 OpenAI Chat Completions API 요청을 인터셉트하고 실제 API로 전달 — 통과
- [x] 각 요청의 messages를 role별로 분류하고, tools 정의를 포함하여 컴포넌트별 토큰 수를 tiktoken으로 카운팅 — 통과
- [x] 웹 대시보드에서 컴포넌트별 토큰 비율을 트리맵 또는 바 차트로 시각화 — 통과
- [x] 연속 호출 간 컨텍스트 diff를 대시보드에서 확인 가능 — 통과
- [x] 특정 컴포넌트가 전체 컨텍스트의 50% 초과 시 경고 표시 — 통과

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-08
- 원본 spec: llm-context-debugger.md
- 자동 생성: prototype-pipeline spawn

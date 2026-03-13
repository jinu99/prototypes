# STATUS: SUCCESS

## 요약
VRAM 사용량 기반 동적 어드미션 컨트롤로 로컬 LLM OOM을 방지하는 OpenAI-호환 리버스 프록시. 임계치 초과 시 큐잉/거부, 헬스체크 기반 백엔드 폴백을 지원한다.

## 완료 기준 결과
- [x] nvidia-smi에서 VRAM 사용률을 주기적으로 폴링하여 SQLite에 기록 — 통과
- [x] VRAM 임계치 초과 시 신규 요청을 큐잉하고, 여유 확보 시 자동 릴리스 — 통과
- [x] 복수 백엔드 등록 후, 헬스체크 실패 또는 VRAM 포화 시 자동으로 다음 백엔드로 폴백 — 통과
- [x] OpenAI-호환 /v1/chat/completions 엔드포인트가 정상 동작 (스트리밍 포함) — 통과
- [x] 동시 요청 부하 테스트에서 VRAM 어드미션 없는 경우 대비 OOM 발생률 감소 확인 — 통과

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-08
- 원본 spec: local-llm-serve-guard.md
- 자동 생성: prototype-pipeline spawn

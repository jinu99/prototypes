# STATUS: SUCCESS

## 요약
에이전트 세션 로그(JSONL)에서 실패-해결 패턴을 자동 추출하여 SQLite에 저장하고, CLAUDE.md / AGENTS.md / .cursor/rules 형식으로 내보내는 CLI 파이프라인. 3개 샘플 로그로 e2e 데모 동작 확인.

## 완료 기준 결과
- [x] CLI로 세션 로그 파일을 입력하면 실패-해결 패턴이 구조화된 교훈으로 추출된다
- [x] 추출된 교훈이 SQLite DB에 저장되고, 중복 교훈은 병합된다
- [x] DB의 교훈을 CLAUDE.md, AGENTS.md, .cursor/rules 3종 형식으로 출력할 수 있다
- [x] 샘플 세션 로그 3개로 end-to-end 데모가 동작한다
- [x] README에 사용법과 데모 시나리오가 문서화되어 있다

## 실행 방법
README.md 참조 — `uv sync && uv run python main.py ingest samples/*.jsonl`

## 소요 정보
- 생성일: 2026-03-22
- 원본 spec: agent-knowledge-loop.md
- 자동 생성: prototype-pipeline spawn

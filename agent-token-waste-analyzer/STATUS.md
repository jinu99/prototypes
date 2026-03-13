# STATUS: SUCCESS

## 요약
Claude Code 세션 로그(JSONL)에서 토큰 낭비 패턴(반복 파일 읽기, 미활용 검색, 중복 컨텍스트)을 자동 감지하고 유효 토큰 비율을 산출하는 터미널 대시보드 CLI 도구.

## 완료 기준 결과
- [x] Claude Code 세션 로그를 파싱하여 tool call 시퀀스를 추출할 수 있다
- [x] 반복 파일 읽기 패턴을 자동 감지하고 중복 횟수/토큰 낭비량을 리포트한다
- [x] 세션별 유효 토큰 비율(작업 토큰 / 전체 토큰)을 산출한다
- [x] 터미널 대시보드에서 낭비 핫스팟 상위 5개와 최적화 제안을 표시한다
- [x] 최소 1개의 실제 세션 로그로 end-to-end 데모가 동작한다

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-12
- 원본 spec: agent-token-waste-analyzer.md
- 자동 생성: prototype-pipeline spawn

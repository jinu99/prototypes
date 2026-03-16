# STATUS: SUCCESS

## 요약
웹훅 카오스 테스터 CLI — 중복/지연/역순 시나리오를 자동 실행하여 웹훅 핸들러의 멱등성 및 에러 처리 결함을 HTTP 응답 코드 기반으로 판정하는 도구.

## 완료 기준 결과
- [x] `webhook-chaos run --target <URL>` 명령으로 기본 시나리오 3종(중복, 지연, 역순) 실행
- [x] YAML 파일로 커스텀 시나리오 정의 가능 (페이로드, 반복 횟수, 지연 시간, 순서)
- [x] 각 시나리오별 PASS/FAIL 판정 + 결과 리포트 (Markdown 또는 JSON)
- [x] 로컬 테스트 서버(echo server) 포함하여 자체 데모 가능
- [x] README에 사용법과 시나리오 작성 가이드 포함

## 실행 방법
```bash
uv sync
uv run webhook-chaos demo
```

## 소요 정보
- 생성일: 2026-03-15
- 원본 spec: webhook-chaos-tester.md
- 자동 생성: prototype-pipeline spawn

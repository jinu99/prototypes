# STATUS: SUCCESS

## 요약
로컬 LLM의 품질을 자동 진단하는 CLI 도구. 구조화 출력(JSON/YAML), 멀티턴 안정성, 토큰 효율성 3가지 프로브를 한 줄 명령으로 실행하고 PASS/WARN/FAIL 리포트를 생성한다.

## 완료 기준 결과
- [x] 한 줄 명령으로 구조화 출력 테스트 실행, 파싱 성공률 숫자 출력
- [x] 5턴 이상 자동 대화 생성, 멀티턴 붕괴 시점 감지 및 리포트 표시
- [x] thinking on/off 비교로 토큰 사용량 차이 측정, 출력 효율성 리포트 생성
- [x] 전체 결과 JSON 파일 내보내기 + 터미널 PASS/WARN/FAIL 요약 표시

## 실행 방법
```bash
uv sync
uv run llm-qual-probe http://localhost:11434        # 실제 Ollama
uv run llm-qual-probe http://localhost:11434 --mock  # mock 모드
```

## 소요 정보
- 생성일: 2026-03-07
- 원본 spec: local-llm-qual-probe.md
- 자동 생성: prototype-pipeline spawn

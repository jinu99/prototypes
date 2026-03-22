# STATUS: SUCCESS

## 요약
Claude Code JSONL 세션 로그에서 프롬프트→코드변경 매핑을 추출하고, 규칙 기반 의도 불일치를 감지하여 HTML 리포트로 시각화하는 프로토타입. 실제 세션 로그로 검증 완료.

## 완료 기준 결과
- [x] Claude Code JSONL 세션 로그를 파싱하여 프롬프트-코드변경 쌍을 추출할 수 있다
- [x] 프롬프트와 해당 프롬프트로 인한 파일 변경(diff)을 매핑하여 시각화하는 웹 리포트가 생성된다
- [x] 간단한 규칙 기반 의도 불일치 감지가 동작한다 (예: 프롬프트에 "삭제"가 있으나 삭제된 코드 없음)
- [x] CLI에서 세션 ID를 지정하면 HTML 리포트가 출력된다
- [x] 실제 Claude Code 세션 로그로 데모를 실행하여 매핑 정확도를 확인할 수 있다

## 실행 방법
```bash
uv run python cli.py analyze --session <SESSION_ID_OR_PATH> --output report.html
```

## 소요 정보
- 생성일: 2026-03-23
- 원본 spec: ai-code-review-process-shift.md
- 자동 생성: prototype-pipeline spawn

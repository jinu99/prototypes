# AI Code Review Process Shift

> Claude Code 세션 로그에서 프롬프트→코드변경 인과관계를 추적하고, 의도 불일치를 감지하는 리뷰 도구

## Architecture

```
┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐
│ JSONL Session│──▶│  Parser  │──▶│ Detector │──▶│   Reporter   │
│    Log       │    │          │    │ (Rules)  │    │  (Jinja2)    │
└─────────────┘    │ Extract: │    │          │    │              │
                   │ • prompts│    │ 5 rules: │    │ Output:      │
                   │ • edits  │    │ • delete  │    │ • HTML report│
                   │ • writes │    │ • add     │    │ • diff view  │
                   │ • bash   │    │ • scope   │    │ • filters    │
                   └──────────┘    │ • file    │    └──────┬───────┘
                                   │ • code    │           │
                                   └──────────┘           ▼
                                                   ┌──────────────┐
                                                   │  HTML Report  │
                                                   │ • 세그먼트별   │
                                                   │   diff 시각화  │
                                                   │ • 불일치 경고  │
                                                   │ • 필터 UI     │
                                                   └──────────────┘
```

## Demo

실제 Claude Code 세션(momentia 프로젝트 작업)을 분석한 결과:

```
$ uv run python cli.py analyze --session 5f593cfd-73b3-4d68-ae65-e427d1798306

Parsing: /home/jinu/.claude/projects/-home-jinu-projects/5f593cfd-...jsonl
Found 39 prompt segments
Found 96 file changes
Report generated: report_5f593cfd-73b3-4d68-ae65-e427d1798306.html
```

생성된 리포트에서 확인 가능한 것:
- 프롬프트 "메모탭 만들어줘" → App.jsx에서 MapView→MemoView 교체 + MemoView 컴포넌트 생성
- 프롬프트에 "없애"(삭제 의도)가 있으나 실제 삭제된 코드가 없을 때 경고 표시
- All / With Changes / Mismatches Only 필터로 관심 세그먼트만 조회

## 실행 방법

```bash
# 의존성 설치
uv sync

# 세션 목록 확인
uv run python cli.py list

# 특정 세션 분석
uv run python cli.py analyze --session <SESSION_ID> --output report.html

# JSONL 파일 직접 지정
uv run python cli.py analyze --session /path/to/session.jsonl
```

## 구조

```
ai-code-review-process-shift/
├── cli.py           # CLI 진입점 (analyze, list 명령)
├── parser.py        # JSONL 세션 로그 파서
├── detector.py      # 규칙 기반 의도 불일치 감지 (5개 규칙)
├── reporter.py      # HTML 리포트 생성기
├── template.html    # Jinja2 HTML 템플릿 (다크 테마)
├── pyproject.toml   # 프로젝트 설정 (uv)
├── BUILD_LOG.md     # 빌드 일지
├── STATUS.md        # 완료 상태
└── README.md        # 이 파일
```

## 원본
prototype-pipeline spec: ai-code-review-process-shift

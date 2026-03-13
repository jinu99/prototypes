# AI Code Change Impact Tracker

> tree-sitter AST 파싱 + git diff 분석으로 코드 변경의 downstream 영향 범위를 추적하고, spec 문서와의 괴리를 자동 탐지하는 CLI 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 변경 영향 추적 (최근 N개 커밋)
uv run impact-track diff HEAD~1
uv run impact-track diff HEAD~3 --path ./my-project

# Spec-코드 괴리 리포트
uv run impact-track spec-check spec.md --path ./my-project
```

## 주요 기능

- **`diff`**: git diff에서 변경된 함수/클래스를 tree-sitter로 식별하고, import/호출 관계 기반 1-hop downstream 영향을 트리 형태로 출력
- **`spec-check`**: markdown spec의 요구사항을 코드 심볼과 매칭하여 "구현됨 / 미구현 / 코드에만 존재" 상태를 리포트

## 구조

```
impact_track/
├── __init__.py
├── cli.py              # typer CLI (diff, spec-check 명령)
├── diff_parser.py      # git diff 파싱 → 변경 파일/라인 범위
├── ast_analyzer.py     # tree-sitter AST → 함수/클래스/import/호출 추출
├── impact_graph.py     # 의존성 그래프 + 1-hop downstream 추적
├── spec_checker.py     # markdown spec 파싱 + 코드 매칭
└── display.py          # rich Tree/Table 터미널 출력
sample_project/         # 테스트용 샘플 프로젝트
├── models.py
├── services.py
├── api.py
└── spec.md
```

## 원본
prototype-pipeline spec: ai-code-change-tracker

# AI Code Change Impact Tracker

> tree-sitter AST 파싱 + git diff 분석으로 코드 변경의 downstream 영향 범위를 추적하고, spec 문서와의 괴리를 자동 탐지하는 CLI 도구

## Architecture

두 개의 파이프라인(`diff`, `spec-check`)이 `ast_analyzer`를 공유하는 구조입니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (typer)                              │
│                  diff  │  spec-check                            │
└────────┬────────────────────────┬────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│   diff_parser   │      │  spec_checker   │
│                 │      │                 │
│ git diff HEAD~N │      │ markdown 파싱    │
│ → ChangedFile[] │      │ → Requirement[] │
│  (path, lines)  │      │  (text, keywords│
└────────┬────────┘      │   line_number)  │
         │               └────────┬────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────┐
│              ast_analyzer (tree-sitter)      │
│                                             │
│  Python 소스 → Symbol[] (함수/클래스/메서드) │
│              → ImportInfo[] (import 관계)    │
│              → FileAnalysis[]               │
└──────┬──────────────────────────┬───────────┘
       │                          │
       ▼                          ▼
┌─────────────────┐      ┌─────────────────┐
│  impact_graph   │      │  spec_checker   │
│                 │      │   .check_spec   │
│ ChangedFile     │      │                 │
│ + FileAnalysis  │      │ Requirement[]   │
│ → 변경 심볼 식별 │      │ + FileAnalysis  │
│ → 1-hop 호출/   │      │ → 키워드 매칭    │
│   import 추적   │      │ → MatchResult[] │
│ → downstream    │      │ + CodeOnlySymbol│
└────────┬────────┘      └────────┬────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────┐
│              display (rich)                  │
│                                             │
│  diff → Impact Tree (변경 심볼 + downstream) │
│  spec → Alignment Table (구현됨/미구현)      │
│       + Code-Only Tree (spec 미언급 심볼)    │
└─────────────────────────────────────────────┘
```

## Demo

### `diff` — 변경 영향 추적

```bash
$ cd sample_project
$ uv run impact-track diff HEAD~1 --path .
```

```
프로젝트: /path/to/sample_project
리비전: HEAD~1

git diff 분석 중...
  변경된 파일: 1개
    models.py (+3/-1 lines)
AST 분석 중...
  분석된 파일: 3개, 심볼: 8개
  변경된 심볼: 1개
영향 범위 추적 중...

📊 Code Change Impact Tree
┣── 🔧 calculate_total (function)  models.py:15-28
│   ┣── ↳ process_order (function)  services.py:10  ← calls calculate_total
│   ┗── ↳ OrderAPI.create (method)  api.py:22       ← imports and calls calculate_total
┗── ⚙️ User.validate (method)      models.py:35-42
    ┗── 영향 범위 없음 (1-hop downstream 없음)

요약: 변경된 심볼 2개, 영향받는 심볼 2개
```

### `spec-check` — Spec-코드 괴리 리포트

```bash
$ uv run impact-track spec-check sample_project/spec.md --path ./sample_project
```

```
프로젝트: /path/to/sample_project
Spec: /path/to/sample_project/spec.md

Spec 파싱 중...
  요구사항: 5개
AST 분석 중...
  분석된 파일: 3개, 심볼: 8개
매칭 중...

            📋 Spec-Code Alignment Report
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ #  ┃ 요구사항                 ┃ 상태     ┃ 매칭된 코드          ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ 1  │ 주문 총액 계산            │ ✅ 구현됨 │ calculate_total     │
│    │                         │          │ (models.py:15)      │
│ 2  │ 사용자 인증              │ ✅ 구현됨 │ User.validate       │
│    │                         │          │ (models.py:35)      │
│ 3  │ 결제 처리                │ ❌ 미구현 │                     │
└────┴─────────────────────────┴──────────┴─────────────────────┘

⚠️ 코드에만 존재 (spec에 미언급)
┣── health_check (function)  api.py:5
┗── format_response (function)  api.py:45

요약: 전체 3개 요구사항 중 2개 구현됨, 1개 미구현, 2개 코드에만 존재
```

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

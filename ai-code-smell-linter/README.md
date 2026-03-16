# AI Code Smell Linter

> tree-sitter AST 기반으로 AI 생성 코드의 구조적 위험 패턴을 탐지하는 CLI 린터

## Architecture

```
                    ┌─────────────┐
   .py/.js/.ts ────▶│  Parser     │ tree-sitter
   source files     │  (multi-    │ Language()
                    │   lang)     │
                    └──────┬──────┘
                           │ AST
                    ┌──────▼──────┐
                    │  Scanner    │ run all rules
                    │             │ against AST
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──┐     ┌──────▼──┐     ┌───────▼─┐
   │ ACS001  │     │ ACS003  │     │ ACS005  │  ... 5 rules
   │ empty   │     │ god     │     │ unnec.  │
   │ catch   │     │ function│     │ abstr.  │
   └─────────┘     └─────────┘     └─────────┘
                           │
                    ┌──────▼──────┐
   CLI ────────────▶│  Output     │──▶ JSON / colored text
   scan / diff      │  Formatter  │
                    └─────────────┘
```

## Demo

### Python 스캔

```bash
$ uv run aicslint scan aicslint/test_samples/smelly_python.py

⚠ Found 12 code smell(s):

  [CRITICAL] smelly_python.py:13 — Empty catch/except block silently swallows errors ACS001
    except Exception:
  [CRITICAL] smelly_python.py:96 — Hardcoded secret in variable 'api_key' ACS004
    api_key = "sk-1234567890abcdef"
  [WARNING] smelly_python.py:30 — Catch block only re-raises/re-throws the same exception ACS002
    except ValueError as e:
  [WARNING] smelly_python.py:42 — Function 'process_everything' is 50 lines with nesting depth 9 ACS003
    process_everything(...)  # 50 lines, depth 9
  [INFO] smelly_python.py:103 — Abstract class 'BaseProcessor' has only one implementation ACS005
    class BaseProcessor(ABC):

Summary: 8 critical, 3 warning, 1 info
```

### Pylint과의 비교 (ACS002, ACS005를 못 잡음)

```bash
$ uv run pylint aicslint/test_samples/comparison_demo.py
# → missing-docstring만 리포트, catch-rethrow/unnecessary abstraction 미탐지

$ uv run aicslint scan aicslint/test_samples/comparison_demo.py
  [WARNING] comparison_demo.py:18 — Catch block only re-raises/re-throws ACS002
  [INFO] comparison_demo.py:25 — Abstract class 'IDataStore' has only one implementation ACS005
```

### JSON 출력

```bash
$ uv run aicslint scan aicslint/test_samples/smelly_python.py -j
[
  {
    "rule_id": "ACS001",
    "rule_name": "empty-catch",
    "severity": "critical",
    "message": "Empty catch/except block silently swallows errors",
    "file": "aicslint/test_samples/smelly_python.py",
    "line": 13,
    ...
  }
]
```

### Git Diff 스캔

```bash
$ git add suspicious_file.py
$ uv run aicslint diff
# → staged된 변경 라인에 해당하는 스멜만 리포트
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 단일 파일 스캔
uv run aicslint scan <file_or_dir>

# JSON 출력
uv run aicslint scan <file> -j

# Git staged 변경만 스캔
uv run aicslint diff
```

## 룰 목록

| ID | Name | Severity | Description |
|---|---|---|---|
| ACS001 | empty-catch | critical | Empty catch/except — 에러를 조용히 삼킴 |
| ACS002 | catch-and-rethrow | warning | Catch 후 동일 예외 재throw — 무의미한 패턴 |
| ACS003 | god-function | warning | 40줄+ & 중첩 5단계+ — AI의 "다 때려넣기" 패턴 |
| ACS004 | hardcoded-secret | critical | AST 기반 시크릿 변수 탐지 |
| ACS005 | unnecessary-abstraction | info | 단일 구현 추상 클래스/인터페이스 |

## 구조

```
ai-code-smell-linter/
├── aicslint/
│   ├── __init__.py
│   ├── cli.py              # Click CLI (scan, diff)
│   ├── parser.py            # tree-sitter 다언어 파서
│   ├── scanner.py           # 스캐너 + 룰 레지스트리
│   ├── diff.py              # git diff --staged 파싱
│   ├── rules/
│   │   ├── base.py          # SmellResult, BaseRule
│   │   ├── empty_catch.py   # ACS001
│   │   ├── catch_rethrow.py # ACS002
│   │   ├── god_function.py  # ACS003
│   │   ├── hardcoded_secret.py # ACS004
│   │   └── unnecessary_abstraction.py # ACS005
│   └── test_samples/
│       ├── smelly_python.py
│       ├── smelly_javascript.js
│       ├── smelly_typescript.ts
│       └── comparison_demo.py
├── pyproject.toml
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: ai-code-smell-linter

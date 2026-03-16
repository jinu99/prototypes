# Doc Freshness Monitor

> 코드 심볼 참조 기반으로 문서의 staleness를 감지하는 CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (click)                             │
│                    scan / check 커맨드                           │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────┐          ┌────────────────────────────────┐
│  symbol_extractor    │          │         git_tracker            │
│                      │          │                                │
│  Markdown/RST 문서   │──────▶  │  ① find_symbol_in_code()       │
│  에서 regex 패턴으로  │ symbols │    git grep으로 심볼 정의 파일   │
│  코드 심볼 참조 추출  │         │    탐색                         │
│                      │          │  ② get_symbol_history()        │
│  · backtick 함수호출 │          │    git log로 변경 이력 수집     │
│  · PascalCase 클래스 │          │  ③ get_doc_last_modified()     │
│  · dotted 모듈 경로  │          │    문서 최종 수정일 조회        │
│  · 파일 경로 참조    │          └───────────────┬────────────────┘
│  · import 구문       │                          │
└─────────────────────┘                          │ tracking records
                                                 ▼
                                    ┌─────────────────────────┐
                                    │        scorer            │
                                    │                          │
                                    │  staleness score (0-100) │
                                    │  = 날짜 차이 (최대 60점)  │
                                    │  + 커밋 수 (최대 40점)    │
                                    └────────────┬────────────┘
                                                 │
                                                 ▼
                                    ┌─────────────────────────┐
                                    │       reporter           │
                                    │                          │
                                    │  · Markdown 테이블 리포트 │
                                    │  · JSON 포맷 리포트       │
                                    │  · scan 테이블 출력       │
                                    └─────────────────────────┘
```

## Demo

**문서에서 코드 심볼 참조 스캔 (`scan`)**

```bash
$ uv run doc-freshness scan ./my-project

# Symbol Scan Results

| Doc File          | Symbol          | Kind     | Line |
|:------------------|:----------------|:---------|-----:|
| README.md         | `scan_docs`     | function |   12 |
| README.md         | `Scorer`        | class    |   25 |
| docs/api.md       | `scorer.py`     | file     |    8 |
| docs/api.md       | `to_markdown`   | function |   34 |

Total: 4 symbol references found across 2 doc files.
```

**staleness 점검 및 리포트 (`check`)**

```bash
$ uv run doc-freshness check ./my-project --threshold 50

Scanning docs in /home/user/my-project...
Found 4 symbol references in 2 doc files.
Tracking symbol changes via git log...
Resolved 3 doc-symbol pairs to code files.

# Doc Freshness Report

Generated: 2026-03-16 14:30

Total doc-symbol pairs analyzed: 3

## Results

| Score   | Doc File    | Symbol        | Kind     | Code Last Changed | Commit # |
|--------:|:------------|:--------------|:---------|:------------------|:---------|
| **72** ⚠️ | docs/api.md | `to_markdown` | function | 2026-03-10        | 18       |
| **45**  | README.md   | `scan_docs`   | function | 2026-02-28        | 7        |
| 12      | README.md   | `Scorer`      | class    | 2026-01-15        | 3        |

## Summary

- **Total pairs**: 3
- **Stale (score > 0)**: 3
- **High staleness (score >= 70)**: 1

⚠ 1 doc-symbol pair(s) exceed staleness threshold (50):
  [72] docs/api.md:34 → `to_markdown` (function)
```

**JSON 포맷 출력**

```bash
$ uv run doc-freshness check ./my-project --format json -o report.json
Report written to report.json
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 문서에서 코드 심볼 참조 스캔
uv run doc-freshness scan <repo-path>

# staleness 점검 (Markdown 리포트)
uv run doc-freshness check <repo-path>

# 임계치 설정 (초과 시 exit code 1)
uv run doc-freshness check <repo-path> --threshold 50

# JSON 포맷 출력
uv run doc-freshness check <repo-path> --format json

# 파일로 저장
uv run doc-freshness check <repo-path> -o report.md
```

## 구조

```
doc_freshness/
  __init__.py
  cli.py               # CLI 엔트리포인트 (click)
  symbol_extractor.py   # 문서에서 코드 심볼 참조 추출
  git_tracker.py        # git log로 심볼 변경 이력 추적
  scorer.py             # staleness score (0-100) 산출
  reporter.py           # JSON/Markdown 리포트 생성
pyproject.toml
BUILD_LOG.md
STATUS.md
```

## 원본
prototype-pipeline spec: doc-freshness-monitor

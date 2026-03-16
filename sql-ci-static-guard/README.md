# SQL CI Static Guard

> sqlglot AST 기반 SQL 안티패턴 감지 CLI — cross-dialect 지원, pre-commit hook 통합

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  SQL 파일/디렉토리  │     │                  sql-guard CLI                   │
│  (.sql)         │     │               (cli.py / Click)                   │
└────────┬────────┘     │                                                  │
         │              │  --dialect, --format, --strict                   │
         ▼              └──────────────────┬───────────────────────────────┘
┌─────────────────┐                        │
│  pre-commit     │───────────────────────▶│
│  hook 트리거     │                        ▼
└─────────────────┘              ┌─────────────────────┐
                                 │   Analyzer           │
                                 │   (analyzer.py)      │
                                 │                      │
                                 │  ┌───────────────┐   │
                                 │  │ dialect 감지    │   │
                                 │  │ (파일명/주석)   │   │
                                 │  └───────┬───────┘   │
                                 │          ▼           │
                                 │  ┌───────────────┐   │
                                 │  │ sqlglot.parse  │   │
                                 │  │ → AST 생성     │   │
                                 │  └───────┬───────┘   │
                                 │          ▼           │
                                 │  ┌───────────────┐   │
                                 │  │ 9개 규칙 실행   │   │
                                 │  │ (rules.py)     │   │
                                 │  └───────┬───────┘   │
                                 └──────────┼──────────┘
                                            ▼
                          ┌─────────────────────────────────┐
                          │         Violation 목록            │
                          │  (rule, message, severity)       │
                          └────────────┬────────────────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
                ┌────────────┐  ┌────────────┐  ┌────────────┐
                │ text 출력   │  │ JSON 출력   │  │ exit code  │
                │ (기본)      │  │ (-f json)  │  │ 0/1 (CI)   │
                └────────────┘  └────────────┘  └────────────┘
```

**핵심 흐름**: SQL 파일 → sqlglot AST 파싱 (cross-dialect) → 9개 규칙 함수가 AST 노드를 순회하며 안티패턴 탐지 → Violation 리포트 출력

## Demo

```bash
$ uv run sql-guard samples/postgres_bad.sql

✗  samples/postgres_bad.sql [postgres]
   🟡 [select-star] Avoid SELECT *; explicitly list needed columns.
   🔴 [missing-where-delete] DELETE without WHERE clause will delete all rows.
   🔴 [missing-where-update] UPDATE without WHERE clause will update all rows.
   🟡 [leading-wildcard-like] LIKE '%widget%' uses a leading wildcard, preventing index usage.
   🟡 [implicit-column-order] INSERT without explicit column list relies on implicit column ordering.
   🔴 [hardcoded-credentials] Possible hardcoded credential: 'password ='
   🟡 [cartesian-join] CROSS JOIN produces a cartesian product — likely unintended.
   🟡 [order-by-ordinal] ORDER BY 2 uses ordinal position; use column name instead.
   🔴 [null-comparison] Use IS NULL / IS NOT NULL instead of = NULL / != NULL.
   🟡 [select-star] Avoid SELECT *; explicitly list needed columns.
   🟡 [select-star] Avoid SELECT *; explicitly list needed columns.

──────────────────────────────────────────────────
Files scanned: 1
Violations: 11
```

```bash
# JSON 출력 모드
$ uv run sql-guard samples/clean.sql -f json
[
  {
    "path": "samples/clean.sql",
    "dialect": "auto",
    "violations": []
  }
]
```

```bash
# CI strict 모드 — warning 포함 모든 violation에서 exit 1
$ uv run sql-guard samples/ --strict; echo "exit: $?"
...
exit: 1
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 단일 파일 검사
uv run sql-guard samples/postgres_bad.sql

# 디렉토리 전체 검사
uv run sql-guard samples/

# JSON 출력
uv run sql-guard samples/ -f json

# dialect 지정
uv run sql-guard query.sql -d snowflake

# CI 모드 (warning 포함 모든 violation에서 exit 1)
uv run sql-guard samples/ --strict
```

## 감지 규칙 (9개)

| # | Rule | Severity | 설명 |
|---|------|----------|------|
| 1 | `select-star` | warning | SELECT * 사용 |
| 2 | `missing-where-delete` | error | WHERE 없는 DELETE |
| 3 | `missing-where-update` | error | WHERE 없는 UPDATE |
| 4 | `leading-wildcard-like` | warning | LIKE '%...' 선행 와일드카드 |
| 5 | `implicit-column-order` | warning | INSERT 컬럼 목록 누락 |
| 6 | `hardcoded-credentials` | error | 하드코딩된 인증 정보 패턴 |
| 7 | `cartesian-join` | warning | CROSS JOIN / 조건 없는 comma-join |
| 8 | `order-by-ordinal` | warning | ORDER BY 숫자 사용 |
| 9 | `null-comparison` | error | = NULL / != NULL 비교 |

## pre-commit hook

```bash
uv run pre-commit install
# 이후 .sql 파일 커밋 시 자동 검사
```

## 구조

```
sql-ci-static-guard/
├── sql_guard/
│   ├── __init__.py
│   ├── rules.py        # 9개 안티패턴 규칙 (AST 기반)
│   ├── analyzer.py     # SQL 파일 파싱 + 규칙 실행
│   └── cli.py          # Click CLI 진입점
├── samples/
│   ├── postgres_bad.sql
│   ├── mysql_bad.sql
│   ├── snowflake_bad.sql
│   └── clean.sql
├── .pre-commit-config.yaml
├── pyproject.toml
├── BUILD_LOG.md
└── STATUS.md
```

## 원본
prototype-pipeline spec: sql-ci-static-guard

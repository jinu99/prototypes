# SQL CI Static Guard

> sqlglot AST 기반 SQL 안티패턴 감지 CLI — cross-dialect 지원, pre-commit hook 통합

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

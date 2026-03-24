# SQL Query Perf Advisor

> pg_stat_statements 스냅샷을 오프라인 분석하여 N+1 패턴, 비효율 쿼리 플랜을 감지하고 구체적 최적화 제안을 출력하는 CLI 도구

## Architecture

```
                         ┌─────────────────┐
  snapshot.json ────────▶│   CLI (click)   │
  (pg_stat_statements    │                 │
   + EXPLAIN plans)      └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
           ┌──────────────┐ ┌──────────┐ ┌──────────────┐
           │ Fingerprint  │ │ EXPLAIN  │ │   Reporter   │
           │   + N+1      │ │  Parser  │ │  (Rich UI)   │
           │  Detection   │ │          │ │              │
           └──────────────┘ └──────────┘ └──────────────┘
                    │             │             ▲
                    │   Rules:    │             │
                    │ • N+1      │             │
                    │ • SeqScan  │─────────────┘
                    │ • Missing  │  Top-N ranking
                    │   Index    │  + findings
                    │ • Nested   │
                    │   Loop     │
                    └────────────┘
```

## Demo

```
$ uv run sql-perf analyze --input samples/snapshot.json

╭──────────────────────────────────────────────────────────╮
│ SQL Query Performance Advisor                            │
│ Snapshot: 2026-03-24T10:00:00Z | Queries: 8 | EXPLAIN: 4│
╰──────────────────────────────────────────────────────────╯

═══ Top-N Costly Queries ═══

 #  Query                          Calls   Cost Score
 1  SELECT * FROM orders WHERE..   4,500   60,750,000
 2  SELECT p.name, r.rating...     3,200   30,720,000
 3  SELECT * FROM products...      3,200   20,480,000

═══ N+1 Pattern Detection ═══

 #1 [HIGH] N+1 Query Pattern
   Parent: SELECT * FROM users WHERE id = $1     (4,500 calls)
   Child:  SELECT * FROM orders WHERE user_id=$1 (4,500 calls)
   → Replace with single JOIN query

═══ EXPLAIN Plan Analysis ═══

 [HIGH] MISSING_INDEX on 'orders'
   → CREATE INDEX idx_orders_user_id ON orders (user_id);
     Expected speedup: ~100x

 [HIGH] INEFFICIENT_NESTED_LOOP
   → Consider Hash Join, add index on orders(created_at)

⚠ 7 performance issue(s) detected.
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run sql-perf analyze --input samples/snapshot.json

# 옵션
uv run sql-perf analyze --input samples/snapshot.json --top-n 5
uv run sql-perf analyze --input samples/snapshot.json --call-threshold 5000
```

## 구조

```
sql-query-perf-advisor/
├── sql_perf_advisor/
│   ├── __init__.py
│   ├── cli.py              # Click CLI 엔트리포인트
│   ├── fingerprint.py      # 쿼리 핑거프린팅 + N+1 감지
│   ├── explain_parser.py   # EXPLAIN JSON 파서 + 규칙 엔진
│   └── reporter.py         # Rich 기반 출력 포매터
├── samples/
│   └── snapshot.json       # 샘플 pg_stat_statements 데이터
├── pyproject.toml
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: sql-query-perf-advisor

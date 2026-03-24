"""Query fingerprinting and N+1 pattern detection."""

import re
from collections import defaultdict


def normalize_query(query: str) -> str:
    """Normalize a SQL query by replacing literals with placeholders."""
    q = query.strip()
    # Already parameterized ($1, $2, etc.) — just normalize whitespace
    q = re.sub(r"\s+", " ", q)
    # Normalize quoted strings
    q = re.sub(r"'[^']*'", "$?", q)
    # Normalize numeric literals (but not $1-style params)
    q = re.sub(r"(?<!\$)\b\d+\b", "$?", q)
    return q.strip().upper()


def extract_table_pattern(query: str) -> str:
    """Extract the core table access pattern from a query for N+1 grouping."""
    q = query.upper().strip()
    # Extract FROM/JOIN table names
    tables = re.findall(r"(?:FROM|JOIN)\s+(\w+)", q, re.IGNORECASE)
    # Extract query type
    if q.startswith("SELECT"):
        qtype = "SELECT"
    elif q.startswith("INSERT"):
        qtype = "INSERT"
    elif q.startswith("UPDATE"):
        qtype = "UPDATE"
    elif q.startswith("DELETE"):
        qtype = "DELETE"
    else:
        qtype = "OTHER"
    return f"{qtype}:{','.join(sorted(set(tables)))}"


def detect_n_plus_1(statements: list[dict], call_threshold: int = 1000) -> list[dict]:
    """Detect N+1 query patterns.

    N+1 pattern: a simple single-table SELECT called many times,
    often paired with another query hitting a related table.
    """
    # Group by table access pattern
    pattern_groups = defaultdict(list)
    for stmt in statements:
        query = stmt.get("query", "")
        if not query.upper().strip().startswith("SELECT"):
            continue
        fingerprint = normalize_query(query)
        pattern = extract_table_pattern(query)
        pattern_groups[pattern].append({
            "queryid": stmt.get("queryid"),
            "query": query,
            "fingerprint": fingerprint,
            "calls": stmt.get("calls", 0),
            "total_exec_time": stmt.get("total_exec_time", 0),
            "mean_exec_time": stmt.get("mean_exec_time", 0),
        })

    # Find high-call single-table patterns that look like N+1
    candidates = []
    for pattern, queries in pattern_groups.items():
        for q in queries:
            if q["calls"] < call_threshold:
                continue
            # Single-table simple WHERE query is a strong N+1 signal
            tables = pattern.split(":")[1].split(",") if ":" in pattern else []
            if len(tables) == 1:
                candidates.append({
                    "pattern": pattern,
                    "table": tables[0] if tables else "unknown",
                    **q,
                })

    # Try to pair N+1 candidates (parent-child relationship)
    pairs = []
    used = set()
    sorted_candidates = sorted(candidates, key=lambda x: x["calls"], reverse=True)

    for i, c1 in enumerate(sorted_candidates):
        for j, c2 in enumerate(sorted_candidates):
            if i >= j or c1["table"] == c2["table"]:
                continue
            if i in used or j in used:
                continue
            # Similar call counts suggest paired queries
            ratio = min(c1["calls"], c2["calls"]) / max(c1["calls"], c2["calls"])
            if ratio > 0.8:
                pairs.append({
                    "type": "N+1 Query Pattern",
                    "severity": "HIGH",
                    "parent": c1,
                    "child": c2,
                    "total_calls": c1["calls"] + c2["calls"],
                    "total_time_ms": c1["total_exec_time"] + c2["total_exec_time"],
                    "suggestion": (
                        f"Replace {c1['calls']} individual queries on "
                        f"{c1['table']} + {c2['table']} with a single JOIN query.\n"
                        f"  Example: SELECT * FROM {c1['table'].lower()} t1 "
                        f"JOIN {c2['table'].lower()} t2 ON t2.{c1['table'].lower().rstrip('s')}_id = t1.id"
                    ),
                })
                used.add(i)
                used.add(j)

    # Unpaired high-call queries are still suspicious
    for i, c in enumerate(sorted_candidates):
        if i not in used:
            pairs.append({
                "type": "N+1 Suspect (Unpaired)",
                "severity": "MEDIUM",
                "query": c,
                "total_calls": c["calls"],
                "total_time_ms": c["total_exec_time"],
                "suggestion": (
                    f"Query on {c['table']} called {c['calls']} times. "
                    f"Consider batching with IN clause or JOIN."
                ),
            })

    return sorted(pairs, key=lambda x: x["total_time_ms"], reverse=True)

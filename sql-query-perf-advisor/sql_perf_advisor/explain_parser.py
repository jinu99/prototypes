"""EXPLAIN JSON parser and anti-pattern detection."""

from dataclasses import dataclass, field

LARGE_TABLE_ROW_THRESHOLD = 10000
HIGH_COST_THRESHOLD = 10000
NESTED_LOOP_ROW_THRESHOLD = 1000


@dataclass
class Finding:
    rule: str
    severity: str  # HIGH, MEDIUM, LOW
    node_type: str
    table: str
    detail: str
    suggestion: str
    cost: float = 0.0


def walk_plan(plan: dict):
    """Recursively yield all plan nodes."""
    yield plan
    for child in plan.get("Plans", []):
        yield from walk_plan(child)


def detect_seq_scan(plan: dict, query: str) -> list[Finding]:
    """Detect Seq Scan on large tables (missing index)."""
    findings = []
    for node in walk_plan(plan):
        if node.get("Node Type") != "Seq Scan":
            continue
        table = node.get("Relation Name", "unknown")
        plan_rows = node.get("Plan Rows", 0)
        rows_removed = node.get("Rows Removed by Filter", 0)
        total_cost = node.get("Total Cost", 0)
        filter_cond = node.get("Filter", "")

        # Seq Scan is only bad if filtering many rows
        if rows_removed < LARGE_TABLE_ROW_THRESHOLD and total_cost < HIGH_COST_THRESHOLD:
            continue

        # Extract column names from filter for index suggestion
        columns = _extract_filter_columns(filter_cond)
        if columns:
            idx_cols = ", ".join(columns)
            idx_name = f"idx_{table}_{'_'.join(columns)}"
            index_sql = f"CREATE INDEX {idx_name} ON {table} ({idx_cols});"
        else:
            index_sql = f"CREATE INDEX idx_{table}_<columns> ON {table} (<filter_columns>);"

        findings.append(Finding(
            rule="SEQ_SCAN_LARGE_TABLE",
            severity="HIGH" if rows_removed > 100000 else "MEDIUM",
            node_type="Seq Scan",
            table=table,
            detail=(
                f"Sequential scan on '{table}' with {rows_removed:,} rows removed by filter. "
                f"Total cost: {total_cost:,.0f}. Filter: {filter_cond}"
            ),
            suggestion=f"Add an index to avoid full table scan:\n  {index_sql}",
            cost=total_cost,
        ))
    return findings


def detect_nested_loop(plan: dict, query: str) -> list[Finding]:
    """Detect inefficient Nested Loops on large result sets."""
    findings = []
    for node in walk_plan(plan):
        if node.get("Node Type") != "Nested Loop":
            continue
        plan_rows = node.get("Plan Rows", 0)
        actual_rows = node.get("Actual Rows", plan_rows)
        total_cost = node.get("Total Cost", 0)

        if plan_rows < NESTED_LOOP_ROW_THRESHOLD and total_cost < HIGH_COST_THRESHOLD:
            continue

        # Check children for Seq Scan (worst case)
        children = node.get("Plans", [])
        outer = children[0] if children else {}
        outer_type = outer.get("Node Type", "")
        outer_table = outer.get("Relation Name", "unknown")

        findings.append(Finding(
            rule="INEFFICIENT_NESTED_LOOP",
            severity="HIGH" if plan_rows > 100000 else "MEDIUM",
            node_type="Nested Loop",
            table=outer_table,
            detail=(
                f"Nested Loop producing {plan_rows:,} rows (cost: {total_cost:,.0f}). "
                f"Outer: {outer_type} on '{outer_table}'."
            ),
            suggestion=(
                f"Consider replacing Nested Loop with Hash Join or Merge Join.\n"
                f"  - If outer is Seq Scan, add an index on the join/filter columns of '{outer_table}'\n"
                f"  - SET enable_nestloop = off; to test alternative plans\n"
                f"  - Consider increasing work_mem for hash joins"
            ),
            cost=total_cost,
        ))
    return findings


def detect_missing_index(plan: dict, query: str) -> list[Finding]:
    """Detect potential missing indexes from filter conditions on Seq Scans."""
    findings = []
    for node in walk_plan(plan):
        if node.get("Node Type") != "Seq Scan":
            continue
        filter_cond = node.get("Filter", "")
        if not filter_cond:
            continue
        table = node.get("Relation Name", "unknown")
        plan_rows = node.get("Plan Rows", 0)
        rows_removed = node.get("Rows Removed by Filter", 0)

        # Selectivity: if returning very few rows vs scanning many
        total_rows = plan_rows + rows_removed
        if total_rows == 0:
            continue
        selectivity = plan_rows / total_rows

        if selectivity > 0.1:  # More than 10% of rows returned — Seq Scan may be OK
            continue

        columns = _extract_filter_columns(filter_cond)
        if not columns:
            continue

        # This overlaps with SEQ_SCAN_LARGE_TABLE but focuses on selectivity
        idx_cols = ", ".join(columns)
        idx_name = f"idx_{table}_{'_'.join(columns)}"

        findings.append(Finding(
            rule="MISSING_INDEX",
            severity="HIGH" if selectivity < 0.01 else "MEDIUM",
            node_type="Seq Scan",
            table=table,
            detail=(
                f"Low selectivity ({selectivity:.4f}) scan on '{table}': "
                f"returning {plan_rows:,} of {total_rows:,} rows. Filter: {filter_cond}"
            ),
            suggestion=(
                f"Create a targeted index:\n"
                f"  CREATE INDEX {idx_name} ON {table} ({idx_cols});\n"
                f"  Expected speedup: ~{int(1/selectivity)}x for this query pattern"
            ),
            cost=node.get("Total Cost", 0),
        ))
    return findings


def analyze_explain(plan_data: dict, query: str = "") -> list[Finding]:
    """Run all anti-pattern rules on an EXPLAIN JSON plan."""
    plan = plan_data.get("Plan", plan_data)
    findings = []
    findings.extend(detect_seq_scan(plan, query))
    findings.extend(detect_nested_loop(plan, query))
    findings.extend(detect_missing_index(plan, query))
    # Deduplicate: if both SEQ_SCAN and MISSING_INDEX on same table, keep MISSING_INDEX
    seen = {}
    for f in findings:
        key = (f.rule, f.table)
        if key not in seen or _severity_rank(f.severity) > _severity_rank(seen[key].severity):
            seen[key] = f

    # If MISSING_INDEX and SEQ_SCAN_LARGE_TABLE both exist for same table, drop SEQ_SCAN
    tables_with_missing_idx = {
        f.table for f in seen.values() if f.rule == "MISSING_INDEX"
    }
    deduped = {
        k: v for k, v in seen.items()
        if not (v.rule == "SEQ_SCAN_LARGE_TABLE" and v.table in tables_with_missing_idx)
    }
    return sorted(deduped.values(), key=lambda f: f.cost, reverse=True)


def _severity_rank(s: str) -> int:
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(s, 0)


def _extract_filter_columns(filter_str: str) -> list[str]:
    """Extract column names from a PostgreSQL filter expression."""
    import re
    # Match patterns like (column_name = $1), (col >= $2)
    # Also handle nested: ((col1 = $1) AND (col2 = $2))
    cols = re.findall(r"\b(\w+)\s*(?:=|<|>|<=|>=|<>|!=|~~|LIKE|BETWEEN|IN)\s*", filter_str)
    # Filter out common noise
    noise = {"AND", "OR", "NOT", "TRUE", "FALSE", "NULL", "IS"}
    seen = []
    for c in cols:
        if c.upper() not in noise and not c.startswith("$") and c not in seen:
            seen.append(c)
    return seen

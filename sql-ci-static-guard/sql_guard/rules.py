"""Anti-pattern detection rules using sqlglot AST."""

from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp


@dataclass
class Violation:
    rule: str
    message: str
    line: int | None = None
    severity: str = "warning"


def check_select_star(expression: exp.Expression) -> list[Violation]:
    """Rule 1: SELECT * — discourages use of SELECT * in production queries."""
    violations = []
    for select in expression.find_all(exp.Select):
        for star in select.find_all(exp.Star):
            # Ignore COUNT(*)
            if isinstance(star.parent, exp.Count):
                continue
            violations.append(Violation(
                rule="select-star",
                message="Avoid SELECT *; explicitly list needed columns.",
                severity="warning",
            ))
    return violations


def check_missing_where_delete(expression: exp.Expression) -> list[Violation]:
    """Rule 2: DELETE without WHERE — extremely dangerous."""
    violations = []
    for delete in expression.find_all(exp.Delete):
        where = delete.find(exp.Where)
        if where is None:
            violations.append(Violation(
                rule="missing-where-delete",
                message="DELETE without WHERE clause will delete all rows.",
                severity="error",
            ))
    return violations


def check_missing_where_update(expression: exp.Expression) -> list[Violation]:
    """Rule 3: UPDATE without WHERE — extremely dangerous."""
    violations = []
    for update in expression.find_all(exp.Update):
        where = update.find(exp.Where)
        if where is None:
            violations.append(Violation(
                rule="missing-where-update",
                message="UPDATE without WHERE clause will update all rows.",
                severity="error",
            ))
    return violations


def check_leading_wildcard_like(expression: exp.Expression) -> list[Violation]:
    """Rule 4: LIKE '%...' — leading wildcard prevents index usage."""
    violations = []
    for like in expression.find_all(exp.Like):
        pattern = like.expression
        if isinstance(pattern, exp.Literal) and pattern.is_string:
            val = pattern.this
            if val.startswith("%") or val.startswith("_"):
                violations.append(Violation(
                    rule="leading-wildcard-like",
                    message=f"LIKE '{val}' uses a leading wildcard, preventing index usage.",
                    severity="warning",
                ))
    return violations


def check_implicit_column_order(expression: exp.Expression) -> list[Violation]:
    """Rule 5: INSERT without explicit column list."""
    violations = []
    for insert in expression.find_all(exp.Insert):
        # If there's a VALUES clause but no column list specified
        if insert.find(exp.Values) or insert.find(exp.Select):
            columns = insert.find(exp.Schema)
            if columns is None:
                violations.append(Violation(
                    rule="implicit-column-order",
                    message="INSERT without explicit column list relies on implicit column ordering.",
                    severity="warning",
                ))
    return violations


def check_hardcoded_credentials(expression: exp.Expression) -> list[Violation]:
    """Rule 6: Hardcoded credential patterns in SQL."""
    violations = []
    cred_patterns = re.compile(
        r"(password|passwd|pwd|secret|api_key|token)\s*=",
        re.IGNORECASE,
    )
    sql_text = expression.sql()
    for match in cred_patterns.finditer(sql_text):
        violations.append(Violation(
            rule="hardcoded-credentials",
            message=f"Possible hardcoded credential: '{match.group().strip()}'",
            severity="error",
        ))
    return violations


def check_cartesian_join(expression: exp.Expression) -> list[Violation]:
    """Rule 7: Cartesian join (CROSS JOIN or comma-join without condition)."""
    violations = []
    for select in expression.find_all(exp.Select):
        for join in select.find_all(exp.Join):
            kind = (join.kind or "").upper()
            # Explicit CROSS JOIN
            if "CROSS" in kind:
                violations.append(Violation(
                    rule="cartesian-join",
                    message="CROSS JOIN produces a cartesian product — likely unintended.",
                    severity="warning",
                ))
            # Comma-join: sqlglot parses "FROM a, b" as an implicit join with no ON/kind
            elif not kind and join.args.get("on") is None and join.args.get("using") is None:
                where = select.find(exp.Where)
                if where is None:
                    violations.append(Violation(
                        rule="cartesian-join",
                        message="Implicit comma-join without WHERE — cartesian product.",
                        severity="warning",
                    ))
    return violations


def check_order_by_ordinal(expression: exp.Expression) -> list[Violation]:
    """Rule 8: ORDER BY using ordinal numbers instead of column names."""
    violations = []
    for order in expression.find_all(exp.Order):
        for ordered in order.find_all(exp.Ordered):
            col = ordered.this
            if isinstance(col, exp.Literal) and col.is_int:
                violations.append(Violation(
                    rule="order-by-ordinal",
                    message=f"ORDER BY {col.this} uses ordinal position; use column name instead.",
                    severity="warning",
                ))
    return violations


def check_not_null_comparison(expression: exp.Expression) -> list[Violation]:
    """Rule 9: Comparing with NULL using = or != instead of IS NULL / IS NOT NULL."""
    violations = []
    for eq in expression.find_all(exp.EQ, exp.NEQ):
        if isinstance(eq.left, exp.Null) or isinstance(eq.right, exp.Null):
            violations.append(Violation(
                rule="null-comparison",
                message="Use IS NULL / IS NOT NULL instead of = NULL / != NULL.",
                severity="error",
            ))
    return violations


ALL_RULES = [
    check_select_star,
    check_missing_where_delete,
    check_missing_where_update,
    check_leading_wildcard_like,
    check_implicit_column_order,
    check_hardcoded_credentials,
    check_cartesian_join,
    check_order_by_ordinal,
    check_not_null_comparison,
]

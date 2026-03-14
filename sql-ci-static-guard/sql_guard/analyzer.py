"""SQL file analyzer — parses SQL and runs rules against AST."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import sqlglot

from sql_guard.rules import ALL_RULES, Violation


DIALECT_MAP = {
    "postgres": "postgres",
    "postgresql": "postgres",
    "mysql": "mysql",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "sqlite": "sqlite",
}


@dataclass
class FileResult:
    path: str
    dialect: str
    violations: list[Violation] = field(default_factory=list)
    parse_error: str | None = None


def detect_dialect(filepath: str) -> str | None:
    """Try to detect dialect from file extension or comment hint."""
    name = os.path.basename(filepath).lower()
    for key in DIALECT_MAP:
        if key in name:
            return DIALECT_MAP[key]
    # Check first line for dialect hint: -- dialect: postgres
    try:
        with open(filepath) as f:
            first_line = f.readline().strip()
        if first_line.startswith("-- dialect:"):
            hint = first_line.split(":", 1)[1].strip().lower()
            return DIALECT_MAP.get(hint, hint)
    except Exception:
        pass
    return None


def analyze_sql(sql: str, dialect: str | None = None) -> list[Violation]:
    """Parse SQL string and run all rules."""
    violations = []
    try:
        statements = sqlglot.parse(sql, dialect=dialect)
    except sqlglot.errors.ParseError as e:
        return [Violation(rule="parse-error", message=str(e), severity="error")]

    for stmt in statements:
        if stmt is None:
            continue
        for rule_fn in ALL_RULES:
            violations.extend(rule_fn(stmt))
    return violations


def analyze_file(filepath: str, dialect: str | None = None) -> FileResult:
    """Analyze a single SQL file."""
    path = Path(filepath)
    if dialect is None:
        dialect = detect_dialect(filepath)

    try:
        sql = path.read_text(encoding="utf-8")
    except Exception as e:
        return FileResult(path=str(path), dialect=dialect or "auto", parse_error=str(e))

    violations = analyze_sql(sql, dialect=dialect)
    parse_errors = [v for v in violations if v.rule == "parse-error"]
    if parse_errors:
        return FileResult(
            path=str(path),
            dialect=dialect or "auto",
            violations=[v for v in violations if v.rule != "parse-error"],
            parse_error=parse_errors[0].message,
        )
    return FileResult(path=str(path), dialect=dialect or "auto", violations=violations)


def analyze_path(target: str, dialect: str | None = None) -> list[FileResult]:
    """Analyze a file or all .sql files in a directory."""
    target_path = Path(target)
    if target_path.is_file():
        return [analyze_file(str(target_path), dialect)]
    elif target_path.is_dir():
        results = []
        for sql_file in sorted(target_path.rglob("*.sql")):
            results.append(analyze_file(str(sql_file), dialect))
        return results
    else:
        return [FileResult(path=target, dialect="unknown", parse_error=f"Path not found: {target}")]

"""Core scanner: parses files and runs all rules."""

import os
from pathlib import Path

from .parser import parse_code, get_language_name
from .rules.base import SmellResult
from .rules.empty_catch import EmptyCatchRule
from .rules.catch_rethrow import CatchRethrowRule
from .rules.god_function import GodFunctionRule
from .rules.hardcoded_secret import HardcodedSecretRule
from .rules.unnecessary_abstraction import UnnecessaryAbstractionRule

ALL_RULES = [
    EmptyCatchRule(),
    CatchRethrowRule(),
    GodFunctionRule(),
    HardcodedSecretRule(),
    UnnecessaryAbstractionRule(),
]

SUPPORTED_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx"}


def scan_file(filepath: str) -> list[SmellResult]:
    """Scan a single file and return all detected smells."""
    ext = Path(filepath).suffix
    if ext not in SUPPORTED_EXTS:
        return []

    source = Path(filepath).read_text(encoding="utf-8", errors="replace")
    tree, lang = parse_code(source, ext)
    if tree is None:
        return []

    results = []
    for rule in ALL_RULES:
        if lang in rule.languages:
            results.extend(rule.check(tree, source, lang, filepath))
    return results


def scan_diff_lines(filepath: str, changed_lines: set[int]) -> list[SmellResult]:
    """Scan a file but only report smells on changed lines."""
    all_results = scan_file(filepath)
    return [
        r for r in all_results
        if r.line in changed_lines
        or (r.end_line and any(l in changed_lines for l in range(r.line, r.end_line + 1)))
    ]


def results_to_json(results: list[SmellResult]) -> list[dict]:
    """Convert results to JSON-serializable dicts."""
    return [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "severity": r.severity,
            "message": r.message,
            "file": r.file,
            "line": r.line,
            "end_line": r.end_line,
            "snippet": r.snippet,
        }
        for r in results
    ]

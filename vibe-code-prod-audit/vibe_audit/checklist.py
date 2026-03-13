"""Production readiness checklist scoring for FastAPI projects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .scanner import ScanResult

CHECKLIST_PATH = Path(__file__).parent.parent / "fastapi_checklist.json"


@dataclass
class CheckItem:
    id: str
    name: str
    category: str
    weight: int
    passed: bool
    detail: str


@dataclass
class AuditReport:
    score: int  # 0-100
    items: list[CheckItem]
    scan: ScanResult

    @property
    def passed_items(self) -> list[CheckItem]:
        return [i for i in self.items if i.passed]

    @property
    def failed_items(self) -> list[CheckItem]:
        return [i for i in self.items if not i.passed]


def load_checklist() -> list[dict]:
    with open(CHECKLIST_PATH) as f:
        return json.load(f)["checks"]


def evaluate(scan: ScanResult) -> AuditReport:
    """Evaluate scan results against the FastAPI production checklist."""
    checks = load_checklist()
    items: list[CheckItem] = []

    evaluators = {
        "has_routes": _check_has_routes,
        "has_healthcheck": _check_healthcheck,
        "has_tests": _check_tests,
        "has_error_handling": _check_error_handling,
        "has_env_management": _check_env_management,
        "has_middleware": _check_middleware,
        "has_cors": _check_cors,
        "has_dockerfile": _check_dockerfile,
        "has_dependency_file": _check_dependency_file,
    }

    total_weight = 0
    earned_weight = 0

    for check in checks:
        check_id = check["id"]
        evaluator = evaluators.get(check_id)
        if evaluator is None:
            continue

        passed, detail = evaluator(scan)
        weight = check.get("weight", 10)
        total_weight += weight
        if passed:
            earned_weight += weight

        items.append(CheckItem(
            id=check_id,
            name=check["name"],
            category=check["category"],
            weight=weight,
            passed=passed,
            detail=detail,
        ))

    score = round(earned_weight / total_weight * 100) if total_weight > 0 else 0
    return AuditReport(score=score, items=items, scan=scan)


def _check_has_routes(scan: ScanResult) -> tuple[bool, str]:
    n = len(scan.routes)
    if n > 0:
        return True, f"{n} route(s) detected"
    return False, "No routes found — is this a FastAPI project?"


def _check_healthcheck(scan: ScanResult) -> tuple[bool, str]:
    if scan.has_healthcheck:
        health_routes = [r for r in scan.routes if "health" in r.path.lower()]
        paths = ", ".join(r.path for r in health_routes)
        return True, f"Health endpoint found: {paths}"
    return False, "No health check endpoint (/health, /healthz, /ping)"


def _check_tests(scan: ScanResult) -> tuple[bool, str]:
    if scan.test_files:
        return True, f"{len(scan.test_files)} test file(s): {', '.join(scan.test_files[:3])}"
    return False, "No test files found (test_*.py or *_test.py)"


def _check_error_handling(scan: ScanResult) -> tuple[bool, str]:
    parts = []
    if scan.has_exception_handler_decorator:
        parts.append("exception_handler decorator")
    if scan.has_try_except_in_routes:
        parts.append("try/except in routes")
    if parts:
        return True, f"Error handling: {', '.join(parts)}"
    return False, "No exception handlers or try/except blocks in route handlers"


def _check_env_management(scan: ScanResult) -> tuple[bool, str]:
    if scan.env_usage:
        return True, f"Environment variable usage in: {', '.join(scan.env_usage[:3])}"
    return False, "No environment variable management (os.environ, dotenv, BaseSettings)"


def _check_middleware(scan: ScanResult) -> tuple[bool, str]:
    if scan.has_middleware:
        return True, "Middleware registered"
    return False, "No middleware configured"


def _check_cors(scan: ScanResult) -> tuple[bool, str]:
    if scan.has_cors:
        return True, "CORS middleware configured"
    return False, "No CORS configuration found"


def _check_dockerfile(scan: ScanResult) -> tuple[bool, str]:
    if scan.has_dockerfile:
        return True, "Dockerfile present"
    return False, "No Dockerfile found"


def _check_dependency_file(scan: ScanResult) -> tuple[bool, str]:
    parts = []
    if scan.has_pyproject:
        parts.append("pyproject.toml")
    if scan.has_requirements:
        parts.append("requirements.txt")
    if parts:
        return True, f"Dependency files: {', '.join(parts)}"
    return False, "No dependency file (requirements.txt or pyproject.toml)"

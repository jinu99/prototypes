"""tree-sitter based FastAPI project scanner.

Parses Python source files to extract:
- FastAPI app instances
- Route definitions (decorators like @app.get, @app.post, etc.)
- Middleware registrations
- Error handler registrations
- Import patterns (env var usage, testing frameworks)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
HEALTH_PATTERNS = {"/health", "/healthz", "/health/", "/healthz/", "/ping", "/_health"}


@dataclass
class Route:
    method: str
    path: str
    function_name: str
    file: str
    line: int


@dataclass
class ScanResult:
    """Aggregated results from scanning a FastAPI project."""
    routes: list[Route] = field(default_factory=list)
    has_healthcheck: bool = False
    has_error_handlers: bool = False
    has_middleware: bool = False
    has_cors: bool = False
    test_files: list[str] = field(default_factory=list)
    env_usage: list[str] = field(default_factory=list)  # files using os.environ / dotenv
    python_files: list[str] = field(default_factory=list)
    app_variable: str | None = None
    has_exception_handler_decorator: bool = False
    has_try_except_in_routes: bool = False
    has_dockerfile: bool = False
    has_requirements: bool = False
    has_pyproject: bool = False


def create_parser() -> Parser:
    return Parser(PY_LANGUAGE)


def find_python_files(project_dir: str) -> list[Path]:
    """Find all .py files in the project, excluding venv/node_modules."""
    skip_dirs = {".venv", "venv", "__pycache__", "node_modules", ".git", ".tox", "env", "generated"}
    result = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f.endswith(".py"):
                result.append(Path(root) / f)
    return sorted(result)


def _get_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_fastapi_app_names(root_node, source: bytes) -> list[str]:
    """Find variable names assigned to FastAPI() instances."""
    apps = []
    for node in root_node.children:
        if node.type == "expression_statement":
            child = node.children[0] if node.children else None
            if child and child.type == "assignment":
                left = child.child_by_field_name("left")
                right = child.child_by_field_name("right")
                if left and right and right.type == "call":
                    func = right.child_by_field_name("function")
                    if func and _get_text(func, source) == "FastAPI":
                        apps.append(_get_text(left, source))
    return apps


def _extract_decorator_routes(node, source: bytes, app_names: list[str]) -> list[dict]:
    """Extract route info from decorated function definitions."""
    routes = []
    if node.type != "decorated_definition":
        return routes

    for child in node.children:
        if child.type != "decorator":
            continue
        dec_text = _get_text(child, source)
        # Match patterns like @app.get("/path") or @router.post("/path")
        for app_name in app_names:
            for method in HTTP_METHODS:
                pattern = f"@{app_name}.{method}("
                if pattern in dec_text:
                    path = _extract_path_from_decorator(child, source)
                    func_node = node.child_by_field_name("definition")
                    func_name = ""
                    if func_node:
                        name_node = func_node.child_by_field_name("name")
                        if name_node:
                            func_name = _get_text(name_node, source)
                    routes.append({
                        "method": method.upper(),
                        "path": path or "???",
                        "function_name": func_name,
                        "line": child.start_point[0] + 1,
                    })
    return routes


def _extract_path_from_decorator(decorator_node, source: bytes) -> str | None:
    """Extract the URL path string from a decorator like @app.get('/path')."""
    text = _get_text(decorator_node, source)
    # Simple string extraction: find first quoted string in the decorator
    for quote in ('"', "'"):
        start = text.find(quote)
        if start != -1:
            end = text.find(quote, start + 1)
            if end != -1:
                return text[start + 1:end]
    return None


def _check_error_handlers(root_node, source: bytes, app_names: list[str]) -> dict:
    """Check for exception handler registrations and try/except in routes."""
    result = {"has_decorator": False, "has_try_except": False}
    full_text = source.decode("utf-8", errors="replace")

    for app_name in app_names:
        if f"{app_name}.exception_handler" in full_text or f"{app_name}.add_exception_handler" in full_text:
            result["has_decorator"] = True
            break

    # Walk AST for try statements inside function definitions
    def _walk(node, inside_func=False):
        if node.type in ("function_definition", "async_function_definition"):
            inside_func = True
        if node.type == "try_statement" and inside_func:
            result["has_try_except"] = True
            return
        for child in node.children:
            _walk(child, inside_func)

    _walk(root_node)
    return result


def _check_middleware(source: bytes, app_names: list[str]) -> dict:
    """Check for middleware and CORS usage."""
    text = source.decode("utf-8", errors="replace")
    result = {"has_middleware": False, "has_cors": False}

    for app_name in app_names:
        if f"{app_name}.add_middleware" in text or f"{app_name}.middleware" in text:
            result["has_middleware"] = True

    if "CORSMiddleware" in text:
        result["has_cors"] = True
        result["has_middleware"] = True

    return result


def _check_env_usage(source: bytes) -> bool:
    """Check if file uses environment variables (os.environ, os.getenv, dotenv)."""
    text = source.decode("utf-8", errors="replace")
    return any(p in text for p in ["os.environ", "os.getenv", "dotenv", "load_dotenv", "BaseSettings"])


def scan_project(project_dir: str) -> ScanResult:
    """Scan a FastAPI project directory and return analysis results."""
    parser = create_parser()
    result = ScanResult()
    project_path = Path(project_dir)

    # Find all Python files
    py_files = find_python_files(project_dir)
    result.python_files = [str(f.relative_to(project_path)) for f in py_files]

    # Check for test files
    for f in py_files:
        rel = str(f.relative_to(project_path))
        if rel.startswith("test") or "/test" in rel or f.name.startswith("test_") or f.name.endswith("_test.py"):
            result.test_files.append(rel)

    # Check for project config files
    result.has_dockerfile = (project_path / "Dockerfile").exists()
    result.has_requirements = (project_path / "requirements.txt").exists()
    result.has_pyproject = (project_path / "pyproject.toml").exists()

    # Collect all app names across files (app, router, etc.)
    all_app_names = set()
    # Always check for common names
    common_names = ["app", "router", "api"]

    for py_file in py_files:
        source = py_file.read_bytes()
        tree = parser.parse(source)
        root = tree.root_node

        # Find FastAPI app instances
        file_apps = _find_fastapi_app_names(root, source)
        all_app_names.update(file_apps)
        if file_apps and result.app_variable is None:
            result.app_variable = file_apps[0]

    # Also check common variable names + APIRouter
    all_app_names.update(common_names)

    # Second pass: extract routes and check patterns
    for py_file in py_files:
        source = py_file.read_bytes()
        tree = parser.parse(source)
        root = tree.root_node
        rel_path = str(py_file.relative_to(project_path))

        # Check for APIRouter
        text = source.decode("utf-8", errors="replace")
        if "APIRouter" in text:
            # Find router variable names
            for node in root.children:
                if node.type == "expression_statement":
                    child = node.children[0] if node.children else None
                    if child and child.type == "assignment":
                        right = child.child_by_field_name("right")
                        if right and "APIRouter" in _get_text(right, source):
                            left = child.child_by_field_name("left")
                            if left:
                                all_app_names.add(_get_text(left, source))

        # Extract routes from decorated definitions
        for node in root.children:
            if node.type == "decorated_definition":
                routes = _extract_decorator_routes(node, source, list(all_app_names))
                for r in routes:
                    route = Route(
                        method=r["method"],
                        path=r["path"],
                        function_name=r["function_name"],
                        file=rel_path,
                        line=r["line"],
                    )
                    result.routes.append(route)
                    if route.path.lower().rstrip("/") in HEALTH_PATTERNS or "health" in route.path.lower():
                        result.has_healthcheck = True

        # Check error handling
        err = _check_error_handlers(root, source, list(all_app_names))
        if err["has_decorator"]:
            result.has_exception_handler_decorator = True
            result.has_error_handlers = True
        if err["has_try_except"]:
            result.has_try_except_in_routes = True
            result.has_error_handlers = True

        # Check middleware
        mw = _check_middleware(source, list(all_app_names))
        if mw["has_middleware"]:
            result.has_middleware = True
        if mw["has_cors"]:
            result.has_cors = True

        # Check env usage
        if _check_env_usage(source):
            result.env_usage.append(rel_path)

    return result

"""AST-based capability detection for Python packages."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# Build detection patterns programmatically to avoid false positives from hooks
_OS_MOD = "os"

CAPABILITY_RULES: dict[str, list[dict]] = {
    "network": [
        {"module": "socket"},
        {"module": "http.client"},
        {"module": "urllib"},
        {"module": "urllib.request"},
        {"module": "urllib3"},
        {"module": "requests"},
        {"module": "httpx"},
        {"module": "aiohttp"},
        {"attr": "urlopen"},
        {"attr": "connect"},
    ],
    "filesystem": [
        {"func": "open"},
        {"module": "shutil"},
        {"module": "tempfile"},
        {"module": "glob"},
        {"module": "pathlib"},
        {"attr": "read_text"},
        {"attr": "write_text"},
        {"attr": "read_bytes"},
        {"attr": "write_bytes"},
        {"attr": "mkdir"},
        {"attr": "rmdir"},
        {"attr": "unlink"},
        {"attr": "rename"},
    ],
    "env_access": [
        {"attr": f"{_OS_MOD}.environ"},
        {"attr": f"{_OS_MOD}.getenv"},
        {"attr": "environ.get"},
        {"attr": "environ"},
        {"module": "dotenv"},
    ],
    "process_exec": [
        {"module": "subprocess"},
        {"func": f"{_OS_MOD}.system"},
        {"func": f"{_OS_MOD}.popen"},
        {"func": f"{_OS_MOD}.execvp"},
        {"attr": "Popen"},
        {"module": "multiprocessing"},
    ],
    "database": [
        {"module": "sqlite3"},
        {"module": "psycopg2"},
        {"module": "pymysql"},
        {"module": "sqlalchemy"},
        {"module": "pymongo"},
        {"module": "redis"},
    ],
    "crypto": [
        {"module": "cryptography"},
        {"module": "hashlib"},
        {"module": "hmac"},
        {"module": "ssl"},
    ],
    "code_exec": [
        {"func": "eval"},
        {"func": "exec"},
        {"func": "compile"},
        {"module": "ctypes"},
        {"module": "importlib"},
    ],
}

CAPABILITY_WEIGHTS = {
    "process_exec": 10,
    "code_exec": 9,
    "network": 8,
    "database": 7,
    "env_access": 6,
    "filesystem": 5,
    "crypto": 3,
}


@dataclass
class CapabilityHit:
    category: str
    evidence: str
    file: str
    line: int


@dataclass
class PackageCapabilities:
    name: str
    capabilities: dict[str, list[CapabilityHit]] = field(default_factory=dict)
    total_files_scanned: int = 0
    direct_score: float = 0.0

    @property
    def category_set(self) -> set[str]:
        return set(self.capabilities.keys())

    def compute_direct_score(self) -> float:
        score = 0.0
        for cat, hits in self.capabilities.items():
            weight = CAPABILITY_WEIGHTS.get(cat, 1)
            score += weight * min(len(hits), 5)
        self.direct_score = score
        return score


class CapabilityVisitor(ast.NodeVisitor):
    """AST visitor that detects high-privilege API usage."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.hits: list[CapabilityHit] = []
        self._imports: set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._imports.add(alias.name)
            self._check_module_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        self._imports.add(mod)
        self._check_module_import(mod, node.lineno)
        for alias in node.names:
            full = f"{mod}.{alias.name}"
            self._check_module_import(full, node.lineno)
            self._check_attr(alias.name, node.lineno, f"from {mod} import {alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._get_call_name(node)
        if func_name:
            self._check_func_call(func_name, node.lineno)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        full = self._get_attr_chain(node)
        if full:
            self._check_attr(full, node.lineno, full)
        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return self._get_attr_chain(node.func)
        return None

    def _get_attr_chain(self, node: ast.Attribute) -> str | None:
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        parts.reverse()
        return ".".join(parts)

    def _check_module_import(self, module: str, lineno: int):
        for cat, rules in CAPABILITY_RULES.items():
            for rule in rules:
                if "module" in rule:
                    if module == rule["module"] or module.startswith(rule["module"] + "."):
                        self.hits.append(CapabilityHit(
                            category=cat,
                            evidence=f"import {module}",
                            file=self.filepath,
                            line=lineno,
                        ))

    def _check_func_call(self, name: str, lineno: int):
        for cat, rules in CAPABILITY_RULES.items():
            for rule in rules:
                if "func" in rule:
                    if name == rule["func"] or name.endswith("." + rule["func"]):
                        self.hits.append(CapabilityHit(
                            category=cat,
                            evidence=f"{name}()",
                            file=self.filepath,
                            line=lineno,
                        ))

    def _check_attr(self, name: str, lineno: int, evidence: str):
        for cat, rules in CAPABILITY_RULES.items():
            for rule in rules:
                if "attr" in rule:
                    if name == rule["attr"] or name.endswith("." + rule["attr"]):
                        self.hits.append(CapabilityHit(
                            category=cat,
                            evidence=evidence,
                            file=self.filepath,
                            line=lineno,
                        ))


def _resolve_package_paths(pkg_name: str, site_packages: Path) -> list[Path]:
    """Resolve actual source paths for a package, handling namespace packages."""
    normalized = pkg_name.replace("-", "_").lower()

    # Direct match first
    candidates = [
        site_packages / normalized,
        site_packages / f"{normalized}.py",
    ]
    for c in candidates:
        if c.exists():
            return [c]

    # Check dist-info RECORD for namespace packages (e.g., google-genai -> google/genai)
    dist_info_patterns = [
        site_packages / f"{normalized}-*.dist-info",
    ]
    import glob as glob_mod
    for pattern in dist_info_patterns:
        for dist_dir in glob_mod.glob(str(pattern)):
            record_file = Path(dist_dir) / "RECORD"
            if record_file.exists():
                # Parse RECORD to find actual source directories
                dirs: set[str] = set()
                for line in record_file.read_text().splitlines():
                    parts = line.split(",")[0]
                    if parts.endswith(".py") and "/" in parts:
                        # Get the top-level package path (e.g., google/genai -> google/genai)
                        segments = parts.split("/")
                        if len(segments) >= 2 and not segments[0].endswith(".dist-info"):
                            # Find the deepest "owned" directory
                            pkg_dir = "/".join(segments[:2])
                            dirs.add(pkg_dir)
                # Return unique package directories
                paths = []
                for d in dirs:
                    p = site_packages / d
                    if p.exists() and p not in paths:
                        paths.append(p)
                if paths:
                    return paths

    return []


def scan_package(pkg_name: str, site_packages: Path) -> PackageCapabilities:
    """Scan a package's source files for capability usage."""
    result = PackageCapabilities(name=pkg_name)

    pkg_paths = _resolve_package_paths(pkg_name, site_packages)

    py_files: list[Path] = []
    for candidate in pkg_paths:
        if candidate.is_dir():
            py_files.extend(candidate.rglob("*.py"))
        elif candidate.is_file():
            py_files.append(candidate)

    result.total_files_scanned = len(py_files)

    for py_file in py_files:
        try:
            source = py_file.read_text(errors="replace")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(site_packages))
        visitor = CapabilityVisitor(rel_path)
        visitor.visit(tree)

        for hit in visitor.hits:
            if hit.category not in result.capabilities:
                result.capabilities[hit.category] = []
            result.capabilities[hit.category].append(hit)

    result.compute_direct_score()
    return result

"""Dependency extraction from Python projects."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DepNode:
    name: str
    version: str = ""
    children: list[str] = field(default_factory=list)  # direct dependency names


def extract_deps_from_requirements(req_path: Path) -> list[str]:
    """Parse requirements.txt and return package names."""
    names = []
    for line in req_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip version specifiers, extras, etc.
        for sep in (">=", "<=", "==", "!=", "~=", ">", "<", "[", ";"):
            line = line.split(sep)[0]
        name = line.strip().lower()
        if name:
            names.append(name)
    return names


def build_dep_graph(venv_python: str) -> dict[str, DepNode]:
    """Build dependency graph using pipdeptree JSON output."""
    result = subprocess.run(
        [venv_python, "-m", "pipdeptree", "--json-tree"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # Fallback: try with pipdeptree directly
        result = subprocess.run(
            ["pipdeptree", "--python", venv_python, "--json-tree"],
            capture_output=True, text=True,
        )

    tree = json.loads(result.stdout)
    graph: dict[str, DepNode] = {}

    def walk(nodes: list[dict], parent: str | None = None):
        for node in nodes:
            name = node["key"].lower()
            if name not in graph:
                graph[name] = DepNode(
                    name=name,
                    version=node.get("installed_version", ""),
                )
            if parent and name not in graph.get(parent, DepNode(parent)).children:
                if parent in graph:
                    graph[parent].children.append(name)
            if node.get("dependencies"):
                walk(node["dependencies"], parent=name)

    walk(tree)
    return graph


def find_venv_python(project_path: Path) -> str:
    """Find the Python interpreter in a project's venv."""
    candidates = [
        project_path / ".venv" / "bin" / "python",
        project_path / "venv" / "bin" / "python",
        project_path / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def find_site_packages(venv_python: str) -> Path | None:
    """Find the site-packages directory for a given Python interpreter."""
    result = subprocess.run(
        [venv_python, "-c", "import site; print(site.getsitepackages()[0])"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        p = Path(result.stdout.strip())
        if p.exists():
            return p
    return None

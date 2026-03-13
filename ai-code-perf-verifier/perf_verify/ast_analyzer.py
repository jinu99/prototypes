"""Analyze Python AST to find which functions/methods were changed."""

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FunctionInfo:
    name: str          # e.g. "MyClass.my_method" or "my_function"
    filepath: str
    start_line: int
    end_line: int
    module: str        # dotted module path for import


def extract_functions(source: str, filepath: str) -> list[FunctionInfo]:
    """Extract all function/method definitions from Python source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    module = Path(filepath).stem
    functions: list[FunctionInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(FunctionInfo(
                        name=f"{node.name}.{item.name}",
                        filepath=filepath,
                        start_line=item.lineno,
                        end_line=item.end_lineno or item.lineno,
                        module=module,
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip methods (already handled inside ClassDef)
            if not any(
                isinstance(p, ast.ClassDef)
                for p in _iter_parents(tree, node)
            ):
                functions.append(FunctionInfo(
                    name=node.name,
                    filepath=filepath,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    module=module,
                ))

    return functions


def _iter_parents(tree: ast.AST, target: ast.AST):
    """Yield parent nodes of target in the AST."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if child is target:
                yield node


def find_changed_functions(
    source: str,
    filepath: str,
    changed_lines: list[int],
) -> list[FunctionInfo]:
    """Find functions that overlap with changed lines."""
    all_funcs = extract_functions(source, filepath)
    changed = []
    for func in all_funcs:
        if any(func.start_line <= line <= func.end_line for line in changed_lines):
            changed.append(func)
    return changed


def read_file_at_ref(filepath: str, ref: str = "HEAD~1") -> str | None:
    """Read a file's content at a specific git ref."""
    import subprocess
    result = subprocess.run(
        ["git", "show", f"{ref}:{filepath}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout


def read_current_file(filepath: str) -> str | None:
    """Read a file's current content."""
    try:
        return Path(filepath).read_text()
    except FileNotFoundError:
        return None

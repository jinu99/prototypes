"""tree-sitter를 사용하여 Python 소스의 함수/클래스/import/호출 관계를 추출한다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter
import tree_sitter_python as tspython

_LANGUAGE = tree_sitter.Language(tspython.language())
_PARSER = tree_sitter.Parser(_LANGUAGE)


@dataclass
class Symbol:
    name: str
    kind: str  # "function" | "class" | "method"
    file: str
    start_line: int
    end_line: int
    calls: list[str] = field(default_factory=list)
    parent_class: str | None = None


@dataclass
class ImportInfo:
    module: str
    names: list[str]  # imported names (["*"] for 'import module')
    file: str


@dataclass
class FileAnalysis:
    path: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)


def _extract_calls(node) -> list[str]:
    """노드 아래의 모든 함수 호출명을 추출한다.

    인스턴스 메서드 호출 (obj.method())의 경우, 전체 이름과 메서드명 모두 기록한다.
    이를 통해 downstream 매칭에서 메서드 이름만으로도 추적이 가능하다.
    """
    calls = []
    if node.type == "call":
        func = node.child_by_field_name("function")
        if func:
            name = func.text.decode()
            # self.method() → method만 추출
            if name.startswith("self."):
                calls.append(name[5:])
            elif "." in name:
                # obj.method() → 전체 이름 + 메서드명 모두 기록
                calls.append(name)
                method_part = name.rsplit(".", 1)[-1]
                calls.append(method_part)
            else:
                calls.append(name)
    for child in node.children:
        calls.extend(_extract_calls(child))
    return calls


def _extract_methods(class_node, file_path: str, class_name: str) -> list[Symbol]:
    """클래스 내부의 메서드들을 추출한다."""
    methods = []
    body = class_node.child_by_field_name("body")
    if not body:
        return methods
    for child in body.children:
        if child.type == "function_definition":
            name_node = child.child_by_field_name("name")
            if name_node:
                method_name = name_node.text.decode()
                calls = _extract_calls(child)
                methods.append(Symbol(
                    name=method_name,
                    kind="method",
                    file=file_path,
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    calls=calls,
                    parent_class=class_name,
                ))
    return methods


def _extract_imports(node, file_path: str) -> list[ImportInfo]:
    """import 문을 추출한다."""
    imports = []
    if node.type == "import_statement":
        # import foo, bar
        for child in node.children:
            if child.type == "dotted_name":
                imports.append(ImportInfo(
                    module=child.text.decode(),
                    names=["*"],
                    file=file_path,
                ))
            elif child.type == "aliased_import":
                dotted = child.child_by_field_name("name")
                if dotted:
                    imports.append(ImportInfo(
                        module=dotted.text.decode(),
                        names=["*"],
                        file=file_path,
                    ))
    elif node.type == "import_from_statement":
        module_node = node.child_by_field_name("module_name")
        module = module_node.text.decode() if module_node else ""
        names = []
        for child in node.children:
            if child.type == "dotted_name" and child != module_node:
                names.append(child.text.decode())
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                if name_node:
                    names.append(name_node.text.decode())
        if not names:
            # from module import *
            names = ["*"]
        imports.append(ImportInfo(module=module, names=names, file=file_path))
    return imports


def analyze_file(file_path: str | Path) -> FileAnalysis:
    """단일 Python 파일을 tree-sitter로 분석한다."""
    file_path = Path(file_path)
    source = file_path.read_bytes()
    tree = _PARSER.parse(source)
    root = tree.root_node

    path_str = str(file_path)
    analysis = FileAnalysis(path=path_str)

    for child in root.children:
        if child.type == "function_definition":
            name_node = child.child_by_field_name("name")
            if name_node:
                calls = _extract_calls(child)
                analysis.symbols.append(Symbol(
                    name=name_node.text.decode(),
                    kind="function",
                    file=path_str,
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    calls=calls,
                ))
        elif child.type == "class_definition":
            name_node = child.child_by_field_name("name")
            if name_node:
                class_name = name_node.text.decode()
                analysis.symbols.append(Symbol(
                    name=class_name,
                    kind="class",
                    file=path_str,
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                ))
                methods = _extract_methods(child, path_str, class_name)
                analysis.symbols.extend(methods)
        elif child.type in ("import_statement", "import_from_statement"):
            analysis.imports.extend(_extract_imports(child, path_str))
        elif child.type == "decorated_definition":
            # handle decorated functions/classes
            for dchild in child.children:
                if dchild.type == "function_definition":
                    name_node = dchild.child_by_field_name("name")
                    if name_node:
                        calls = _extract_calls(dchild)
                        analysis.symbols.append(Symbol(
                            name=name_node.text.decode(),
                            kind="function",
                            file=path_str,
                            start_line=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            calls=calls,
                        ))
                elif dchild.type == "class_definition":
                    name_node = dchild.child_by_field_name("name")
                    if name_node:
                        class_name = name_node.text.decode()
                        analysis.symbols.append(Symbol(
                            name=class_name,
                            kind="class",
                            file=path_str,
                            start_line=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                        ))
                        methods = _extract_methods(dchild, path_str, class_name)
                        analysis.symbols.extend(methods)

    return analysis


def analyze_project(project_path: str | Path) -> list[FileAnalysis]:
    """프로젝트 내 모든 Python 파일을 분석한다."""
    project_path = Path(project_path)
    results = []
    for py_file in sorted(project_path.rglob("*.py")):
        # .venv, __pycache__ 등 제외
        parts = py_file.relative_to(project_path).parts
        if any(p.startswith(".") or p == "__pycache__" or p == "node_modules" for p in parts):
            continue
        try:
            results.append(analyze_file(py_file))
        except Exception:
            continue
    return results

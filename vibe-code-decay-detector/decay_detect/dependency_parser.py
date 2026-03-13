"""tree-sitter based import statement parsing for dependency graph construction."""

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser
from pathlib import Path


PY_LANG = Language(tspython.language())
JS_LANG = Language(tsjavascript.language())


def _make_parser(lang: Language) -> Parser:
    parser = Parser(lang)
    return parser


def parse_python_imports(source: bytes, file_path: str) -> list[tuple[str, str]]:
    """Parse Python imports, return list of (from_module, to_module) edges."""
    parser = _make_parser(PY_LANG)
    tree = parser.parse(source)
    edges = []
    from_mod = _file_to_module(file_path)

    for node in _walk(tree.root_node):
        if node.type == "import_statement":
            # import foo / import foo.bar
            for child in node.children:
                if child.type == "dotted_name":
                    to_mod = _normalize_module(child.text.decode("utf-8"))
                    edges.append((from_mod, to_mod))
        elif node.type == "import_from_statement":
            # from foo import bar
            module_node = None
            for child in node.children:
                if child.type in ("dotted_name", "relative_import"):
                    module_node = child
                    break
            if module_node:
                to_mod = _normalize_module(module_node.text.decode("utf-8"))
                edges.append((from_mod, to_mod))

    return edges


def parse_js_imports(source: bytes, file_path: str) -> list[tuple[str, str]]:
    """Parse JS/TS imports, return list of (from_module, to_module) edges."""
    parser = _make_parser(JS_LANG)
    tree = parser.parse(source)
    edges = []
    from_mod = _file_to_module(file_path)

    for node in _walk(tree.root_node):
        if node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node:
                to_mod = source_node.text.decode("utf-8").strip("'\"")
                edges.append((from_mod, to_mod))
        elif node.type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn and fn.text == b"require":
                args = node.child_by_field_name("arguments")
                if args and args.child_count > 1:
                    arg = args.children[1]
                    if arg.type == "string":
                        to_mod = arg.text.decode("utf-8").strip("'\"")
                        edges.append((from_mod, to_mod))

    return edges


def parse_file_imports(file_path: str, source: bytes) -> list[tuple[str, str]]:
    """Auto-detect language and parse imports."""
    p = Path(file_path)
    if p.suffix == ".py":
        return parse_python_imports(source, file_path)
    elif p.suffix in (".js", ".jsx", ".ts", ".tsx"):
        return parse_js_imports(source, file_path)
    return []


def _normalize_module(name: str) -> str:
    """Normalize module name by stripping common prefixes."""
    parts = name.split(".")
    while parts and parts[0] in ("src", "lib", "app"):
        parts.pop(0)
    return ".".join(parts) if parts else name


def _file_to_module(file_path: str) -> str:
    """Convert file path to module-like name."""
    p = Path(file_path)
    parts = list(p.with_suffix("").parts)
    # Remove leading .
    while parts and parts[0] == ".":
        parts.pop(0)
    return _normalize_module(".".join(parts)) if parts else file_path


def _walk(node):
    """Walk all nodes in tree-sitter AST."""
    yield node
    for child in node.children:
        yield from _walk(child)

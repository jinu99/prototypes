"""Multi-language AST parser using tree-sitter."""

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())

LANG_MAP = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TS_LANGUAGE,
    ".jsx": JS_LANGUAGE,
}

LANG_NAME_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
}


def get_language(ext: str) -> Language | None:
    return LANG_MAP.get(ext)


def get_language_name(ext: str) -> str | None:
    return LANG_NAME_MAP.get(ext)


def parse_code(source: str, ext: str) -> tuple:
    """Parse source code and return (tree, language_name) or (None, None)."""
    lang = get_language(ext)
    if lang is None:
        return None, None
    parser = Parser(lang)
    tree = parser.parse(source.encode("utf-8"))
    return tree, get_language_name(ext)

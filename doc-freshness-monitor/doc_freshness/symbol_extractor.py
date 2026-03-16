"""Extract code symbol references from documentation files."""

import re
from pathlib import Path

# Patterns for Python symbols referenced in markdown docs
PATTERNS = {
    # Backtick-quoted identifiers: `some_function()`, `SomeClass`, `module.func`
    "backtick_ref": re.compile(r"`([a-zA-Z_]\w*(?:\.\w+)*)\(\)`"),
    "backtick_class": re.compile(r"`([A-Z]\w+)`"),
    "backtick_module": re.compile(r"`([a-zA-Z_]\w*(?:\.\w+)+)`"),
    # Bare function/class references in prose (conservative: PascalCase only)
    "prose_class": re.compile(r"(?<!\w)([A-Z][a-z]\w{2,})(?:\s+class|\s+object)?(?!\w)"),
    # File path references: src/foo.py, foo/bar.py
    "file_path": re.compile(r"(?:^|\s|`)([\w/]+\.py)(?:`|\s|$|[,.)'\"])"),
    # import-style refs: from foo import bar, import foo.bar
    "import_ref": re.compile(r"(?:from\s+([\w.]+)\s+import\s+([\w, ]+)|import\s+([\w.]+))"),
}

DOC_GLOBS = [
    "README*.md", "CONTRIBUTING*.md", "CHANGELOG*.md",
    "docs/**/*.md", "doc/**/*.md",
    "README*.rst", "CONTRIBUTING*.rst", "CHANGELOG*.rst",
    "docs/**/*.rst", "doc/**/*.rst",
]

# Common English words that look like PascalCase class names
FALSE_POSITIVES = {
    "The", "This", "That", "These", "Those", "There", "Then", "They",
    "What", "When", "Where", "Which", "While", "Who", "Why", "How",
    "For", "From", "With", "Into", "About", "After", "Before",
    "Between", "Under", "Over", "Each", "Every", "Also", "Just",
    "But", "And", "Not", "All", "Any", "Some", "Many", "Most",
    "Other", "New", "Old", "See", "Use", "Using", "Used",
    "Note", "Please", "Make", "Like", "Here", "More", "One",
    "First", "Last", "Next", "Only", "Very", "Still", "Even",
    "However", "Because", "Since", "Until", "Once", "Both",
    "True", "False", "None", "Python", "Flask", "Django",
    "FastAPI", "Linux", "Windows", "MacOS", "Docker", "GitHub",
    "Markdown", "HTML", "JSON", "YAML", "TOML", "HTTP", "HTTPS",
    "API", "REST", "URL", "CLI", "GUI", "SQL", "CSS",
    "Available", "Example", "Examples", "Install", "Installation",
    "Getting", "Started", "Quick", "Start", "Overview", "Welcome",
    "Thanks", "Todo", "Changelog", "License", "Contributing",
    "Documentation", "Features", "Requirements", "Setup", "Usage",
    "Configuration", "Options", "Arguments", "Parameters", "Returns",
    "Raises", "Deprecated", "Version", "Release", "Breaking",
    "Changes", "Added", "Fixed", "Removed", "Updated", "Security",
}

# Too-generic symbol names that produce excessive false positives
GENERIC_SYMBOLS = {
    "it", "at", "the", "from", "a", "an", "is", "to", "in", "on",
    "or", "if", "do", "no", "so", "up", "by",
}

# Minimum symbol length to consider (bare names only, not dotted)
MIN_SYMBOL_LEN = 2


def find_doc_files(repo_path: Path) -> list[Path]:
    """Find all documentation files in the repo."""
    docs = []
    for pattern in DOC_GLOBS:
        docs.extend(repo_path.glob(pattern))
    return sorted(set(docs))


def _should_skip(sym: str) -> bool:
    """Check if a symbol should be filtered out."""
    base = sym.split(".")[0] if "." in sym else sym
    if len(base) < MIN_SYMBOL_LEN:
        return True
    if base.lower() in GENERIC_SYMBOLS:
        return True
    return False


def extract_symbols(doc_path: Path) -> list[dict]:
    """Extract code symbol references from a single doc file.

    Returns list of dicts with keys: symbol, kind, line_number
    """
    text = doc_path.read_text(errors="replace")
    lines = text.splitlines()
    symbols = []
    seen = set()
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Track fenced code blocks (``` or ~~~)
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Backtick function calls: `func()`
        for m in PATTERNS["backtick_ref"].finditer(line):
            sym = m.group(1)
            if _should_skip(sym):
                continue
            key = (sym, "function")
            if key not in seen:
                seen.add(key)
                symbols.append({"symbol": sym, "kind": "function", "line": i})

        # Backtick class refs: `ClassName`
        for m in PATTERNS["backtick_class"].finditer(line):
            sym = m.group(1)
            if sym in FALSE_POSITIVES or _should_skip(sym):
                continue
            key = (sym, "class")
            if key not in seen:
                seen.add(key)
                symbols.append({"symbol": sym, "kind": "class", "line": i})

        # Backtick module refs: `module.submodule`
        for m in PATTERNS["backtick_module"].finditer(line):
            sym = m.group(1)
            # Skip if it looks like a version number
            if re.match(r"\d", sym):
                continue
            key = (sym, "module")
            if key not in seen:
                seen.add(key)
                symbols.append({"symbol": sym, "kind": "module", "line": i})

        # File path references
        for m in PATTERNS["file_path"].finditer(line):
            sym = m.group(1)
            key = (sym, "file")
            if key not in seen:
                seen.add(key)
                symbols.append({"symbol": sym, "kind": "file", "line": i})

        # Import references
        for m in PATTERNS["import_ref"].finditer(line):
            if m.group(1):  # from X import Y
                mod = m.group(1)
                key = (mod, "module")
                if key not in seen:
                    seen.add(key)
                    symbols.append({"symbol": mod, "kind": "module", "line": i})
                for name in m.group(2).split(","):
                    name = name.strip()
                    if name:
                        key = (name, "function")
                        if key not in seen:
                            seen.add(key)
                            symbols.append({"symbol": name, "kind": "function", "line": i})
            elif m.group(3):  # import X
                mod = m.group(3)
                key = (mod, "module")
                if key not in seen:
                    seen.add(key)
                    symbols.append({"symbol": mod, "kind": "module", "line": i})

    return symbols


def scan_docs(repo_path: Path) -> dict[str, list[dict]]:
    """Scan all docs in repo, return {doc_relative_path: [symbols]}."""
    repo_path = Path(repo_path).resolve()
    doc_files = find_doc_files(repo_path)
    result = {}
    for doc in doc_files:
        symbols = extract_symbols(doc)
        if symbols:
            rel = str(doc.relative_to(repo_path))
            result[rel] = symbols
    return result

"""Track code symbol changes via git log."""

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def get_doc_last_modified(repo_path: Path, doc_rel_path: str) -> datetime | None:
    """Get the last commit date of a doc file."""
    out = run_git(
        ["log", "-1", "--format=%aI", "--", doc_rel_path],
        cwd=repo_path,
    )
    if out:
        return datetime.fromisoformat(out)
    return None


def find_symbol_in_code(repo_path: Path, symbol: str, kind: str) -> list[str]:
    """Find Python files that define a given symbol."""
    if kind == "file":
        # Symbol is a file path — check if it exists
        target = repo_path / symbol
        if target.exists():
            return [symbol]
        return []

    if kind == "module":
        # Convert dotted module to path
        parts = symbol.split(".")
        candidates = [
            "/".join(parts) + ".py",
            "/".join(parts) + "/__init__.py",
        ]
        found = []
        for c in candidates:
            if (repo_path / c).exists():
                found.append(c)
        return found

    # function or class: grep for definition
    if kind == "class":
        pattern = f"^class {symbol}"
    else:
        pattern = f"^def {symbol}|^    def {symbol}|^async def {symbol}"

    result = subprocess.run(
        ["git", "grep", "-l", "-E", pattern, "--", "*.py"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().splitlines()
    return []


def get_symbol_history(
    repo_path: Path, code_files: list[str], symbol: str, kind: str
) -> dict:
    """Get git history for a symbol's defining files.

    Returns dict with:
        last_modified: datetime of last change
        commit_count: number of commits touching these files
        last_commit_hash: short hash
        last_commit_msg: commit message
    """
    if not code_files:
        return {
            "last_modified": None,
            "commit_count": 0,
            "last_commit_hash": None,
            "last_commit_msg": None,
            "code_files": [],
        }

    # Get last modification date across all matching files
    latest = None
    latest_hash = None
    latest_msg = None
    total_commits = 0

    for f in code_files:
        # Last commit info
        out = run_git(
            ["log", "-1", "--format=%aI|%h|%s", "--", f],
            cwd=repo_path,
        )
        if out:
            parts = out.split("|", 2)
            dt = datetime.fromisoformat(parts[0])
            if latest is None or dt > latest:
                latest = dt
                latest_hash = parts[1]
                latest_msg = parts[2] if len(parts) > 2 else ""

        # Commit count
        out = run_git(
            ["rev-list", "--count", "HEAD", "--", f],
            cwd=repo_path,
        )
        if out:
            total_commits += int(out)

    return {
        "last_modified": latest,
        "commit_count": total_commits,
        "last_commit_hash": latest_hash,
        "last_commit_msg": latest_msg,
        "code_files": code_files,
    }


def track_symbols(
    repo_path: Path, doc_symbols: dict[str, list[dict]]
) -> list[dict]:
    """For each doc-symbol pair, find the code and get git history.

    Returns list of tracking records.
    """
    repo_path = Path(repo_path).resolve()
    records = []

    for doc_path, symbols in doc_symbols.items():
        doc_modified = get_doc_last_modified(repo_path, doc_path)

        for sym_info in symbols:
            symbol = sym_info["symbol"]
            kind = sym_info["kind"]

            code_files = find_symbol_in_code(repo_path, symbol, kind)
            if not code_files:
                continue  # Symbol not found in codebase, skip

            history = get_symbol_history(repo_path, code_files, symbol, kind)

            records.append({
                "doc_path": doc_path,
                "doc_line": sym_info["line"],
                "symbol": symbol,
                "kind": kind,
                "code_files": history["code_files"],
                "doc_modified": doc_modified,
                "code_modified": history["last_modified"],
                "commit_count": history["commit_count"],
                "last_commit_hash": history["last_commit_hash"],
                "last_commit_msg": history["last_commit_msg"],
            })

    return records

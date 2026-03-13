"""Parse git diff output to identify changed Python files and line ranges."""

import subprocess
from dataclasses import dataclass


@dataclass
class ChangedFile:
    path: str
    changed_lines: list[int]  # 1-based line numbers in the "after" version


def get_git_diff(ref: str = "HEAD~1") -> str:
    """Get unified diff between ref and current working tree."""
    result = subprocess.run(
        ["git", "diff", ref, "--unified=0", "--", "*.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    return result.stdout


def parse_diff(diff_text: str) -> list[ChangedFile]:
    """Parse unified diff to extract changed files and their changed line numbers."""
    files: dict[str, list[int]] = {}
    current_file: str | None = None

    for line in diff_text.splitlines():
        # New file header: +++ b/path/to/file.py
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file not in files:
                files[current_file] = []
        # Hunk header: @@ -old_start,old_count +new_start,new_count @@
        elif line.startswith("@@") and current_file:
            parts = line.split()
            for part in parts:
                if part.startswith("+") and "," in part:
                    start, count = part[1:].split(",")
                    start, count = int(start), int(count)
                    files[current_file].extend(range(start, start + count))
                elif part.startswith("+") and part[1:].isdigit():
                    files[current_file].append(int(part[1:]))

    return [
        ChangedFile(path=path, changed_lines=sorted(set(lines)))
        for path, lines in files.items()
        if path.endswith(".py") and lines
    ]


def get_changed_files(ref: str = "HEAD~1") -> list[ChangedFile]:
    """High-level: get list of changed Python files with line numbers."""
    diff_text = get_git_diff(ref)
    return parse_diff(diff_text)

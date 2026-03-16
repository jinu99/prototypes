"""Git diff integration: parse staged diff and identify changed lines."""

import re
import subprocess
from pathlib import Path


def get_staged_files() -> dict[str, set[int]]:
    """Return {filepath: set_of_changed_line_numbers} from git diff --staged."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "-U0", "--diff-filter=ACMR"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}

    return parse_unified_diff(result.stdout)


def parse_unified_diff(diff_text: str) -> dict[str, set[int]]:
    """Parse unified diff output to extract changed lines per file."""
    files: dict[str, set[int]] = {}
    current_file = None

    for line in diff_text.split("\n"):
        # Match +++ b/path/to/file
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file not in files:
                files[current_file] = set()
            continue

        # Match @@ hunk headers: @@ -old,count +new,count @@
        if line.startswith("@@") and current_file:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                for i in range(start, start + count):
                    files[current_file].add(i)

    return files

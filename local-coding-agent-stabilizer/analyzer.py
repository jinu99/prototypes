"""Destructive edit detection via diff analysis.

Detects:
1. File deletion (rm, unlink, or write_file with empty content)
2. Large-scale code loss (deletion ratio > threshold)
3. Empty file writes
"""

import json
import re

DELETE_RATIO_THRESHOLD = 0.8  # Block if >80% of lines are deleted


def analyze_tool_call(tool_name: str, arguments: dict) -> tuple[bool, str | None]:
    """Analyze a tool call for destructive patterns.

    Returns:
        (is_destructive, reason) — reason is None if not destructive.
    """
    name = tool_name.lower()

    # 1. File deletion tools
    if name in ("delete_file", "remove_file", "rm", "unlink"):
        path = arguments.get("path") or arguments.get("file_path") or arguments.get("target", "")
        return True, f"File deletion detected: {path}"

    # 2. Shell commands that delete files
    if name in ("run_command", "execute", "shell", "bash", "terminal"):
        cmd = arguments.get("command") or arguments.get("cmd") or ""
        if _is_destructive_command(cmd):
            return True, f"Destructive shell command detected: {cmd[:100]}"

    # 3. File write operations — check for empty or massive deletion
    if name in ("write_file", "write_to_file", "create_file", "overwrite_file"):
        return _check_write_operation(arguments)

    # 4. Edit/patch operations — check deletion ratio
    if name in ("edit_file", "apply_diff", "patch", "replace_in_file", "str_replace_editor"):
        return _check_edit_operation(arguments)

    return False, None


def _is_destructive_command(cmd: str) -> bool:
    """Check if a shell command is destructive."""
    dangerous_patterns = [
        r"\brm\s+(-[rRf]+\s+)*[^\s|;&]+",  # rm with paths
        r"\brm\s+-[rRf]*\s",                 # rm -rf
        r">\s*/dev/null\s*<",                 # redirect tricks
        r"truncate\s",                        # truncate
        r":\s*>\s*\S+",                       # : > file (empty file)
        r"echo\s+['\"]?['\"]?\s*>\s*\S+",    # echo "" > file
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, cmd):
            return True
    return False


def _check_write_operation(arguments: dict) -> tuple[bool, str | None]:
    """Check write operations for empty file writes or massive content loss."""
    content = arguments.get("content") or arguments.get("new_content") or ""
    path = arguments.get("path") or arguments.get("file_path") or arguments.get("target", "unknown")

    # Empty file write
    if not content.strip():
        return True, f"Empty file write detected: {path}"

    # Check if old_content is provided (some tools include it)
    old_content = arguments.get("old_content") or arguments.get("original_content")
    if old_content:
        return _check_deletion_ratio(old_content, content, path)

    return False, None


def _check_edit_operation(arguments: dict) -> tuple[bool, str | None]:
    """Check edit operations for large-scale deletion."""
    old = arguments.get("old_content") or arguments.get("original") or arguments.get("old_str") or ""
    new = arguments.get("new_content") or arguments.get("replacement") or arguments.get("new_str") or ""
    path = arguments.get("path") or arguments.get("file_path") or arguments.get("target", "unknown")

    # If we have a diff/patch string, analyze it
    diff = arguments.get("diff") or arguments.get("patch") or ""
    if diff:
        return _check_diff_string(diff, path)

    # If we have old and new content, compare
    if old:
        return _check_deletion_ratio(old, new, path)

    return False, None


def _check_deletion_ratio(old_content: str, new_content: str, path: str) -> tuple[bool, str | None]:
    """Check if the edit removes more than the threshold of content."""
    old_lines = old_content.strip().splitlines()
    new_lines = new_content.strip().splitlines()

    if not old_lines:
        return False, None

    old_count = len(old_lines)
    new_count = len(new_lines)

    if new_count == 0:
        return True, f"All content deleted from {path} ({old_count} lines removed)"

    deleted_ratio = max(0, (old_count - new_count)) / old_count

    if deleted_ratio > DELETE_RATIO_THRESHOLD:
        return True, (
            f"Excessive deletion in {path}: {deleted_ratio:.0%} of content removed "
            f"({old_count} → {new_count} lines)"
        )

    return False, None


def _check_diff_string(diff: str, path: str) -> tuple[bool, str | None]:
    """Analyze a unified diff string for excessive deletions."""
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))

    if removed == 0:
        return False, None

    total_changes = added + removed
    deletion_ratio = removed / total_changes if total_changes > 0 else 0

    if deletion_ratio > DELETE_RATIO_THRESHOLD and removed > 5:
        return True, (
            f"Diff shows excessive deletion in {path}: "
            f"{removed} lines removed vs {added} added ({deletion_ratio:.0%} deletion ratio)"
        )

    return False, None

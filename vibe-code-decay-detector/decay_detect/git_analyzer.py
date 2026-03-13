"""Git history analysis: extract commits, file contents at each commit, churn stats."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommitInfo:
    hash: str
    timestamp: int
    author: str
    message: str


@dataclass
class ChurnStats:
    additions: int
    deletions: int
    files_changed: int


def get_commit_list(repo_path: Path, max_commits: int = 200) -> list[CommitInfo]:
    """Get list of commits from oldest to newest."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%at|%an|%s", "--reverse",
             f"-{max_commits}"],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        return []
    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commits.append(CommitInfo(
            hash=parts[0],
            timestamp=int(parts[1]),
            author=parts[2],
            message=parts[3],
        ))
    return commits


def get_python_files_at_commit(repo_path: Path, commit_hash: str) -> list[str]:
    """List .py files tracked at a specific commit."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit_hash],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    files = []
    for f in result.stdout.strip().split("\n"):
        f = f.strip()
        if f.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
            files.append(f)
    return files


def get_file_content_at_commit(
    repo_path: Path, commit_hash: str, file_path: str
) -> bytes | None:
    """Get file content at a specific commit."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{file_path}"],
            cwd=repo_path, capture_output=True, check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def get_churn_stats(repo_path: Path, commit_hash: str) -> ChurnStats:
    """Get additions/deletions/files_changed for a commit."""
    result = subprocess.run(
        ["git", "diff-tree", "--numstat", "-r", "--root", commit_hash],
        cwd=repo_path, capture_output=True, text=True,
    )
    additions, deletions, files_changed = 0, 0, 0
    for line in result.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                additions += int(parts[0])
                deletions += int(parts[1])
                files_changed += 1
            except ValueError:
                files_changed += 1  # binary file
    return ChurnStats(additions=additions, deletions=deletions,
                      files_changed=files_changed)


def get_diff_files(repo_path: Path, commit_hash: str) -> list[dict]:
    """Get list of files changed in a commit with their status (A/D/M)."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--root", "--name-status", commit_hash],
        cwd=repo_path, capture_output=True, text=True,
    )
    files = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            files.append({"status": parts[0], "path": parts[1]})
    return files

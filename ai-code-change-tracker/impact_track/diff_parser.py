"""git diff를 파싱하여 변경된 파일과 라인 범위를 추출한다."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HunkRange:
    start: int
    count: int


@dataclass
class ChangedFile:
    path: str
    added_lines: list[int] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)


def get_git_root(path: str | Path) -> Path:
    """git 저장소 루트 디렉토리를 찾는다."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        cwd=str(path),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Not a git repository: {path}")
    return Path(result.stdout.strip())


def run_git_diff(repo_path: str | Path, revision: str = "HEAD~1") -> str:
    """git diff를 실행하여 unified diff 문자열을 반환한다."""
    result = subprocess.run(
        ["git", "diff", revision, "HEAD", "--unified=0"],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    return result.stdout


def parse_diff(diff_text: str) -> list[ChangedFile]:
    """unified diff 텍스트를 파싱하여 변경된 파일별 라인 정보를 추출한다."""
    files: dict[str, ChangedFile] = {}
    current_file: str | None = None
    # new file path in diff
    file_pattern = re.compile(r"^\+\+\+ b/(.+)$")
    # @@ -old_start,old_count +new_start,new_count @@
    hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    for line in diff_text.splitlines():
        m = file_pattern.match(line)
        if m:
            current_file = m.group(1)
            if current_file not in files:
                files[current_file] = ChangedFile(path=current_file)
            continue

        m = hunk_pattern.match(line)
        if m and current_file:
            old_start = int(m.group(1))
            old_count = int(m.group(2) or "1")
            new_start = int(m.group(3))
            new_count = int(m.group(4) or "1")

            cf = files[current_file]
            for i in range(old_start, old_start + old_count):
                cf.removed_lines.append(i)
            for i in range(new_start, new_start + new_count):
                cf.added_lines.append(i)

    return list(files.values())


def get_changed_files(repo_path: str | Path, revision: str = "HEAD~1") -> list[ChangedFile]:
    """지정된 리비전부터 HEAD까지 변경된 파일과 라인 정보를 반환한다."""
    diff_text = run_git_diff(repo_path, revision)
    return parse_diff(diff_text)

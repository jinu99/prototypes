"""Detect commit-revert patterns: add-delete loops, rapid edits on same files."""

from dataclasses import dataclass
from .git_analyzer import CommitInfo


@dataclass
class FileAction:
    commit_hash: str
    timestamp: int
    status: str  # A, D, M
    path: str


def detect_add_delete_patterns(
    file_actions: list[FileAction],
) -> list[dict]:
    """Detect files that are added then deleted (or vice versa) within short spans."""
    # Group actions by file
    by_file: dict[str, list[FileAction]] = {}
    for action in file_actions:
        by_file.setdefault(action.path, []).append(action)

    patterns = []
    for path, actions in by_file.items():
        actions.sort(key=lambda a: a.timestamp)
        for i in range(len(actions) - 1):
            curr = actions[i]
            nxt = actions[i + 1]
            # Add then delete
            if curr.status == "A" and nxt.status == "D":
                patterns.append({
                    "file": path,
                    "type": "add-delete",
                    "commit1": curr.commit_hash[:8],
                    "commit2": nxt.commit_hash[:8],
                    "detail": f"Added in {curr.commit_hash[:8]}, deleted in {nxt.commit_hash[:8]}",
                })
            # Delete then add (revert-like)
            elif curr.status == "D" and nxt.status == "A":
                patterns.append({
                    "file": path,
                    "type": "delete-readd",
                    "commit1": curr.commit_hash[:8],
                    "commit2": nxt.commit_hash[:8],
                    "detail": f"Deleted in {curr.commit_hash[:8]}, re-added in {nxt.commit_hash[:8]}",
                })

    return patterns


def detect_rapid_edits(
    file_actions: list[FileAction],
    threshold_seconds: int = 3600,
    min_edits: int = 3,
) -> list[dict]:
    """Detect files modified many times in a short window (rapid churn)."""
    by_file: dict[str, list[FileAction]] = {}
    for action in file_actions:
        if action.status == "M":
            by_file.setdefault(action.path, []).append(action)

    patterns = []
    for path, actions in by_file.items():
        actions.sort(key=lambda a: a.timestamp)
        # Sliding window
        for i in range(len(actions)):
            window = [actions[i]]
            for j in range(i + 1, len(actions)):
                if actions[j].timestamp - actions[i].timestamp <= threshold_seconds:
                    window.append(actions[j])
                else:
                    break
            if len(window) >= min_edits:
                patterns.append({
                    "file": path,
                    "type": "rapid-edit",
                    "count": len(window),
                    "commit1": window[0].commit_hash[:8],
                    "commit2": window[-1].commit_hash[:8],
                    "detail": (
                        f"{len(window)} edits within "
                        f"{(window[-1].timestamp - window[0].timestamp) // 60}min"
                    ),
                })
                break  # One pattern per file

    return patterns

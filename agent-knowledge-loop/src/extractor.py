"""Extract failure-resolution patterns from agent session logs.

Uses pattern matching as a mock LLM extractor.
In production, this would call an LLM API to analyze the session.
"""
import json
import re
from pathlib import Path

# Signals that indicate a failure occurred
FAILURE_SIGNALS = [
    "error", "Error", "ERROR", "fail", "Fail", "FAIL",
    "cannot", "Cannot", "CANNOT", "not found", "Not found",
    "충돌", "실패", "에러", "문제", "안 됩", "안됩", "안 돼", "안돼",
    "CONFLICT", "Exception", "Traceback", "denied", "refused",
    "DeprecationWarning", "ImportError", "ModuleNotFoundError",
]

# Signals that indicate a resolution
RESOLUTION_SIGNALS = [
    "수정", "해결", "변경", "업그레이드", "바꾸", "고정",
    "fix", "Fix", "resolve", "change", "update", "upgrade",
    "동작합니다", "완벽합니다", "감사합니다", "잘 됩니다",
    "Successfully", "successfully", "works", "solved",
]

CATEGORY_KEYWORDS = {
    "docker": ["docker", "Docker", "container", "컨테이너", "Dockerfile", "image"],
    "git": ["git", "Git", "merge", "conflict", "충돌", "branch", "commit", "rebase"],
    "dependency": ["pip", "npm", "import", "module", "package", "버전", "version", "install", "dependency"],
    "config": ["config", "설정", "환경변수", "env", "yaml", "json", "toml"],
    "runtime": ["runtime", "실행", "crash", "segfault", "OOM", "timeout"],
}


def _detect_category(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw.lower() in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def _has_signal(text: str, signals: list[str]) -> bool:
    return any(s in text for s in signals)


def _extract_from_jsonl(lines: list[dict]) -> list[dict]:
    """Extract failure-resolution patterns from parsed JSONL messages."""
    lessons = []
    full_text = " ".join(m.get("content", "") for m in lines)
    category = _detect_category(full_text)

    # Walk through messages looking for failure→resolution arcs
    failure_ctx = None
    for i, msg in enumerate(lines):
        content = msg.get("content", "")
        role = msg.get("role", "")

        # Tool output with error
        if role == "tool" and _has_signal(content, FAILURE_SIGNALS):
            failure_ctx = {
                "error_msg": content.strip(),
                "index": i,
            }
            # Look backwards for the user/assistant message that triggered this
            for j in range(i - 1, -1, -1):
                if lines[j].get("role") in ("user", "assistant"):
                    failure_ctx["trigger"] = lines[j].get("content", "").strip()
                    break

        # User message with a problem
        elif role == "user" and _has_signal(content, FAILURE_SIGNALS) and not failure_ctx:
            failure_ctx = {
                "error_msg": content.strip(),
                "index": i,
            }

        # Resolution: assistant explains the fix, or user confirms it worked
        # Skip tool outputs — they contain raw command output, not explanations
        elif failure_ctx and role in ("assistant", "user") and _has_signal(content, RESOLUTION_SIGNALS):
            resolution_text = content.strip()
            if role == "user":
                # User confirmed — look back for assistant's fix
                for j in range(i - 1, -1, -1):
                    if lines[j].get("role") == "assistant":
                        resolution_text = lines[j].get("content", "").strip()
                        break

            # Build the lesson
            failure_summary = _summarize(failure_ctx["error_msg"], max_len=200)
            resolution_summary = _summarize(resolution_text, max_len=200)
            rule = _generate_rule(failure_summary, resolution_summary, category)

            lessons.append({
                "category": category,
                "failure": failure_summary,
                "resolution": resolution_summary,
                "rule": rule,
                "tags": [category],
            })
            failure_ctx = None  # Reset for next pattern

    return lessons


def _summarize(text: str, max_len: int = 200) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _generate_rule(failure: str, resolution: str, category: str) -> str:
    """Generate a concise rule from failure-resolution pair."""
    # Truncate for rule brevity
    short_failure = _summarize(failure, 80)
    short_resolution = _summarize(resolution, 120)
    prefixes = {
        "docker": "Docker",
        "git": "Git",
        "dependency": "Dependencies",
        "config": "Config",
        "runtime": "Runtime",
        "general": "General",
    }
    prefix = prefixes.get(category, "General")
    return f"[{prefix}] {short_resolution} (trigger: {short_failure})"


def extract_lessons(log_path: Path) -> list[dict]:
    """Main entry point: extract lessons from a session log file."""
    text = log_path.read_text(encoding="utf-8")
    lines = []

    # Try JSONL
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            # Not valid JSONL — treat as plain text
            lines = None
            break

    if lines:
        lessons = _extract_from_jsonl(lines)
    else:
        # Plain text fallback: split into chunks and analyze
        lessons = _extract_from_plaintext(text)

    # Tag each lesson with source file
    for lesson in lessons:
        lesson["source_file"] = str(log_path.name)

    return lessons


def _extract_from_plaintext(text: str) -> list[dict]:
    """Fallback extractor for non-JSONL logs."""
    category = _detect_category(text)
    paragraphs = re.split(r"\n\n+", text)

    lessons = []
    failure_text = None
    for para in paragraphs:
        if _has_signal(para, FAILURE_SIGNALS):
            failure_text = para.strip()
        elif failure_text and _has_signal(para, RESOLUTION_SIGNALS):
            lessons.append({
                "category": category,
                "failure": _summarize(failure_text),
                "resolution": _summarize(para.strip()),
                "rule": _generate_rule(
                    _summarize(failure_text, 100),
                    _summarize(para.strip(), 100),
                    category,
                ),
                "tags": [category],
            })
            failure_text = None

    return lessons

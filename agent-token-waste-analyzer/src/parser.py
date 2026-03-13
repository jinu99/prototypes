"""Claude Code session log parser — extracts tool call sequences and token usage."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolCall:
    name: str
    input_args: dict
    message_index: int
    token_usage: dict = field(default_factory=dict)
    # For Read/Grep/Glob: the target path or pattern
    target: str = ""


@dataclass
class SessionMessage:
    index: int
    type: str  # user, assistant, tool_result, file-history-snapshot
    role: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)
    content_text: str = ""
    timestamp: str = ""


@dataclass
class SessionData:
    session_id: str
    messages: list[SessionMessage] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0


def extract_target(tool_name: str, input_args: dict) -> str:
    """Extract the primary target (file path or pattern) from tool input."""
    if tool_name == "Read":
        return input_args.get("file_path", "")
    elif tool_name in ("Grep", "Glob"):
        return input_args.get("pattern", "")
    elif tool_name == "Edit":
        return input_args.get("file_path", "")
    elif tool_name == "Write":
        return input_args.get("file_path", "")
    elif tool_name == "Bash":
        return input_args.get("command", "")[:100]
    return ""


def parse_session(path: Path) -> SessionData:
    """Parse a JSONL session log file into structured SessionData."""
    session_id = path.stem
    session = SessionData(session_id=session_id)

    with open(path, "r") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type", "")
            if msg_type == "file-history-snapshot":
                continue

            msg = obj.get("message", {})
            role = msg.get("role", "")
            usage = msg.get("usage", {})

            session_msg = SessionMessage(
                index=idx,
                type=msg_type,
                role=role,
                timestamp=obj.get("timestamp", ""),
            )

            if usage:
                session_msg.token_usage = usage
                session.total_input_tokens += usage.get("input_tokens", 0)
                session.total_output_tokens += usage.get("output_tokens", 0)
                session.total_cache_read_tokens += usage.get(
                    "cache_read_input_tokens", 0
                )
                session.total_cache_creation_tokens += usage.get(
                    "cache_creation_input_tokens", 0
                )

            # Extract tool calls from assistant messages
            if msg_type == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tc = ToolCall(
                                name=item.get("name", ""),
                                input_args=item.get("input", {}),
                                message_index=idx,
                                token_usage=usage,
                                target=extract_target(
                                    item.get("name", ""),
                                    item.get("input", {}),
                                ),
                            )
                            session_msg.tool_calls.append(tc)
                            session.tool_calls.append(tc)
                elif isinstance(content, str):
                    session_msg.content_text = content

            session.messages.append(session_msg)

    return session


def find_session_logs(base_dir: Path | None = None) -> list[Path]:
    """Find all JSONL session logs under Claude Code projects directory."""
    if base_dir is None:
        base_dir = Path.home() / ".claude" / "projects"
    if not base_dir.exists():
        return []
    return sorted(base_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

"""Parse Claude Code JSONL session logs into structured events."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolCall:
    name: str
    tool_id: str
    input: dict
    timestamp: str
    uuid: str


@dataclass
class FileChange:
    """A file modification extracted from a tool call."""
    file_path: str
    change_type: str  # "edit", "write", "bash_write"
    old_string: str | None = None
    new_string: str | None = None
    command: str | None = None  # for Bash-based changes


@dataclass
class PromptSegment:
    """A user prompt and all assistant actions that followed it."""
    prompt_text: str
    prompt_uuid: str
    prompt_timestamp: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    assistant_text: list[str] = field(default_factory=list)


def extract_prompt_text(message: dict) -> str:
    """Extract text from a user message content field."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def extract_file_changes(tool: ToolCall) -> list[FileChange]:
    """Extract file changes from a tool call."""
    changes = []
    inp = tool.input

    if tool.name == "Edit":
        changes.append(FileChange(
            file_path=inp.get("file_path", ""),
            change_type="edit",
            old_string=inp.get("old_string"),
            new_string=inp.get("new_string"),
        ))
    elif tool.name == "Write":
        content = inp.get("content", "")
        changes.append(FileChange(
            file_path=inp.get("file_path", ""),
            change_type="write",
            new_string=content[:500] + ("..." if len(content) > 500 else ""),
        ))
    elif tool.name == "Bash":
        cmd = inp.get("command", "")
        # Detect file-writing bash commands
        write_indicators = [">", "cat <<", "tee ", "echo ", "printf "]
        if any(ind in cmd for ind in write_indicators):
            changes.append(FileChange(
                file_path="(via bash)",
                change_type="bash_write",
                command=cmd[:300],
            ))

    return changes


def parse_session(jsonl_path: str | Path) -> list[PromptSegment]:
    """Parse a JSONL session file into prompt segments."""
    jsonl_path = Path(jsonl_path)
    events = []

    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    segments: list[PromptSegment] = []
    current_segment: PromptSegment | None = None

    for event in events:
        etype = event.get("type")

        if etype == "user":
            msg = event.get("message", {})
            text = extract_prompt_text(msg)
            # Skip empty or system-only prompts
            if not text.strip():
                continue
            # Skip context continuation summaries (not real user prompts)
            if text.startswith("This session is being continued"):
                continue
            current_segment = PromptSegment(
                prompt_text=text,
                prompt_uuid=event.get("uuid", ""),
                prompt_timestamp=event.get("timestamp", ""),
            )
            segments.append(current_segment)

        elif etype == "assistant" and current_segment is not None:
            msg = event.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "text":
                        current_segment.assistant_text.append(item["text"])
                    elif item.get("type") == "tool_use":
                        tc = ToolCall(
                            name=item.get("name", ""),
                            tool_id=item.get("id", ""),
                            input=item.get("input", {}),
                            timestamp=event.get("timestamp", ""),
                            uuid=event.get("uuid", ""),
                        )
                        current_segment.tool_calls.append(tc)
                        current_segment.file_changes.extend(
                            extract_file_changes(tc)
                        )

    return segments

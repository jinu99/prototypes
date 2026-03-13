"""Token counting for OpenAI Chat Completions API components."""

import json
import tiktoken

# Use cl100k_base (GPT-4/3.5-turbo default)
_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a string."""
    if not text:
        return 0
    return len(_enc.encode(text))


def count_message_tokens(message: dict) -> int:
    """Count tokens in a single message (OpenAI format overhead included)."""
    # Every message has 3 overhead tokens: <|start|>role<|end|>
    tokens = 3
    tokens += count_tokens(message.get("role", ""))
    content = message.get("content")
    if isinstance(content, str):
        tokens += count_tokens(content)
    elif isinstance(content, list):
        # Multi-part content (text parts only)
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                tokens += count_tokens(part.get("text", ""))
    # Tool calls in assistant messages
    if "tool_calls" in message:
        for tc in message["tool_calls"]:
            fn = tc.get("function", {})
            tokens += count_tokens(fn.get("name", ""))
            tokens += count_tokens(fn.get("arguments", ""))
    # Tool call ID for tool messages
    if message.get("tool_call_id"):
        tokens += count_tokens(message["tool_call_id"])
    if message.get("name"):
        tokens += count_tokens(message["name"])
    return tokens


def count_tools_tokens(tools: list | None) -> int:
    """Count tokens in tools/functions definitions."""
    if not tools:
        return 0
    return count_tokens(json.dumps(tools, ensure_ascii=False))


def analyze_request(body: dict) -> dict:
    """Analyze an OpenAI Chat Completions request body.

    Returns component-level token breakdown.
    """
    messages = body.get("messages", [])
    tools = body.get("tools") or body.get("functions")

    components = {
        "system": 0,
        "user": 0,
        "assistant": 0,
        "tool": 0,
        "tools_definition": 0,
    }
    message_details = []

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        tokens = count_message_tokens(msg)
        bucket = role if role in components else "tool"
        components[bucket] += tokens

        # Summarize content for diff display
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        preview = (content[:120] + "...") if len(str(content)) > 120 else str(content)

        message_details.append({
            "index": i,
            "role": role,
            "tokens": tokens,
            "preview": preview,
        })

    components["tools_definition"] = count_tools_tokens(tools)

    total = sum(components.values())
    # 3 tokens for reply priming
    total += 3

    warnings = []
    if total > 0:
        for comp, count in components.items():
            ratio = count / total
            if ratio > 0.5:
                warnings.append({
                    "component": comp,
                    "ratio": round(ratio, 3),
                    "tokens": count,
                    "message": f"{comp} uses {ratio:.1%} of context ({count}/{total} tokens)",
                })

    return {
        "components": components,
        "total_tokens": total,
        "warnings": warnings,
        "messages": message_details,
        "model": body.get("model", "unknown"),
    }

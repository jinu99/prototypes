"""Mock LLM runtime — executes agent instances with their configured tool sets."""

import json
import time

# Mock tool execution results
TOOL_MOCK_RESULTS = {
    "Search": lambda params: f"검색 결과: '{params.get('query', '')}' 관련 정보 3건을 찾았습니다.",
    "Memory": lambda params: (
        f"메모리 저장 완료: {params.get('key', '')}"
        if params.get("action") == "write"
        else f"메모리 조회: {params.get('key', '')} = '저장된 값'"
    ),
    "Slack": lambda params: f"Slack #{params.get('channel', 'general')}에 메시지 전송 완료.",
    "Email": lambda params: f"{params.get('to', '')}에게 이메일 발송 완료.",
    "Orchestrator": lambda params: f"에이전트 '{params.get('target_agent', '')}'에 작업 위임 완료.",
    "CodeExec": lambda params: f"코드 실행 결과: 42 (mock result)",
}


def mock_tool_call(tool_name: str, context: str) -> dict:
    """Simulate a tool being called by the LLM."""
    mock_fn = TOOL_MOCK_RESULTS.get(tool_name)
    if not mock_fn:
        return {"tool": tool_name, "result": f"[{tool_name}] 실행 완료 (mock)"}
    result = mock_fn({"query": context, "key": "context", "action": "read",
                       "channel": "general", "message": context,
                       "to": "user@example.com", "subject": "결과 보고",
                       "body": context, "target_agent": "helper", "task": context,
                       "code": ""})
    return {"tool": tool_name, "result": result}


def execute_agent(
    system_prompt: str,
    tool_names: list[str],
    permissions: list[str],
    llm_config: dict,
    user_message: str,
) -> dict:
    """
    Mock LLM agent execution.

    Returns:
        dict with keys: output, tools_used, duration_ms, status, error_message
    """
    start = time.time()

    try:
        used_tools = _select_tools(tool_names, user_message)
        tool_results = [mock_tool_call(t, user_message) for t in used_tools]
        response = _generate_response(system_prompt, user_message, tool_results, llm_config)

        duration_ms = int((time.time() - start) * 1000)
        return {
            "output": response,
            "tools_used": used_tools,
            "duration_ms": duration_ms,
            "status": "success",
            "error_message": None,
        }

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return {
            "output": "",
            "tools_used": [],
            "duration_ms": duration_ms,
            "status": "error",
            "error_message": str(e),
        }


def _select_tools(available_tools: list[str], message: str) -> list[str]:
    """Heuristically select tools based on message keywords."""
    selected = []
    keywords = {
        "Search": ["검색", "찾아", "search", "find", "조회"],
        "Memory": ["기억", "저장", "memory", "remember", "recall"],
        "Slack": ["슬랙", "알림", "slack", "notify", "channel"],
        "Email": ["메일", "이메일", "email", "send mail"],
        "Orchestrator": ["위임", "delegate", "orchestrate", "다른 에이전트"],
        "CodeExec": ["코드", "실행", "code", "execute", "run"],
    }

    msg_lower = message.lower()
    for tool_name in available_tools:
        tool_keywords = keywords.get(tool_name, [])
        if any(kw in msg_lower for kw in tool_keywords):
            selected.append(tool_name)

    if not selected and available_tools:
        selected.append(available_tools[0])

    return selected


def _generate_response(
    system_prompt: str, user_message: str,
    tool_results: list[dict], llm_config: dict
) -> str:
    """Generate a mock LLM response."""
    parts = []

    if system_prompt:
        parts.append(f"[역할: {system_prompt[:80]}{'...' if len(system_prompt) > 80 else ''}]")

    if tool_results:
        parts.append("사용한 도구:")
        for tr in tool_results:
            parts.append(f"  • {tr['tool']}: {tr['result']}")
        parts.append("")

    parts.append(f'요청 "{user_message}"에 대한 처리를 완료했습니다.')
    parts.append(f"(모델: {llm_config.get('model', 'mock-gpt')}, "
                 f"temperature: {llm_config.get('temperature', 0.7)})")

    return "\n".join(parts)

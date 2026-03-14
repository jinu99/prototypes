"""OpenAI-compatible reverse proxy with destructive edit detection."""

import json
import time
import uuid
import asyncio
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from analyzer import analyze_tool_call
from loop_detector import get_tracker, clear_tracker
from db import init_db, create_session, end_session, log_tool_call, get_sessions, get_tool_calls, get_blocked_events

# Config
BACKEND_URL = "http://localhost:11434"  # Ollama default
PROXY_PORT = 8400
MOCK_MODE = False  # Set via --mock flag


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Coding Agent Stabilizer", lifespan=lifespan)


# ── Dashboard routes ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(html_path.read_text())


@app.get("/api/sessions")
async def api_sessions():
    return await get_sessions()


@app.get("/api/tool-calls")
async def api_tool_calls(session_id: str | None = None):
    return await get_tool_calls(session_id)


@app.get("/api/blocked")
async def api_blocked():
    return await get_blocked_events()


@app.get("/api/stats")
async def api_stats():
    sessions = await get_sessions()
    calls = await get_tool_calls()
    blocked = await get_blocked_events()
    return {
        "total_sessions": len(sessions),
        "active_sessions": sum(1 for s in sessions if s["status"] == "active"),
        "total_tool_calls": len(calls),
        "total_blocked": len(blocked),
    }


# ── OpenAI-compatible proxy routes ──────────────────────────────

@app.get("/v1/models")
@app.get("/api/tags")
async def proxy_models():
    """Forward model listing."""
    if MOCK_MODE:
        return {"object": "list", "data": [
            {"id": "mock-model", "object": "model", "owned_by": "local"}
        ]}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BACKEND_URL}/v1/models", timeout=10)
            return Response(content=resp.content, status_code=resp.status_code,
                          headers={"content-type": resp.headers.get("content-type", "application/json")})
        except httpx.ConnectError:
            return JSONResponse({"error": "Backend not reachable", "backend": BACKEND_URL}, status_code=502)


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """Main proxy endpoint: intercept tool calls, detect destructive edits."""
    body = await request.json()
    session_id = request.headers.get("x-session-id", str(uuid.uuid4())[:8])
    await create_session(session_id)

    is_streaming = body.get("stream", False)

    if MOCK_MODE:
        return await _mock_response(body, session_id, is_streaming)

    # Forward to backend
    async with httpx.AsyncClient() as client:
        try:
            if is_streaming:
                return await _proxy_streaming(client, body, session_id)
            else:
                return await _proxy_non_streaming(client, body, session_id)
        except httpx.ConnectError:
            return JSONResponse(
                {"error": "Backend not reachable", "backend": BACKEND_URL},
                status_code=502,
            )


async def _proxy_non_streaming(client: httpx.AsyncClient, body: dict, session_id: str):
    """Forward non-streaming request, inspect response for tool calls."""
    resp = await client.post(
        f"{BACKEND_URL}/v1/chat/completions",
        json=body,
        timeout=120,
    )
    data = resp.json()

    # Check tool calls in response
    choices = data.get("choices", [])
    for choice in choices:
        msg = choice.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            try:
                arguments = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            # Destructive edit check
            is_destructive, reason = analyze_tool_call(tool_name, arguments)
            if is_destructive:
                await log_tool_call(session_id, tool_name, arguments, blocked=True, block_reason=reason)
                return _blocked_response(reason, session_id)

            # Loop check
            tracker = get_tracker(session_id)
            is_loop, loop_reason = tracker.check_and_record(tool_name, arguments)
            if is_loop:
                await log_tool_call(session_id, tool_name, arguments, blocked=True, block_reason=loop_reason)
                await end_session(session_id, "halted_loop")
                return _blocked_response(loop_reason, session_id)

            await log_tool_call(session_id, tool_name, arguments)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={"content-type": "application/json"},
    )


async def _proxy_streaming(client: httpx.AsyncClient, body: dict, session_id: str):
    """Forward streaming request, buffer tool calls for inspection."""

    async def stream_generator():
        tool_call_buffer: dict[int, dict] = {}  # index -> {name, arguments_parts}
        blocked = False

        async with client.stream(
            "POST",
            f"{BACKEND_URL}/v1/chat/completions",
            json=body,
            timeout=120,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    if line.strip():
                        yield line + "\n"
                    continue

                payload = line[6:].strip()
                if payload == "[DONE]":
                    # Before sending DONE, analyze buffered tool calls
                    for idx, tc_data in tool_call_buffer.items():
                        tool_name = tc_data.get("name", "")
                        args_str = "".join(tc_data.get("argument_parts", []))
                        try:
                            arguments = json.loads(args_str) if args_str else {}
                        except json.JSONDecodeError:
                            arguments = {}

                        is_destructive, reason = analyze_tool_call(tool_name, arguments)
                        if is_destructive:
                            await log_tool_call(session_id, tool_name, arguments, blocked=True, block_reason=reason)
                            blocked = True
                            # Send a warning chunk
                            warn = _blocked_sse_chunk(reason, session_id)
                            yield f"data: {json.dumps(warn)}\n\n"
                            break

                        tracker = get_tracker(session_id)
                        is_loop, loop_reason = tracker.check_and_record(tool_name, arguments)
                        if is_loop:
                            await log_tool_call(session_id, tool_name, arguments, blocked=True, block_reason=loop_reason)
                            await end_session(session_id, "halted_loop")
                            blocked = True
                            warn = _blocked_sse_chunk(loop_reason, session_id)
                            yield f"data: {json.dumps(warn)}\n\n"
                            break

                        await log_tool_call(session_id, tool_name, arguments)

                    yield "data: [DONE]\n\n"
                    continue

                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    yield line + "\n"
                    continue

                # Buffer tool call deltas
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta", {})
                    for tc in delta.get("tool_calls", []):
                        idx = tc.get("index", 0)
                        if idx not in tool_call_buffer:
                            tool_call_buffer[idx] = {"name": "", "argument_parts": []}
                        if "function" in tc:
                            if "name" in tc["function"]:
                                tool_call_buffer[idx]["name"] = tc["function"]["name"]
                            if "arguments" in tc["function"]:
                                tool_call_buffer[idx]["argument_parts"].append(tc["function"]["arguments"])

                # Forward chunk as-is (we block at DONE if needed)
                yield line + "\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


def _blocked_response(reason: str, session_id: str) -> JSONResponse:
    """Return a blocked response mimicking OpenAI format."""
    return JSONResponse({
        "id": f"blocked-{session_id}",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"⚠️ BLOCKED by Stabilizer: {reason}",
            },
            "finish_reason": "stop",
        }],
        "stabilizer": {"blocked": True, "reason": reason},
    })


def _blocked_sse_chunk(reason: str, session_id: str) -> dict:
    """Return a blocked SSE chunk."""
    return {
        "id": f"blocked-{session_id}",
        "object": "chat.completion.chunk",
        "choices": [{
            "index": 0,
            "delta": {"content": f"\n⚠️ BLOCKED by Stabilizer: {reason}"},
            "finish_reason": "stop",
        }],
    }


# ── Mock mode for demo/testing ──────────────────────────────────

async def _mock_response(body: dict, session_id: str, streaming: bool):
    """Generate mock responses that simulate tool calls for testing."""
    messages = body.get("messages", [])
    last_msg = messages[-1].get("content", "") if messages else ""

    # Determine which mock scenario to use
    scenario = _detect_mock_scenario(last_msg, body)

    if streaming:
        return StreamingResponse(
            _mock_stream(scenario, session_id),
            media_type="text/event-stream",
        )
    else:
        return JSONResponse(await _mock_non_stream(scenario, session_id))


def _detect_mock_scenario(content: str, body: dict) -> str:
    """Detect which demo scenario to simulate based on message content."""
    content_lower = content.lower()
    if "delete" in content_lower or "remove" in content_lower:
        return "destructive_delete"
    if "empty" in content_lower or "clear" in content_lower:
        return "empty_write"
    if "rewrite" in content_lower or "refactor all" in content_lower:
        return "massive_deletion"
    if "loop" in content_lower or "repeat" in content_lower:
        return "loop"
    return "normal"


async def _mock_non_stream(scenario: str, session_id: str) -> dict:
    """Generate a mock non-streaming response."""
    base = {
        "id": f"mock-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "mock-model",
    }

    if scenario == "destructive_delete":
        tc = {"name": "delete_file", "arguments": json.dumps({"path": "/src/main.py"})}
        msg = {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_1", "type": "function", "function": tc}
        ]}
        # Run analysis
        args = json.loads(tc["arguments"])
        is_destructive, reason = analyze_tool_call(tc["name"], args)
        if is_destructive:
            await log_tool_call(session_id, tc["name"], args, blocked=True, block_reason=reason)
            return {**base, "choices": [{"index": 0, "message": {
                "role": "assistant",
                "content": f"⚠️ BLOCKED by Stabilizer: {reason}",
            }, "finish_reason": "stop"}], "stabilizer": {"blocked": True, "reason": reason}}

    elif scenario == "empty_write":
        tc = {"name": "write_file", "arguments": json.dumps({"path": "/src/utils.py", "content": ""})}
        args = json.loads(tc["arguments"])
        is_destructive, reason = analyze_tool_call(tc["name"], args)
        if is_destructive:
            await log_tool_call(session_id, tc["name"], args, blocked=True, block_reason=reason)
            return {**base, "choices": [{"index": 0, "message": {
                "role": "assistant",
                "content": f"⚠️ BLOCKED by Stabilizer: {reason}",
            }, "finish_reason": "stop"}], "stabilizer": {"blocked": True, "reason": reason}}

    elif scenario == "massive_deletion":
        old = "\n".join(f"line {i}" for i in range(100))
        new = "# emptied"
        tc = {"name": "write_file", "arguments": json.dumps({
            "path": "/src/app.py", "content": new, "old_content": old
        })}
        args = json.loads(tc["arguments"])
        is_destructive, reason = analyze_tool_call(tc["name"], args)
        if is_destructive:
            await log_tool_call(session_id, tc["name"], args, blocked=True, block_reason=reason)
            return {**base, "choices": [{"index": 0, "message": {
                "role": "assistant",
                "content": f"⚠️ BLOCKED by Stabilizer: {reason}",
            }, "finish_reason": "stop"}], "stabilizer": {"blocked": True, "reason": reason}}

    elif scenario == "loop":
        tracker = get_tracker(session_id)
        tc_name = "edit_file"
        tc_args = {"path": "/src/config.py", "content": "x = 1"}
        for i in range(3):
            is_loop, loop_reason = tracker.check_and_record(tc_name, tc_args)
            await log_tool_call(session_id, tc_name, tc_args,
                              blocked=is_loop, block_reason=loop_reason)
            if is_loop:
                await end_session(session_id, "halted_loop")
                return {**base, "choices": [{"index": 0, "message": {
                    "role": "assistant",
                    "content": f"⚠️ BLOCKED by Stabilizer: {loop_reason}",
                }, "finish_reason": "stop"}], "stabilizer": {"blocked": True, "reason": loop_reason}}

    # Normal response
    await log_tool_call(session_id, "write_file", {"path": "/src/hello.py", "content": "print('hello')"})
    return {**base, "choices": [{"index": 0, "message": {
        "role": "assistant",
        "content": "I've written a simple hello world program.",
    }, "finish_reason": "stop"}]}


async def _mock_stream(scenario: str, session_id: str):
    """Generate mock SSE stream."""
    # For simplicity, use non-streaming mock and wrap it
    result = await _mock_non_stream(scenario, session_id)
    chunk = {
        "id": result["id"],
        "object": "chat.completion.chunk",
        "created": result.get("created", int(time.time())),
        "model": "mock-model",
        "choices": [{
            "index": 0,
            "delta": {"content": result["choices"][0]["message"]["content"]},
            "finish_reason": "stop",
        }],
    }
    if "stabilizer" in result:
        chunk["stabilizer"] = result["stabilizer"]
    yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"


# ── Entry point ─────────────────────────────────────────────────

def main():
    import argparse
    global MOCK_MODE, BACKEND_URL, PROXY_PORT

    parser = argparse.ArgumentParser(description="Coding Agent Stabilizer Proxy")
    parser.add_argument("--port", type=int, default=8400, help="Proxy port (default: 8400)")
    parser.add_argument("--backend", default="http://localhost:11434", help="Backend URL")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no backend needed)")
    args = parser.parse_args()

    MOCK_MODE = args.mock
    BACKEND_URL = args.backend
    PROXY_PORT = args.port

    print(f"🛡️  Coding Agent Stabilizer")
    print(f"   Proxy:   http://localhost:{PROXY_PORT}")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   Mock:    {'ON' if MOCK_MODE else 'OFF'}")
    print(f"   Dashboard: http://localhost:{PROXY_PORT}/")
    print()

    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT, log_level="info")


if __name__ == "__main__":
    main()

"""FastAPI proxy server that intercepts OpenAI Chat Completions API calls."""

import os
import json
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from token_counter import analyze_request
from store import store

app = FastAPI(title="LLM Context Debugger")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPSTREAM_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """Intercept, analyze, and forward Chat Completions requests."""
    body_bytes = await request.body()
    body = json.loads(body_bytes.decode("utf-8"))

    # Analyze the request
    analysis = analyze_request(body)
    record = store.add(analysis)

    # Log to console
    print(f"\n{'='*60}")
    print(f"[Call #{record.id}] model={record.model} total={record.total_tokens} tokens")
    for comp, count in record.components.items():
        if count > 0:
            pct = count / record.total_tokens * 100 if record.total_tokens else 0
            print(f"  {comp}: {count} ({pct:.1f}%)")
    for w in record.warnings:
        print(f"  ⚠ WARNING: {w['message']}")
    print(f"{'='*60}")

    # Forward to upstream (or mock if no API key)
    api_key = request.headers.get("authorization", "")
    if not api_key or api_key == "Bearer mock" or "MOCK" in os.environ.get("LLM_DEBUG_MODE", ""):
        # Return mock response
        return JSONResponse({
            "id": f"chatcmpl-debug-{record.id}",
            "object": "chat.completion",
            "model": body.get("model", "gpt-4"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[Mock response] Context debugger captured {record.total_tokens} tokens across {len(record.messages)} messages.",
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": record.total_tokens,
                "completion_tokens": 20,
                "total_tokens": record.total_tokens + 20,
            },
        })

    # Forward to real API
    headers = dict(request.headers)
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    headers.pop("content-length", None)

    async with httpx.AsyncClient(timeout=120.0) as client:
        upstream_url = f"{UPSTREAM_BASE}/v1/chat/completions"
        resp = await client.post(
            upstream_url,
            content=body_bytes,
            headers=headers,
        )

    # Pass through the response
    return StreamingResponse(
        content=iter([resp.content]),
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


# --- Dashboard & API routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    return DASHBOARD_PATH.read_text(encoding="utf-8")


@app.get("/api/calls")
async def list_calls():
    """List all intercepted calls."""
    return store.get_all()


@app.get("/api/calls/{call_id}")
async def get_call(call_id: int):
    """Get details of a specific call."""
    record = store.get(call_id)
    if not record:
        return JSONResponse({"error": "not found"}, status_code=404)
    return record


@app.get("/api/diff/{id_a}/{id_b}")
async def get_diff(id_a: int, id_b: int):
    """Get context diff between two calls."""
    diff = store.get_diff(id_a, id_b)
    if not diff:
        return JSONResponse({"error": "not found"}, status_code=404)
    return diff


@app.post("/api/demo")
async def inject_demo():
    """Inject demo data for testing the dashboard."""
    demos = [
        {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant. You write clean, well-documented Python code. Always explain your reasoning step by step."},
                {"role": "user", "content": "Write a function to calculate fibonacci numbers"},
                {"role": "assistant", "content": "Here's an efficient fibonacci function using memoization:\n\n```python\ndef fib(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 1: return n\n    memo[n] = fib(n-1) + fib(n-2)\n    return memo[n]\n```"},
                {"role": "user", "content": "Now add type hints and make it iterative"},
            ],
            "tools": [
                {"type": "function", "function": {"name": "run_code", "description": "Execute Python code in a sandbox", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}}}}
            ],
        },
        {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant. You write clean, well-documented Python code. Always explain your reasoning step by step."},
                {"role": "user", "content": "Write a function to calculate fibonacci numbers"},
                {"role": "assistant", "content": "Here's an efficient fibonacci function using memoization:\n\n```python\ndef fib(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 1: return n\n    memo[n] = fib(n-1) + fib(n-2)\n    return memo[n]\n```"},
                {"role": "user", "content": "Now add type hints and make it iterative"},
                {"role": "assistant", "content": "```python\ndef fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b\n```"},
                {"role": "user", "content": "Great! Now write comprehensive tests using pytest"},
                {"role": "tool", "content": "Test execution result:\n4 passed, 0 failed\nExecution time: 0.02s", "tool_call_id": "call_123"},
            ],
            "tools": [
                {"type": "function", "function": {"name": "run_code", "description": "Execute Python code in a sandbox", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}}}},
                {"type": "function", "function": {"name": "read_file", "description": "Read contents of a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
            ],
        },
        {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant. You write clean, well-documented Python code. Always explain your reasoning step by step. " + "Additional context: " * 50 + "This is a very long system prompt to simulate context budget issues."},
                {"role": "user", "content": "Hello"},
            ],
        },
    ]

    records = []
    for demo in demos:
        analysis = analyze_request(demo)
        record = store.add(analysis)
        records.append(store._to_dict(record))

    return {"injected": len(records), "records": records}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)

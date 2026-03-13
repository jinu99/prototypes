"""Mock Ollama backend for testing without a real LLM."""

from __future__ import annotations

import json
import time
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Mock Ollama Backend")


@app.get("/api/tags")
async def tags():
    return {"models": [{"name": "mock-model:latest", "size": 4_000_000_000}]}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    is_stream = body.get("stream", False)
    model = body.get("model", "mock-model")

    # Simulate processing time
    await asyncio.sleep(0.1)

    if is_stream:
        return StreamingResponse(
            _stream_response(model),
            media_type="text/event-stream",
        )

    return JSONResponse({
        "id": "mock-chatcmpl-001",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello! I'm a mock LLM response from Serve Guard's test backend.",
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
    })


async def _stream_response(model: str):
    chunks = ["Hello", "!", " I'm", " a", " mock", " streamed", " response", "."]
    for i, token in enumerate(chunks):
        data = {
            "id": "mock-chatcmpl-001",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": token} if i > 0 else {"role": "assistant", "content": token},
                "finish_reason": None if i < len(chunks) - 1 else "stop",
            }],
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.05)
    yield "data: [DONE]\n\n"


@app.post("/v1/completions")
async def completions(request: Request):
    body = await request.json()
    return JSONResponse({
        "id": "mock-cmpl-001",
        "object": "text_completion",
        "created": int(time.time()),
        "model": body.get("model", "mock-model"),
        "choices": [{"text": "Mock completion response.", "index": 0, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    })


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [{
            "id": "mock-model",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "serve-guard-mock",
        }],
    }

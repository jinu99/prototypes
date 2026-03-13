"""OpenAI-compatible reverse proxy with admission control."""

from __future__ import annotations

import json
import logging
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .admission import AdmissionController
from .backends import BackendManager
from .metrics import MetricsStore

logger = logging.getLogger(__name__)


def create_proxy_routes(
    app: FastAPI,
    admission: AdmissionController,
    backend_mgr: BackendManager,
    metrics: MetricsStore,
):
    client = httpx.AsyncClient(timeout=120.0)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        return await _proxy_request(request, "/v1/chat/completions")

    @app.post("/v1/completions")
    async def completions(request: Request):
        return await _proxy_request(request, "/v1/completions")

    @app.get("/v1/models")
    async def list_models(request: Request):
        return await _proxy_request(request, "/v1/models", skip_admission=True)

    async def _proxy_request(
        request: Request, path: str, skip_admission: bool = False,
    ):
        queued_ms = 0.0

        if not skip_admission:
            result = admission.acquire()
            result = await result
            await metrics.record_queue(admission.queue_depth, result.reason)

            if not result.admitted:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "message": f"Request rejected: {result.reason}",
                            "type": "server_error",
                            "code": "vram_admission_denied",
                        }
                    },
                )
            queued_ms = result.wait_time * 1000

        backend = backend_mgr.get_healthy_backend()
        if not backend:
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "message": "No healthy backend available",
                        "type": "server_error",
                        "code": "no_backend",
                    }
                },
            )

        method = request.method.upper()
        body = await request.body()
        req_data = json.loads(body) if body and method == "POST" else {}
        model_name = req_data.get("model", "")
        is_stream = req_data.get("stream", False)

        target_url = backend.config.url.rstrip("/") + path
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding")
        }

        backend.active_requests += 1
        start = time.time()

        try:
            if is_stream:
                return await _handle_stream(
                    client, target_url, headers, body,
                    backend, metrics, queued_ms, model_name, start,
                )
            else:
                return await _handle_normal(
                    client, target_url, headers, body,
                    backend, metrics, queued_ms, model_name, start, method,
                )
        except httpx.ConnectError:
            backend.consecutive_failures += 1
            latency = (time.time() - start) * 1000
            await metrics.record_request(backend.config.name, latency, 502, queued_ms, model_name)
            return JSONResponse(
                status_code=502,
                content={"error": {"message": "Backend connection failed", "type": "server_error"}},
            )
        finally:
            backend.active_requests -= 1

    async def _handle_normal(
        client, url, headers, body, backend, metrics, queued_ms, model, start,
        method: str = "POST",
    ):
        if method == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, content=body, headers=headers)
        latency = (time.time() - start) * 1000
        await metrics.record_request(
            backend.config.name, latency, resp.status_code, queued_ms, model,
        )
        return JSONResponse(
            status_code=resp.status_code,
            content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text},
            headers={"x-serve-guard-backend": backend.config.name},
        )

    async def _handle_stream(
        client, url, headers, body, backend, metrics, queued_ms, model, start,
    ):
        req = client.build_request("POST", url, content=body, headers=headers)
        resp = await client.send(req, stream=True)

        async def generate():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()
                latency = (time.time() - start) * 1000
                await metrics.record_request(
                    backend.config.name, latency, resp.status_code, queued_ms, model,
                )

        return StreamingResponse(
            generate(),
            status_code=resp.status_code,
            media_type="text/event-stream",
            headers={"x-serve-guard-backend": backend.config.name},
        )

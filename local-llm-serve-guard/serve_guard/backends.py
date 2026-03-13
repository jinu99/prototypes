"""Backend manager with health checks and fallback routing."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

import httpx

from .config import BackendConfig

logger = logging.getLogger(__name__)


class BackendState(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class BackendInfo:
    config: BackendConfig
    state: BackendState = BackendState.UNKNOWN
    last_check: float = 0.0
    consecutive_failures: int = 0
    active_requests: int = 0


class BackendManager:
    def __init__(self, configs: list[BackendConfig]):
        self._backends: list[BackendInfo] = [
            BackendInfo(config=c) for c in sorted(configs, key=lambda x: x.priority)
        ]
        self._client = httpx.AsyncClient(timeout=5.0)
        self._tasks: list[asyncio.Task] = []

    @property
    def backends(self) -> list[BackendInfo]:
        return self._backends

    async def start(self):
        for backend in self._backends:
            task = asyncio.create_task(self._healthcheck_loop(backend))
            self._tasks.append(task)

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()

    def get_healthy_backend(self) -> BackendInfo | None:
        """Return the highest-priority healthy backend."""
        for b in self._backends:
            if b.state == BackendState.HEALTHY:
                return b
        return None

    def get_all_status(self) -> list[dict]:
        return [
            {
                "name": b.config.name,
                "url": b.config.url,
                "state": b.state.value,
                "priority": b.config.priority,
                "active_requests": b.active_requests,
                "last_check": b.last_check,
            }
            for b in self._backends
        ]

    async def _healthcheck_loop(self, backend: BackendInfo):
        while True:
            try:
                url = backend.config.url.rstrip("/") + backend.config.healthcheck_path
                resp = await self._client.get(url)
                if resp.status_code < 500:
                    backend.state = BackendState.HEALTHY
                    backend.consecutive_failures = 0
                else:
                    backend.consecutive_failures += 1
                    if backend.consecutive_failures >= 3:
                        backend.state = BackendState.UNHEALTHY
            except Exception:
                backend.consecutive_failures += 1
                if backend.consecutive_failures >= 3:
                    backend.state = BackendState.UNHEALTHY
            backend.last_check = time.time()
            await asyncio.sleep(backend.config.healthcheck_interval_seconds)

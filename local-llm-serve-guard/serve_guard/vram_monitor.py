"""VRAM monitoring via nvidia-smi with mock fallback."""

from __future__ import annotations

import asyncio
import logging
import random
import shutil
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VramStatus:
    used_mb: float
    total_mb: float
    utilization_percent: float
    timestamp: float


class VramMonitor:
    """Polls nvidia-smi for VRAM usage. Falls back to mock if unavailable."""

    def __init__(self, poll_interval: float = 2.0, mock: bool = False):
        self.poll_interval = poll_interval
        self._mock = mock or not shutil.which("nvidia-smi")
        self._latest: VramStatus | None = None
        self._task: asyncio.Task | None = None
        self._callbacks: list = []

        if self._mock:
            logger.info("nvidia-smi not found — using mock VRAM data")

    @property
    def is_mock(self) -> bool:
        return self._mock

    @property
    def latest(self) -> VramStatus | None:
        return self._latest

    def on_update(self, callback):
        self._callbacks.append(callback)

    async def start(self):
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self):
        while True:
            try:
                status = await self._read_vram()
                self._latest = status
                for cb in self._callbacks:
                    try:
                        await cb(status)
                    except Exception:
                        logger.exception("VRAM callback error")
            except Exception:
                logger.exception("VRAM poll error")
            await asyncio.sleep(self.poll_interval)

    async def _read_vram(self) -> VramStatus:
        if self._mock:
            return self._mock_read()
        return await self._nvidia_smi_read()

    def _mock_read(self) -> VramStatus:
        total = 24576.0  # 24GB mock GPU
        # Simulate fluctuating usage between 40-90%
        base = 50 + 30 * (0.5 + 0.5 * random.random())
        used = total * base / 100
        return VramStatus(
            used_mb=round(used, 1),
            total_mb=total,
            utilization_percent=round(used / total * 100, 1),
            timestamp=time.time(),
        )

    async def _nvidia_smi_read(self) -> VramStatus:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        line = stdout.decode().strip().split("\n")[0]
        used_str, total_str = line.split(",")
        used = float(used_str.strip())
        total = float(total_str.strip())
        return VramStatus(
            used_mb=used,
            total_mb=total,
            utilization_percent=round(used / total * 100, 1),
            timestamp=time.time(),
        )

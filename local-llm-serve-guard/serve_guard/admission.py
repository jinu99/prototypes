"""VRAM-based admission controller with queuing."""

from __future__ import annotations

import asyncio
import logging
import time

from .vram_monitor import VramStatus

logger = logging.getLogger(__name__)


class AdmissionResult:
    def __init__(self, admitted: bool, queued: bool = False, wait_time: float = 0,
                 reason: str = ""):
        self.admitted = admitted
        self.queued = queued
        self.wait_time = wait_time
        self.reason = reason


class AdmissionController:
    def __init__(
        self,
        threshold_percent: float = 85.0,
        critical_percent: float = 95.0,
        max_queue_size: int = 50,
        queue_timeout: float = 30.0,
    ):
        self.threshold_percent = threshold_percent
        self.critical_percent = critical_percent
        self.max_queue_size = max_queue_size
        self.queue_timeout = queue_timeout
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._vram_ok = asyncio.Event()
        self._vram_ok.set()  # Start optimistic
        self._current_vram: VramStatus | None = None
        self._stats = {"admitted": 0, "queued": 0, "rejected": 0, "timeout": 0}

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    @property
    def stats(self) -> dict:
        return {**self._stats, "queue_depth": self.queue_depth}

    async def on_vram_update(self, status: VramStatus):
        """Called by VramMonitor when new data arrives."""
        self._current_vram = status
        if status.utilization_percent < self.threshold_percent:
            self._vram_ok.set()
        else:
            self._vram_ok.clear()

    async def acquire(self) -> AdmissionResult:
        """Try to admit a request. May queue or reject."""
        vram = self._current_vram

        # No VRAM data yet — admit optimistically
        if vram is None:
            self._stats["admitted"] += 1
            return AdmissionResult(admitted=True, reason="no_vram_data")

        # Below threshold — admit immediately
        if vram.utilization_percent < self.threshold_percent:
            self._stats["admitted"] += 1
            return AdmissionResult(admitted=True, reason="below_threshold")

        # Critical — reject immediately
        if vram.utilization_percent >= self.critical_percent:
            self._stats["rejected"] += 1
            return AdmissionResult(
                admitted=False,
                reason=f"vram_critical_{vram.utilization_percent:.1f}%",
            )

        # Between threshold and critical — queue
        if self._queue.full():
            self._stats["rejected"] += 1
            return AdmissionResult(admitted=False, reason="queue_full")

        self._stats["queued"] += 1
        start = time.time()
        waiter = asyncio.Event()

        try:
            self._queue.put_nowait(waiter)
        except asyncio.QueueFull:
            self._stats["rejected"] += 1
            return AdmissionResult(admitted=False, reason="queue_full")

        try:
            await asyncio.wait_for(self._vram_ok.wait(), timeout=self.queue_timeout)
            wait_time = time.time() - start
            self._stats["admitted"] += 1
            return AdmissionResult(
                admitted=True, queued=True, wait_time=wait_time, reason="queued_released"
            )
        except asyncio.TimeoutError:
            self._stats["timeout"] += 1
            return AdmissionResult(
                admitted=False, queued=True,
                wait_time=self.queue_timeout, reason="queue_timeout",
            )
        finally:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

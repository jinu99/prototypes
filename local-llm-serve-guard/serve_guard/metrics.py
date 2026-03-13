"""SQLite metrics storage for VRAM, latency, and queue depth."""

from __future__ import annotations

import time

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS vram_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    used_mb REAL NOT NULL,
    total_mb REAL NOT NULL,
    utilization_percent REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS request_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    backend TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    status_code INTEGER NOT NULL,
    queued_ms REAL DEFAULT 0,
    model TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS queue_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    queue_depth INTEGER NOT NULL,
    action TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vram_ts ON vram_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_req_ts ON request_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_queue_ts ON queue_metrics(timestamp);
"""


class MetricsStore:
    def __init__(self, db_path: str = "metrics.db", retention_hours: int = 24):
        self.db_path = db_path
        self.retention_hours = retention_hours
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    async def record_vram(self, used_mb: float, total_mb: float, util_pct: float):
        await self._db.execute(
            "INSERT INTO vram_metrics (timestamp, used_mb, total_mb, utilization_percent) VALUES (?, ?, ?, ?)",
            (time.time(), used_mb, total_mb, util_pct),
        )
        await self._db.commit()

    async def record_request(
        self, backend: str, latency_ms: float, status_code: int,
        queued_ms: float = 0, model: str = "",
    ):
        await self._db.execute(
            "INSERT INTO request_metrics (timestamp, backend, latency_ms, status_code, queued_ms, model) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), backend, latency_ms, status_code, queued_ms, model),
        )
        await self._db.commit()

    async def record_queue(self, queue_depth: int, action: str):
        await self._db.execute(
            "INSERT INTO queue_metrics (timestamp, queue_depth, action) VALUES (?, ?, ?)",
            (time.time(), queue_depth, action),
        )
        await self._db.commit()

    async def cleanup_old(self):
        cutoff = time.time() - self.retention_hours * 3600
        for table in ("vram_metrics", "request_metrics", "queue_metrics"):
            await self._db.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))
        await self._db.commit()

    async def get_recent_vram(self, limit: int = 60) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT timestamp, used_mb, total_mb, utilization_percent FROM vram_metrics ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {"timestamp": r[0], "used_mb": r[1], "total_mb": r[2], "utilization_percent": r[3]}
            for r in reversed(rows)
        ]

    async def get_recent_requests(self, limit: int = 100) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT timestamp, backend, latency_ms, status_code, queued_ms, model FROM request_metrics ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {"timestamp": r[0], "backend": r[1], "latency_ms": r[2],
             "status_code": r[3], "queued_ms": r[4], "model": r[5]}
            for r in reversed(rows)
        ]

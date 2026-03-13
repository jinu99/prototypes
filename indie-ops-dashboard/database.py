"""SQLite database setup and query helpers."""

import aiosqlite

DB_PATH = "metrics.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_percent REAL NOT NULL,
                net_sent_bytes INTEGER NOT NULL,
                net_recv_bytes INTEGER NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS uptime_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                response_ms REAL,
                error TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cron_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                job_name TEXT NOT NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_uptime_ts ON uptime_checks(ts)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_heartbeat_ts ON cron_heartbeats(ts)"
        )
        await db.commit()


async def insert_metric(ts, cpu, mem, net_sent, net_recv):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO metrics (ts, cpu_percent, memory_percent, net_sent_bytes, net_recv_bytes) VALUES (?, ?, ?, ?, ?)",
            (ts, cpu, mem, net_sent, net_recv),
        )
        await db.commit()


async def get_metrics(since_ts: float):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ts, cpu_percent, memory_percent, net_sent_bytes, net_recv_bytes FROM metrics WHERE ts >= ? ORDER BY ts",
            (since_ts,),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def insert_uptime_check(ts, url, status, response_ms, error):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO uptime_checks (ts, url, status, response_ms, error) VALUES (?, ?, ?, ?, ?)",
            (ts, url, status, response_ms, error),
        )
        await db.commit()


async def get_uptime_checks(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ts, url, status, response_ms, error FROM uptime_checks ORDER BY ts DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def insert_heartbeat(ts, job_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cron_heartbeats (ts, job_name) VALUES (?, ?)",
            (ts, job_name),
        )
        await db.commit()


async def get_heartbeats():
    """Get the latest heartbeat per job."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT job_name, MAX(ts) as last_ts, COUNT(*) as total_beats
            FROM cron_heartbeats GROUP BY job_name ORDER BY last_ts DESC
        """)
        return [dict(row) for row in await cursor.fetchall()]

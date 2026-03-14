"""SQLite session logging for tool calls and block events."""

import aiosqlite
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "stabilizer.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT,
    blocked INTEGER NOT NULL DEFAULT 0,
    block_reason TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def create_session(session_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sessions (id, started_at, status) VALUES (?, ?, ?)",
            (session_id, time.time(), "active"),
        )
        await db.commit()


async def end_session(session_id: str, status: str = "completed"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET status = ? WHERE id = ?",
            (status, session_id),
        )
        await db.commit()


async def log_tool_call(
    session_id: str,
    tool_name: str,
    arguments: dict | None = None,
    blocked: bool = False,
    block_reason: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tool_calls (session_id, timestamp, tool_name, arguments, blocked, block_reason) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                time.time(),
                tool_name,
                json.dumps(arguments) if arguments else None,
                1 if blocked else 0,
                block_reason,
            ),
        )
        await db.commit()


async def get_sessions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT s.*, "
            "(SELECT COUNT(*) FROM tool_calls t WHERE t.session_id = s.id) as total_calls, "
            "(SELECT COUNT(*) FROM tool_calls t WHERE t.session_id = s.id AND t.blocked = 1) as blocked_calls "
            "FROM sessions s ORDER BY s.started_at DESC LIMIT 50"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_tool_calls(session_id: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if session_id:
            cursor = await db.execute(
                "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY timestamp DESC LIMIT 100",
                (session_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tool_calls ORDER BY timestamp DESC LIMIT 100"
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_blocked_events(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tool_calls WHERE blocked = 1 ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

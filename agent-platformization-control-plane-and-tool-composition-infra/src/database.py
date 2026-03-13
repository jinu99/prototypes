"""SQLite database setup and lifecycle management."""

import aiosqlite
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "control_plane.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    parameters TEXT NOT NULL DEFAULT '{}',
    category TEXT NOT NULL DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    tool_ids TEXT NOT NULL DEFAULT '[]',
    permissions TEXT NOT NULL DEFAULT '[]',
    llm_config TEXT NOT NULL DEFAULT '{}',
    system_prompt TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_instances (
    id TEXT PRIMARY KEY,
    definition_id TEXT NOT NULL REFERENCES agent_definitions(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    config_override TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL REFERENCES agent_instances(id),
    input_message TEXT NOT NULL,
    output_message TEXT NOT NULL DEFAULT '',
    tools_used TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await _seed_default_tools(db)
        await db.commit()
    finally:
        await db.close()


async def _seed_default_tools(db: aiosqlite.Connection):
    """Seed mock tools if the tools table is empty."""
    cursor = await db.execute("SELECT COUNT(*) FROM tools")
    row = await cursor.fetchone()
    if row[0] > 0:
        return

    tools = [
        {
            "id": "tool-search",
            "name": "Search",
            "description": "웹 검색을 수행하여 정보를 찾습니다",
            "parameters": json.dumps({"query": "string"}),
            "category": "information",
        },
        {
            "id": "tool-memory",
            "name": "Memory",
            "description": "장기 메모리에 정보를 저장하고 검색합니다",
            "parameters": json.dumps({"action": "read|write", "key": "string", "value": "string?"}),
            "category": "storage",
        },
        {
            "id": "tool-slack",
            "name": "Slack",
            "description": "Slack 채널에 메시지를 전송합니다",
            "parameters": json.dumps({"channel": "string", "message": "string"}),
            "category": "notification",
        },
        {
            "id": "tool-email",
            "name": "Email",
            "description": "이메일을 발송합니다",
            "parameters": json.dumps({"to": "string", "subject": "string", "body": "string"}),
            "category": "notification",
        },
        {
            "id": "tool-orchestrator",
            "name": "Orchestrator",
            "description": "다른 에이전트에게 작업을 위임합니다",
            "parameters": json.dumps({"target_agent": "string", "task": "string"}),
            "category": "orchestration",
        },
        {
            "id": "tool-code-exec",
            "name": "CodeExec",
            "description": "Python 코드를 실행하고 결과를 반환합니다",
            "parameters": json.dumps({"code": "string"}),
            "category": "execution",
        },
    ]

    for t in tools:
        await db.execute(
            "INSERT INTO tools (id, name, description, parameters, category) VALUES (?, ?, ?, ?, ?)",
            (t["id"], t["name"], t["description"], t["parameters"], t["category"]),
        )

"""Agent definition CRUD routes."""

import json
import uuid
from fastapi import APIRouter, HTTPException
from src.database import get_db
from src.models import AgentDefinitionCreate, AgentDefinitionUpdate, AgentDefinitionOut

router = APIRouter(prefix="/api/agents", tags=["agent-definitions"])


@router.get("", response_model=list[AgentDefinitionOut])
async def list_agent_definitions():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agent_definitions ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_def(r) for r in rows]
    finally:
        await db.close()


@router.post("", response_model=AgentDefinitionOut, status_code=201)
async def create_agent_definition(body: AgentDefinitionCreate):
    db = await get_db()
    try:
        # Validate tool_ids exist
        if body.tool_ids:
            placeholders = ",".join("?" for _ in body.tool_ids)
            cursor = await db.execute(
                f"SELECT id FROM tools WHERE id IN ({placeholders})", body.tool_ids
            )
            found = {r["id"] for r in await cursor.fetchall()}
            missing = set(body.tool_ids) - found
            if missing:
                raise HTTPException(400, f"Unknown tool IDs: {missing}")

        agent_id = f"def-{uuid.uuid4().hex[:8]}"
        await db.execute(
            """INSERT INTO agent_definitions (id, name, description, tool_ids, permissions, llm_config, system_prompt)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, body.name, body.description,
             json.dumps(body.tool_ids), json.dumps(body.permissions),
             json.dumps(body.llm_config), body.system_prompt),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM agent_definitions WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        return _row_to_def(row)
    finally:
        await db.close()


@router.get("/{agent_id}", response_model=AgentDefinitionOut)
async def get_agent_definition(agent_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agent_definitions WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Agent definition '{agent_id}' not found")
        return _row_to_def(row)
    finally:
        await db.close()


@router.patch("/{agent_id}", response_model=AgentDefinitionOut)
async def update_agent_definition(agent_id: str, body: AgentDefinitionUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agent_definitions WHERE id = ?", (agent_id,))
        existing = await cursor.fetchone()
        if not existing:
            raise HTTPException(404, f"Agent definition '{agent_id}' not found")

        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.description is not None:
            updates["description"] = body.description
        if body.tool_ids is not None:
            updates["tool_ids"] = json.dumps(body.tool_ids)
        if body.permissions is not None:
            updates["permissions"] = json.dumps(body.permissions)
        if body.llm_config is not None:
            updates["llm_config"] = json.dumps(body.llm_config)
        if body.system_prompt is not None:
            updates["system_prompt"] = body.system_prompt

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            await db.execute(
                f"UPDATE agent_definitions SET {set_clause} WHERE id = ?",
                (*updates.values(), agent_id),
            )
            await db.commit()

        cursor = await db.execute("SELECT * FROM agent_definitions WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        return _row_to_def(row)
    finally:
        await db.close()


@router.delete("/{agent_id}", status_code=204)
async def delete_agent_definition(agent_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM agent_definitions WHERE id = ?", (agent_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, f"Agent definition '{agent_id}' not found")

        # Check for active instances
        cursor = await db.execute(
            "SELECT COUNT(*) FROM agent_instances WHERE definition_id = ? AND status != 'stopped'",
            (agent_id,),
        )
        count = (await cursor.fetchone())[0]
        if count > 0:
            raise HTTPException(409, f"Cannot delete: {count} active instance(s) exist")

        await db.execute("DELETE FROM agent_definitions WHERE id = ?", (agent_id,))
        await db.commit()
    finally:
        await db.close()


def _row_to_def(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "tool_ids": json.loads(row["tool_ids"]),
        "permissions": json.loads(row["permissions"]),
        "llm_config": json.loads(row["llm_config"]),
        "system_prompt": row["system_prompt"],
        "created_at": row["created_at"],
    }

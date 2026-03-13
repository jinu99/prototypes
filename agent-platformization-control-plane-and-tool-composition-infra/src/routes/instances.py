"""Agent instance CRUD + execution routes."""

import json
import uuid
from fastapi import APIRouter, HTTPException
from src.database import get_db
from src.models import (
    InstanceCreate, InstanceUpdate, InstanceOut,
    ExecuteRequest, ExecutionLogOut,
)
from src.runtime import execute_agent

router = APIRouter(prefix="/api/instances", tags=["instances"])


@router.get("", response_model=list[InstanceOut])
async def list_instances(status: str | None = None):
    db = await get_db()
    try:
        query = """
            SELECT i.*, d.name as definition_name,
                   COALESCE(s.total, 0) as total_executions,
                   COALESCE(s.errors, 0) as error_count
            FROM agent_instances i
            JOIN agent_definitions d ON i.definition_id = d.id
            LEFT JOIN (
                SELECT instance_id, COUNT(*) as total,
                       SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors
                FROM execution_logs GROUP BY instance_id
            ) s ON s.instance_id = i.id
        """
        params = []
        if status:
            query += " WHERE i.status = ?"
            params.append(status)
        query += " ORDER BY i.updated_at DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_instance(r) for r in rows]
    finally:
        await db.close()


@router.post("", response_model=InstanceOut, status_code=201)
async def create_instance(body: InstanceCreate):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name FROM agent_definitions WHERE id = ?", (body.definition_id,)
        )
        defn = await cursor.fetchone()
        if not defn:
            raise HTTPException(400, f"Agent definition '{body.definition_id}' not found")

        instance_id = f"inst-{uuid.uuid4().hex[:8]}"
        await db.execute(
            """INSERT INTO agent_instances (id, definition_id, name, status, config_override)
               VALUES (?, ?, ?, 'running', ?)""",
            (instance_id, body.definition_id, body.name, json.dumps(body.config_override)),
        )
        await db.commit()

        cursor = await db.execute(
            """SELECT i.*, d.name as definition_name, 0 as total_executions, 0 as error_count
               FROM agent_instances i JOIN agent_definitions d ON i.definition_id = d.id
               WHERE i.id = ?""",
            (instance_id,),
        )
        row = await cursor.fetchone()
        return _row_to_instance(row)
    finally:
        await db.close()


@router.get("/{instance_id}", response_model=InstanceOut)
async def get_instance(instance_id: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT i.*, d.name as definition_name,
                      COALESCE(s.total, 0) as total_executions,
                      COALESCE(s.errors, 0) as error_count
               FROM agent_instances i
               JOIN agent_definitions d ON i.definition_id = d.id
               LEFT JOIN (
                   SELECT instance_id, COUNT(*) as total,
                          SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors
                   FROM execution_logs GROUP BY instance_id
               ) s ON s.instance_id = i.id
               WHERE i.id = ?""",
            (instance_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Instance '{instance_id}' not found")
        return _row_to_instance(row)
    finally:
        await db.close()


@router.patch("/{instance_id}", response_model=InstanceOut)
async def update_instance(instance_id: str, body: InstanceUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM agent_instances WHERE id = ?", (instance_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, f"Instance '{instance_id}' not found")

        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.status is not None:
            updates["status"] = body.status
        if body.config_override is not None:
            updates["config_override"] = json.dumps(body.config_override)

        if updates:
            updates["updated_at"] = "datetime('now')"
            set_parts = []
            values = []
            for k, v in updates.items():
                if k == "updated_at":
                    set_parts.append(f"{k} = datetime('now')")
                else:
                    set_parts.append(f"{k} = ?")
                    values.append(v)
            await db.execute(
                f"UPDATE agent_instances SET {', '.join(set_parts)} WHERE id = ?",
                (*values, instance_id),
            )
            await db.commit()

        return await get_instance(instance_id)
    finally:
        await db.close()


@router.delete("/{instance_id}", status_code=204)
async def delete_instance(instance_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM agent_instances WHERE id = ?", (instance_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, f"Instance '{instance_id}' not found")

        await db.execute("DELETE FROM execution_logs WHERE instance_id = ?", (instance_id,))
        await db.execute("DELETE FROM agent_instances WHERE id = ?", (instance_id,))
        await db.commit()
    finally:
        await db.close()


@router.post("/{instance_id}/execute", response_model=ExecutionLogOut)
async def execute_instance(instance_id: str, body: ExecuteRequest):
    db = await get_db()
    try:
        # Load instance + definition
        cursor = await db.execute(
            """SELECT i.*, d.tool_ids, d.permissions, d.llm_config, d.system_prompt
               FROM agent_instances i
               JOIN agent_definitions d ON i.definition_id = d.id
               WHERE i.id = ?""",
            (instance_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Instance '{instance_id}' not found")
        if row["status"] != "running":
            raise HTTPException(409, f"Instance is '{row['status']}', must be 'running' to execute")

        tool_ids = json.loads(row["tool_ids"])
        # Resolve tool names from IDs
        tool_names = []
        if tool_ids:
            placeholders = ",".join("?" for _ in tool_ids)
            cursor = await db.execute(
                f"SELECT name FROM tools WHERE id IN ({placeholders})", tool_ids
            )
            tool_names = [r["name"] for r in await cursor.fetchall()]

        # Execute via mock runtime
        result = execute_agent(
            system_prompt=row["system_prompt"],
            tool_names=tool_names,
            permissions=json.loads(row["permissions"]),
            llm_config=json.loads(row["llm_config"]),
            user_message=body.message,
        )

        # Log execution
        log_id = f"log-{uuid.uuid4().hex[:8]}"
        await db.execute(
            """INSERT INTO execution_logs
               (id, instance_id, input_message, output_message, tools_used, status, error_message, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, instance_id, body.message, result["output"],
             json.dumps(result["tools_used"]), result["status"],
             result["error_message"], result["duration_ms"]),
        )
        await db.execute(
            "UPDATE agent_instances SET updated_at = datetime('now') WHERE id = ?",
            (instance_id,),
        )
        await db.commit()

        return {
            "id": log_id,
            "instance_id": instance_id,
            "input_message": body.message,
            "output_message": result["output"],
            "tools_used": result["tools_used"],
            "status": result["status"],
            "error_message": result["error_message"],
            "duration_ms": result["duration_ms"],
            "created_at": "",
        }
    finally:
        await db.close()


@router.get("/{instance_id}/logs", response_model=list[ExecutionLogOut])
async def list_execution_logs(instance_id: str, limit: int = 50):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM execution_logs WHERE instance_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (instance_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "instance_id": r["instance_id"],
                "input_message": r["input_message"],
                "output_message": r["output_message"],
                "tools_used": json.loads(r["tools_used"]),
                "status": r["status"],
                "error_message": r["error_message"],
                "duration_ms": r["duration_ms"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        await db.close()


def _row_to_instance(row) -> dict:
    return {
        "id": row["id"],
        "definition_id": row["definition_id"],
        "definition_name": row["definition_name"],
        "name": row["name"],
        "status": row["status"],
        "config_override": json.loads(row["config_override"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "total_executions": row["total_executions"],
        "error_count": row["error_count"],
    }

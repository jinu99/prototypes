"""Tool registry API routes."""

import json
from fastapi import APIRouter, HTTPException
from src.database import get_db
from src.models import ToolOut

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=list[ToolOut])
async def list_tools():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM tools ORDER BY category, name")
        rows = await cursor.fetchall()
        return [_row_to_tool(r) for r in rows]
    finally:
        await db.close()


@router.get("/{tool_id}", response_model=ToolOut)
async def get_tool(tool_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Tool '{tool_id}' not found")
        return _row_to_tool(row)
    finally:
        await db.close()


def _row_to_tool(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "parameters": json.loads(row["parameters"]),
        "category": row["category"],
        "created_at": row["created_at"],
    }

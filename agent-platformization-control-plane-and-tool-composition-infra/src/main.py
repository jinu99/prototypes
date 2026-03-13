"""Agent Control Plane — FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.database import init_db
from src.routes import tools, agents, instances

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Agent Control Plane",
    description="Tool 조합 기반 에이전트 관리 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(tools.router)
app.include_router(agents.router)
app.include_router(instances.router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(str(STATIC_DIR / "dashboard.html"))


@app.get("/api/stats")
async def get_stats():
    """Dashboard summary stats."""
    from src.database import get_db
    db = await get_db()
    try:
        stats = {}
        cursor = await db.execute("SELECT COUNT(*) FROM agent_definitions")
        stats["total_definitions"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM agent_instances")
        stats["total_instances"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM agent_instances WHERE status='running'")
        stats["running_instances"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM execution_logs")
        stats["total_executions"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM execution_logs WHERE status='error'")
        stats["total_errors"] = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM tools")
        stats["total_tools"] = (await cursor.fetchone())[0]

        return stats
    finally:
        await db.close()

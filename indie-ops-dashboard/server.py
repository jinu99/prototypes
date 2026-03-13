"""FastAPI server for the Indie Ops Dashboard."""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from analyzer import classify_metrics, compute_cost_comparison
from collector import run_collector
from database import (
    get_heartbeats,
    get_metrics,
    get_uptime_checks,
    init_db,
    insert_heartbeat,
)
from seed_data import seed_if_empty
from uptime import run_uptime_checks


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    seeded = await seed_if_empty()
    if seeded:
        print("[server] Demo data seeded for 36h")
    task = asyncio.create_task(run_collector())
    print("[server] Metric collector started (30s interval)")
    yield
    task.cancel()


app = FastAPI(title="Indie Ops Dashboard", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/metrics")
async def api_metrics(hours: float = 24):
    """Get raw metrics for the last N hours."""
    since = time.time() - hours * 3600
    metrics = await get_metrics(since)
    return JSONResponse({"metrics": metrics, "count": len(metrics)})


@app.get("/api/analysis")
async def api_analysis(hours: float = 24):
    """Get pattern analysis and cost comparison."""
    since = time.time() - hours * 3600
    metrics = await get_metrics(since)
    classification = classify_metrics(metrics)
    cost = compute_cost_comparison(classification["daily_hours"])
    return JSONResponse({
        "classification": {
            "segments": classification["segments"],
            "daily_hours": classification["daily_hours"],
            "total_active_pct": classification["total_active_pct"],
        },
        "cost_comparison": cost,
    })


@app.get("/api/uptime")
async def api_uptime():
    """Get recent uptime check results."""
    checks = await get_uptime_checks(limit=50)
    return JSONResponse({"checks": checks})


@app.post("/api/uptime/check")
async def api_run_uptime_check():
    """Trigger an uptime check now."""
    results = await run_uptime_checks()
    return JSONResponse({"results": results})


@app.get("/api/heartbeats")
async def api_heartbeats():
    """Get cron heartbeat summary."""
    beats = await get_heartbeats()
    return JSONResponse({"heartbeats": beats})


@app.post("/api/heartbeat/{job_name}")
async def api_receive_heartbeat(job_name: str):
    """Receive a cron heartbeat ping."""
    await insert_heartbeat(time.time(), job_name)
    return JSONResponse({"status": "ok", "job": job_name, "ts": time.time()})


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

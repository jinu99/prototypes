"""FastAPI server: REST API + SSE for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from graph import DependencyGraph, Status
from feed import fetch_feed, fetch_feed_mock, FeedResult
from db import get_connection, init_db, record_event, get_recent_events

logger = logging.getLogger(__name__)

# --- Global state ---
graph = DependencyGraph()
db_conn = None
sse_subscribers: list[asyncio.Queue] = []
GRAPH_PATH = Path(__file__).parent / "example_graph.yaml"
USE_MOCK_FEEDS = True  # Toggle for real vs mock feeds
POLL_INTERVAL = 60  # seconds between feed polls


def broadcast(event_type: str, data: dict) -> None:
    """Send event to all SSE subscribers."""
    msg = json.dumps({"type": event_type, **data})
    for q in sse_subscribers:
        q.put_nowait(msg)


async def poll_feeds() -> None:
    """Periodically poll RSS feeds and update statuses."""
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            for svc in graph.services.values():
                if svc.status_feed or USE_MOCK_FEEDS:
                    if USE_MOCK_FEEDS:
                        result = fetch_feed_mock(svc.id)
                    else:
                        result = await asyncio.to_thread(
                            fetch_feed, svc.id, svc.status_feed
                        )
                    _apply_feed_result(result)
        except Exception:
            logger.exception("Feed poll error")


def _apply_feed_result(result: FeedResult) -> None:
    """Apply feed result to graph and record in DB."""
    svc = graph.services.get(result.service_id)
    if not svc:
        return

    old_status = svc.status
    if result.status == old_status:
        return

    cascade = graph.set_status(result.service_id, result.status)

    record_event(
        db_conn, result.service_id,
        old_status.value, result.status.value, "feed",
    )
    for sid, st in cascade.affected.items():
        if sid != result.service_id:
            record_event(
                db_conn, sid,
                old_status.value, st.value, "cascade",
                cascade_from=result.service_id,
            )

    broadcast("status_update", {
        "graph": graph.to_dict(),
        "cascade": {
            "origin": result.service_id,
            "affected": {k: v.value for k, v in cascade.affected.items()},
        },
    })


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_conn
    db_conn = get_connection()
    init_db(db_conn)
    graph.load_yaml(GRAPH_PATH)

    poll_task = asyncio.create_task(poll_feeds())
    yield
    poll_task.cancel()
    db_conn.close()


app = FastAPI(title="Stack Cascade Predictor", lifespan=lifespan)


# --- SSE endpoint ---

@app.get("/api/events")
async def sse_events(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    sse_subscribers.append(queue)

    async def stream():
        try:
            # Send initial state
            yield f"data: {json.dumps({'type': 'init', 'graph': graph.to_dict()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            sse_subscribers.remove(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


# --- REST API ---

@app.get("/api/graph")
async def get_graph():
    return graph.to_dict()


@app.post("/api/simulate")
async def simulate_failure(body: dict):
    """Inject a simulated failure. Body: {service_id, status}"""
    service_id = body["service_id"]
    status = Status(body["status"])
    svc = graph.services[service_id]
    old_status = svc.status

    cascade = graph.set_status(service_id, status)

    record_event(
        db_conn, service_id,
        old_status.value, status.value, "simulation",
    )
    for sid, st in cascade.affected.items():
        if sid != service_id:
            old = graph.services[sid].status.value
            record_event(
                db_conn, sid,
                old, st.value, "cascade",
                cascade_from=service_id,
            )

    broadcast("status_update", {
        "graph": graph.to_dict(),
        "cascade": {
            "origin": service_id,
            "affected": {k: v.value for k, v in cascade.affected.items()},
        },
    })

    return {
        "ok": True,
        "affected": {k: v.value for k, v in cascade.affected.items()},
        "paths": {k: v for k, v in cascade.path.items()},
    }


@app.post("/api/reset")
async def reset_all():
    """Reset all services to operational."""
    graph.clear_all()
    broadcast("status_update", {
        "graph": graph.to_dict(),
        "cascade": {"origin": "reset", "affected": {}},
    })
    return {"ok": True}


@app.get("/api/history")
async def get_history(limit: int = 50):
    return get_recent_events(db_conn, limit)


@app.post("/api/poll-now")
async def poll_now():
    """Trigger an immediate feed poll."""
    results = []
    for svc in graph.services.values():
        if svc.status_feed or USE_MOCK_FEEDS:
            if USE_MOCK_FEEDS:
                result = fetch_feed_mock(svc.id)
            else:
                result = await asyncio.to_thread(
                    fetch_feed, svc.id, svc.status_feed
                )
            _apply_feed_result(result)
            results.append({
                "service_id": result.service_id,
                "status": result.status.value,
                "title": result.latest_title,
                "error": result.error,
            })
    return {"results": results}


# --- Serve static HTML ---

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8099, reload=True)

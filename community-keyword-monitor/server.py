"""FastAPI server — API endpoints + static file serving."""

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from db import (
    init_db, seed_defaults, get_matches, get_config,
    add_config, remove_config,
)
from reddit_collector import collect_reddit
from rss_collector import collect_rss

app = FastAPI(title="Community Keyword Monitor")

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def startup():
    init_db()
    seed_defaults()


# ── Dashboard ──────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ── Timeline API ───────────────────────────────────────

@app.get("/api/matches")
def api_matches(
    source: str | None = Query(None),
    min_score: int = Query(0),
    keyword: str | None = Query(None),
    limit: int = Query(100),
):
    return get_matches(source_type=source, min_score=min_score,
                       keyword=keyword, limit=limit)


# ── Collection triggers ───────────────────────────────

@app.post("/api/collect/reddit")
def api_collect_reddit():
    return collect_reddit()


@app.post("/api/collect/rss")
def api_collect_rss():
    return collect_rss()


@app.post("/api/collect/all")
def api_collect_all():
    reddit = collect_reddit()
    rss = collect_rss()
    return {"reddit": reddit, "rss": rss}


# ── Config management ─────────────────────────────────

@app.get("/api/config")
def api_get_config():
    return {
        "keywords": get_config("keyword"),
        "subreddits": get_config("subreddit"),
        "rss_feeds": get_config("rss_feed"),
    }


@app.post("/api/config/{key}")
def api_add_config(key: str, value: str = Query(...)):
    valid_keys = {"keyword", "subreddit", "rss_feed"}
    if key not in valid_keys:
        return JSONResponse({"error": f"Invalid key. Use: {valid_keys}"}, 400)
    add_config(key, value)
    return {"status": "added", "key": key, "value": value}


@app.delete("/api/config/{key}")
def api_remove_config(key: str, value: str = Query(...)):
    valid_keys = {"keyword", "subreddit", "rss_feed"}
    if key not in valid_keys:
        return JSONResponse({"error": f"Invalid key. Use: {valid_keys}"}, 400)
    remove_config(key, value)
    return {"status": "removed", "key": key, "value": value}


# ── Static files (CSS etc.) ───────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

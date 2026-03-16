"""FastAPI server for Local Feed Relevance Engine."""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

import database as db
from embedder import (
    build_interest_vector,
    compute_scores,
    update_interest_vector_ema,
)
from feed_parser import import_opml_and_fetch

app = FastAPI(title="Local Feed Relevance Engine")

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/opml")
async def upload_opml(file: UploadFile = File(...)):
    """Upload OPML file → parse feeds → fetch articles → compute scores."""
    content = await file.read()
    opml_text = content.decode("utf-8")

    result = import_opml_and_fetch(opml_text)

    # Recompute scores if interest vector exists
    profile = db.get_interest_profile()
    if profile["vector"]:
        _recompute_scores(profile["vector"])

    return result


class KeywordsRequest(BaseModel):
    keywords: list[str]


@app.post("/api/keywords")
def set_keywords(req: KeywordsRequest):
    """Set interest keywords → build interest vector → score all articles."""
    if not req.keywords or len(req.keywords) < 1:
        raise HTTPException(400, "At least 1 keyword required")

    vector = build_interest_vector(req.keywords)
    db.update_interest_profile(keywords=req.keywords, vector=vector, feedback_count=0)

    score_count = _recompute_scores(vector)

    return {
        "keywords": req.keywords,
        "articles_scored": score_count,
    }


@app.get("/api/articles")
def list_articles(limit: int = 100, offset: int = 0):
    """List articles sorted by relevance score."""
    articles = db.get_articles(limit=limit, offset=offset)
    total = db.get_article_count()
    profile = db.get_interest_profile()
    return {
        "articles": articles,
        "total": total,
        "keywords": profile["keywords"],
        "feedback_count": profile["feedback_count"],
        "has_interest_vector": profile["vector"] is not None,
    }


class FeedbackRequest(BaseModel):
    article_id: int
    feedback: str  # "read" or "skip"


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    """Submit read/skip feedback → update interest vector → recompute scores."""
    if req.feedback not in ("read", "skip"):
        raise HTTPException(400, "Feedback must be 'read' or 'skip'")

    # Get article embedding
    article_emb = db.get_article_embedding(req.article_id)
    if not article_emb:
        raise HTTPException(404, "Article not found or has no embedding")

    # Get current profile
    profile = db.get_interest_profile()
    if not profile["vector"]:
        raise HTTPException(400, "Set interest keywords first")

    # Update interest vector with EMA
    new_vector = update_interest_vector_ema(
        profile["vector"], article_emb, req.feedback
    )
    new_count = profile["feedback_count"] + 1
    db.update_interest_profile(vector=new_vector, feedback_count=new_count)

    # Record feedback on article
    db.set_feedback(req.article_id, req.feedback)

    # Recompute all scores
    score_count = _recompute_scores(new_vector)

    return {
        "feedback": req.feedback,
        "article_id": req.article_id,
        "feedback_count": new_count,
        "articles_rescored": score_count,
    }


@app.get("/api/profile")
def get_profile():
    """Get current interest profile."""
    return db.get_interest_profile()


@app.get("/api/stats")
def get_stats():
    """Get basic stats."""
    conn = db.get_conn()
    article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    feed_count = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
    feedback_count = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE feedback IS NOT NULL"
    ).fetchone()[0]
    avg_score = conn.execute(
        "SELECT AVG(relevance_score) FROM articles WHERE relevance_score > 0"
    ).fetchone()[0]
    conn.close()
    return {
        "feeds": feed_count,
        "articles": article_count,
        "feedbacks": feedback_count,
        "avg_score": round(avg_score, 1) if avg_score else 0,
    }


def _recompute_scores(interest_vector: list[float]) -> int:
    """Recompute relevance scores for all articles."""
    article_embs = db.get_article_embeddings()
    if not article_embs:
        return 0
    scores = compute_scores(article_embs, interest_vector)
    db.update_scores(scores)
    return len(scores)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

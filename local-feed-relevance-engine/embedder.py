"""Embedding and scoring engine using sentence-transformers."""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, return list of float vectors."""
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


def embed_single(text: str) -> list[float]:
    return embed_texts([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two normalized vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    # Vectors are already normalized from sentence-transformers
    return float(dot)


def compute_scores(
    article_embeddings: list[tuple[int, list[float]]],
    interest_vector: list[float],
) -> dict[int, float]:
    """Compute relevance scores (0-100) for articles against interest vector."""
    if not article_embeddings or interest_vector is None:
        return {}

    interest = np.array(interest_vector)
    scores = {}
    for article_id, emb in article_embeddings:
        sim = float(np.dot(np.array(emb), interest))
        # Map from [-1, 1] to [0, 100]
        score = round(max(0, min(100, (sim + 1) * 50)), 1)
        scores[article_id] = score
    return scores


def build_interest_vector(keywords: list[str]) -> list[float]:
    """Build initial interest vector from keywords by averaging their embeddings."""
    if not keywords:
        return [0.0] * EMBED_DIM
    embeddings = embed_texts(keywords)
    avg = np.mean(embeddings, axis=0)
    # Normalize
    norm = np.linalg.norm(avg)
    if norm > 0:
        avg = avg / norm
    return avg.tolist()


def update_interest_vector_ema(
    current_vector: list[float],
    article_embedding: list[float],
    feedback: str,
    alpha: float = 0.15,
) -> list[float]:
    """Update interest vector using EMA based on feedback.

    'read' → move toward the article embedding
    'skip' → move away from it
    """
    current = np.array(current_vector)
    article = np.array(article_embedding)

    if feedback == "read":
        updated = (1 - alpha) * current + alpha * article
    else:  # skip
        updated = (1 - alpha) * current - (alpha * 0.5) * article

    # Re-normalize
    norm = np.linalg.norm(updated)
    if norm > 0:
        updated = updated / norm
    return updated.tolist()

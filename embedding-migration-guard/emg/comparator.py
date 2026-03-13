"""Vector space comparison and recall@k measurement."""
from __future__ import annotations

import numpy as np
from numpy.linalg import norm


def cosine_similarity_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Compute pairwise cosine similarity between rows of A and B. Assumes L2-normalized inputs."""
    return A @ B.T


def pairwise_cosine_similarities(old_emb: np.ndarray, new_emb: np.ndarray) -> np.ndarray:
    """Cosine similarity between corresponding document pairs (old[i] vs new[i])."""
    # dot product of normalized vectors = cosine similarity
    return np.sum(old_emb * new_emb, axis=1)


def cosine_distribution_stats(similarities: np.ndarray) -> dict:
    """Compute statistics of a cosine similarity distribution."""
    return {
        "mean": float(np.mean(similarities)),
        "std": float(np.std(similarities)),
        "min": float(np.min(similarities)),
        "max": float(np.max(similarities)),
        "p5": float(np.percentile(similarities, 5)),
        "p25": float(np.percentile(similarities, 25)),
        "median": float(np.median(similarities)),
        "p75": float(np.percentile(similarities, 75)),
        "p95": float(np.percentile(similarities, 95)),
    }


def nearest_neighbor_overlap(old_emb: np.ndarray, new_emb: np.ndarray, k: int = 10) -> dict:
    """Measure how much the top-k nearest neighbors overlap between old and new embeddings.

    For each query (document), find top-k neighbors in old space and new space,
    then compute the Jaccard overlap.
    """
    n = old_emb.shape[0]
    effective_k = min(k, n - 1)

    old_sim = cosine_similarity_matrix(old_emb, old_emb)
    new_sim = cosine_similarity_matrix(new_emb, new_emb)

    overlaps = []
    for i in range(n):
        # Exclude self
        old_sim[i, i] = -2.0
        new_sim[i, i] = -2.0

        old_topk = set(np.argsort(old_sim[i])[-effective_k:])
        new_topk = set(np.argsort(new_sim[i])[-effective_k:])

        overlap = len(old_topk & new_topk) / len(old_topk | new_topk) if old_topk | new_topk else 1.0
        overlaps.append(overlap)

    overlaps = np.array(overlaps)
    return {
        "k": effective_k,
        "mean_jaccard_overlap": float(np.mean(overlaps)),
        "std": float(np.std(overlaps)),
        "min": float(np.min(overlaps)),
        "median": float(np.median(overlaps)),
        "max": float(np.max(overlaps)),
    }


def recall_at_k(old_emb: np.ndarray, new_emb: np.ndarray, queries_idx: list[int], k_values: list[int] = None) -> dict:
    """Measure recall@k: for each query, how many of the old model's top-k results
    are still in the new model's top-k results.

    queries_idx: indices of documents to use as queries (rest are the "database").
    """
    if k_values is None:
        k_values = [1, 5, 10]

    n = old_emb.shape[0]
    db_idx = [i for i in range(n) if i not in set(queries_idx)]
    if not db_idx:
        raise ValueError("No database documents left after removing queries")

    old_db = old_emb[db_idx]
    new_db = new_emb[db_idx]
    old_q = old_emb[queries_idx]
    new_q = new_emb[queries_idx]

    # Similarities: (num_queries, num_db)
    old_scores = cosine_similarity_matrix(old_q, old_db)
    new_scores = cosine_similarity_matrix(new_q, new_db)

    results = {}
    for k in k_values:
        effective_k = min(k, len(db_idx))
        recalls = []
        for qi in range(len(queries_idx)):
            old_topk = set(np.argsort(old_scores[qi])[-effective_k:])
            new_topk = set(np.argsort(new_scores[qi])[-effective_k:])
            recall = len(old_topk & new_topk) / effective_k
            recalls.append(recall)
        results[f"recall@{k}"] = {
            "mean": float(np.mean(recalls)),
            "std": float(np.std(recalls)),
            "min": float(np.min(recalls)),
            "max": float(np.max(recalls)),
        }

    return results

"""Embedding-based document trust scoring using multi-signal approach.

Combines:
1. IsolationForest outlier detection on corpus embeddings
2. K-nearest neighbor density estimation (distance to clean corpus)
3. Cosine similarity to corpus centroid
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity


class TrustScorer:
    """Scores documents based on how well they fit the corpus embedding distribution.

    Uses a multi-signal approach combining IsolationForest with
    distance-based measures against the clean corpus.
    """

    def __init__(
        self,
        contamination: float = 0.1,
        random_state: int = 42,
        knn_k: int = 5,
        weights: tuple[float, float, float] = (0.15, 0.45, 0.40),
    ):
        self.contamination = contamination
        self.knn_k = knn_k
        self.weights = weights  # (isolation_forest, knn_density, centroid_sim)
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=200,
        )
        self._fitted = False
        self._corpus_embeddings: np.ndarray | None = None
        self._centroid: np.ndarray | None = None

    def fit(self, embeddings: np.ndarray) -> "TrustScorer":
        """Fit the scorer on corpus embeddings (clean documents)."""
        self.model.fit(embeddings)
        self._corpus_embeddings = embeddings.copy()
        self._centroid = embeddings.mean(axis=0, keepdims=True)
        self._fitted = True
        return self

    def _isolation_score(self, embeddings: np.ndarray) -> np.ndarray:
        """IsolationForest score normalized to [0, 1]."""
        raw = self.model.decision_function(embeddings)
        return 1.0 / (1.0 + np.exp(-8.0 * raw))

    def _knn_density_score(self, embeddings: np.ndarray) -> np.ndarray:
        """KNN density: average cosine similarity to k-nearest corpus neighbors."""
        sims = cosine_similarity(embeddings, self._corpus_embeddings)
        k = min(self.knn_k, sims.shape[1])
        topk_sims = np.sort(sims, axis=1)[:, -k:]
        avg_sim = topk_sims.mean(axis=1)
        return avg_sim

    def _centroid_score(self, embeddings: np.ndarray) -> np.ndarray:
        """Cosine similarity to corpus centroid."""
        sims = cosine_similarity(embeddings, self._centroid).flatten()
        return np.clip(sims, 0.0, 1.0)

    def score(self, embeddings: np.ndarray) -> np.ndarray:
        """Return trust scores in [0, 1]. Lower = more suspicious."""
        if not self._fitted:
            raise RuntimeError("TrustScorer must be fit() before scoring.")

        w_if, w_knn, w_cent = self.weights
        s_if = self._isolation_score(embeddings)
        s_knn = self._knn_density_score(embeddings)
        s_cent = self._centroid_score(embeddings)

        combined = w_if * s_if + w_knn * s_knn + w_cent * s_cent
        return combined

    def score_with_consistency(
        self,
        embeddings: np.ndarray,
        consistency_weight: float = 0.35,
    ) -> np.ndarray:
        """Score with within-set consistency bonus.

        Documents that are consistent with other retrieved docs get a bonus.
        Poisoned docs tend to be outliers within the retrieved set.
        """
        base_scores = self.score(embeddings)

        if len(embeddings) < 2:
            return base_scores

        # Compute pairwise similarity within retrieved set
        pairwise = cosine_similarity(embeddings)
        np.fill_diagonal(pairwise, 0)  # exclude self-similarity
        # Average similarity to other docs in the set
        consistency = pairwise.sum(axis=1) / (len(embeddings) - 1)

        # Normalize consistency to [0, 1]
        c_min, c_max = consistency.min(), consistency.max()
        if c_max > c_min:
            consistency = (consistency - c_min) / (c_max - c_min)
        else:
            consistency = np.ones_like(consistency) * 0.5

        final = (1 - consistency_weight) * base_scores + consistency_weight * consistency
        return final

    def predict(self, embeddings: np.ndarray) -> np.ndarray:
        """Return binary predictions: 1 = trusted, -1 = suspicious."""
        if not self._fitted:
            raise RuntimeError("TrustScorer must be fit() before predicting.")
        return self.model.predict(embeddings)

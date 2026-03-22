"""TrustedRetriever — middleware that wraps a LangChain retriever with trust scoring."""

from __future__ import annotations

from typing import Any

import numpy as np
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from sklearn.metrics.pairwise import cosine_similarity

from rag_poison_defense.audit_log import AuditLog, RetrievalRecord
from rag_poison_defense.scorer import TrustScorer


class TrustedRetriever(BaseRetriever):
    """Wraps a LangChain retriever, filtering results through trust scoring.

    Strategy: over-retrieve, compute combined relevance*trust score,
    and return only the top-ranked docs. This ensures results are
    both query-relevant AND consistent with the clean corpus.
    """

    base_retriever: BaseRetriever
    scorer: Any  # TrustScorer
    embed_fn: Any  # Callable[[list[str]], np.ndarray]
    trust_threshold: float = 0.35
    top_k: int = 3
    filter_mode: str = "rerank"  # "flag", "remove", or "rerank"
    relevance_weight: float = 0.4
    trust_weight: float = 0.6
    audit_log: Any = None

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        docs = self.base_retriever.invoke(query)

        if not docs:
            return docs

        texts = [doc.page_content for doc in docs]
        doc_embeddings = self.embed_fn(texts)

        # Trust scores from corpus distribution analysis
        trust_scores = self.scorer.score(doc_embeddings)

        # Relevance scores: cosine similarity between query and each doc
        query_embedding = self.embed_fn([query])
        relevance_scores = cosine_similarity(query_embedding, doc_embeddings).flatten()

        # Normalize both to [0, 1] range within the retrieved set
        def normalize(arr: np.ndarray) -> np.ndarray:
            mn, mx = arr.min(), arr.max()
            if mx > mn:
                return (arr - mn) / (mx - mn)
            return np.ones_like(arr) * 0.5

        norm_trust = normalize(trust_scores)
        norm_relevance = normalize(relevance_scores)

        # Combined score: docs must be both relevant AND trusted
        combined = self.relevance_weight * norm_relevance + self.trust_weight * norm_trust

        # Log ALL docs for audit trail
        audit_records = []
        for doc, ts, rs, cs in zip(docs, trust_scores, relevance_scores, combined):
            doc.metadata["trust_score"] = float(ts)
            doc.metadata["relevance_score"] = float(rs)
            doc.metadata["combined_score"] = float(cs)
            doc.metadata["is_trusted"] = bool(ts >= self.trust_threshold)

            if self.audit_log:
                audit_records.append(RetrievalRecord(
                    query=query,
                    doc_id=doc.metadata.get("id", doc.metadata.get("source", "unknown")),
                    content_preview=doc.page_content[:200],
                    source=doc.metadata.get("source", "unknown"),
                    trust_score=float(ts),
                    is_trusted=bool(ts >= self.trust_threshold),
                ))

        if self.audit_log and audit_records:
            self.audit_log.log(audit_records)

        if self.filter_mode == "rerank":
            ranked = sorted(
                zip(docs, combined), key=lambda x: x[1], reverse=True,
            )
            return [doc for doc, _ in ranked[:self.top_k]]
        elif self.filter_mode == "remove":
            return [doc for doc in docs if doc.metadata.get("is_trusted", True)]
        else:
            return docs

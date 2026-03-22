"""Demo: end-to-end usage of TrustedRetriever with audit log."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer

from rag_poison_defense import TrustScorer, TrustedRetriever, AuditLog
from rag_poison_defense.dataset import CLEAN_DOCS, POISONED_DOCS


class LocalEmbeddings(Embeddings):
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], show_progress_bar=False)[0].tolist()


def main():
    print("=== RAG Poison Defense — Demo ===\n")

    # Setup
    embeddings = LocalEmbeddings()

    docs = []
    for d in CLEAN_DOCS + POISONED_DOCS:
        docs.append(Document(
            page_content=d["text"],
            metadata={"id": d["id"], "source": d.get("source", "unknown")},
        ))
    vectorstore = FAISS.from_documents(docs, embeddings)
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

    # Train scorer on clean corpus
    clean_texts = [d["text"] for d in CLEAN_DOCS]
    clean_embs = np.array(embeddings.embed_documents(clean_texts))
    scorer = TrustScorer(contamination=0.05)
    scorer.fit(clean_embs)

    def embed_fn(texts):
        return np.array(embeddings.embed_documents(texts))

    # Create TrustedRetriever with audit log
    audit = AuditLog(db_path="demo_audit.db")
    trusted = TrustedRetriever(
        base_retriever=base_retriever,
        scorer=scorer,
        embed_fn=embed_fn,
        trust_threshold=0.35,
        top_k=3,
        filter_mode="rerank",
        relevance_weight=0.3,
        trust_weight=0.7,
        audit_log=audit,
    )

    # --- Demo Query 1: Capital of France ---
    print("Query: 'What is the capital of France?'")
    print("-" * 50)
    results = trusted.invoke("What is the capital of France?")
    for i, doc in enumerate(results):
        print(f"  [{i+1}] trust={doc.metadata['trust_score']:.3f} "
              f"id={doc.metadata['id']} — {doc.page_content[:80]}...")
    print()

    # --- Demo Query 2: Who created Python? ---
    print("Query: 'Who created Python?'")
    print("-" * 50)
    results = trusted.invoke("Who created Python?")
    for i, doc in enumerate(results):
        print(f"  [{i+1}] trust={doc.metadata['trust_score']:.3f} "
              f"id={doc.metadata['id']} — {doc.page_content[:80]}...")
    print()

    # --- Demo Query 3: Speed of light ---
    print("Query: 'What is the speed of light?'")
    print("-" * 50)
    results = trusted.invoke("What is the speed of light?")
    for i, doc in enumerate(results):
        print(f"  [{i+1}] trust={doc.metadata['trust_score']:.3f} "
              f"id={doc.metadata['id']} — {doc.page_content[:80]}...")
    print()

    # --- Audit Log Queries ---
    print("=" * 50)
    print("Audit Log Analysis")
    print("=" * 50)

    summary = audit.summary()
    print(f"\nOverall: {summary['total']} retrievals, "
          f"{summary['trusted']} trusted, {summary['untrusted']} untrusted")
    print(f"Average trust score: {summary['avg_score']:.3f}")

    print("\nLow-trust documents (score < 0.4):")
    low_trust = audit.query_low_trust(threshold=0.4)
    for r in low_trust[:5]:
        print(f"  score={r['trust_score']:.3f} id={r['doc_id']} "
              f"query='{r['query'][:40]}...'")

    print("\nRecords from 'unknown_blog' source:")
    blog_records = audit.query_by_source("unknown_blog")
    for r in blog_records[:3]:
        print(f"  score={r['trust_score']:.3f} query='{r['query'][:40]}...'")

    audit.close()

    # Cleanup
    Path("demo_audit.db").unlink(missing_ok=True)


if __name__ == "__main__":
    main()

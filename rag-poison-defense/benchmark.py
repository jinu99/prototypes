"""Benchmark: PoisonedRAG attack success rate before/after TrustedRetriever defense.

This script:
1. Builds a vector store with clean + poisoned documents
2. Measures attack success rate WITHOUT defense (baseline)
3. Measures attack success rate WITH TrustedRetriever defense
4. Reports before/after comparison
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from sentence_transformers import SentenceTransformer

from rag_poison_defense.scorer import TrustScorer
from rag_poison_defense.trusted_retriever import TrustedRetriever
from rag_poison_defense.audit_log import AuditLog
from rag_poison_defense.dataset import CLEAN_DOCS, POISONED_DOCS, BENCHMARK_QUERIES


class LocalEmbeddings(Embeddings):
    """LangChain-compatible wrapper around sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], show_progress_bar=False)[0].tolist()


def build_vectorstore(
    clean_docs: list[dict],
    poisoned_docs: list[dict],
    embeddings: LocalEmbeddings,
) -> FAISS:
    """Build a FAISS vector store with both clean and poisoned documents."""
    documents = []
    for d in clean_docs:
        documents.append(Document(
            page_content=d["text"],
            metadata={"id": d["id"], "source": d["source"]},
        ))
    for d in poisoned_docs:
        documents.append(Document(
            page_content=d["text"],
            metadata={"id": d["id"], "source": d["source"]},
        ))
    return FAISS.from_documents(documents, embeddings)


def check_attack_success(retrieved_docs: list[Document], query_info: dict) -> bool:
    """Check if the attack succeeded: poisoned doc appears in top results
    AND would likely influence the answer."""
    for doc in retrieved_docs[:3]:  # Check top-3 results
        doc_id = doc.metadata.get("id", "")
        if doc_id.startswith("poison_"):
            return True
    return False


def run_benchmark():
    print("=" * 70)
    print("  RAG Poison Defense — Benchmark")
    print("=" * 70)
    print()

    # Initialize embedding model
    print("[1/5] Loading embedding model (all-MiniLM-L6-v2)...")
    embeddings = LocalEmbeddings()

    # Build vector store
    print("[2/5] Building vector store with clean + poisoned documents...")
    print(f"      Clean docs: {len(CLEAN_DOCS)}, Poisoned docs: {len(POISONED_DOCS)}")
    vectorstore = build_vectorstore(CLEAN_DOCS, POISONED_DOCS, embeddings)
    # Baseline: standard RAG with k=3 (typical retrieval count)
    baseline_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    # Defense: over-fetch k=10, then rerank to top 3
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

    # --- Baseline: No defense ---
    print("[3/5] Running baseline (no defense)...")
    baseline_attacks = 0
    for qinfo in BENCHMARK_QUERIES:
        docs = baseline_retriever.invoke(qinfo["query"])
        if check_attack_success(docs, qinfo):
            baseline_attacks += 1

    baseline_rate = baseline_attacks / len(BENCHMARK_QUERIES) * 100
    print(f"      Baseline attack success rate: {baseline_rate:.0f}% ({baseline_attacks}/{len(BENCHMARK_QUERIES)})")

    # --- Defense: TrustedRetriever ---
    print("[4/5] Training trust scorer on clean corpus embeddings...")
    clean_texts = [d["text"] for d in CLEAN_DOCS]
    clean_embeddings = np.array(embeddings.embed_documents(clean_texts))

    scorer = TrustScorer(contamination=0.05)
    scorer.fit(clean_embeddings)

    def embed_fn(texts: list[str]) -> np.ndarray:
        return np.array(embeddings.embed_documents(texts))

    with tempfile.TemporaryDirectory() as tmpdir:
        audit = AuditLog(db_path=Path(tmpdir) / "benchmark_audit.db")

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

        print("[5/5] Running defended retrieval...")
        defended_attacks = 0
        for qinfo in BENCHMARK_QUERIES:
            docs = trusted.invoke(qinfo["query"])
            if check_attack_success(docs, qinfo):
                defended_attacks += 1

        defended_rate = defended_attacks / len(BENCHMARK_QUERIES) * 100

        # Print results
        print()
        print("=" * 70)
        print("  RESULTS")
        print("=" * 70)
        print(f"  Baseline attack success rate:  {baseline_rate:5.1f}%  ({baseline_attacks}/{len(BENCHMARK_QUERIES)})")
        print(f"  Defended attack success rate:  {defended_rate:5.1f}%  ({defended_attacks}/{len(BENCHMARK_QUERIES)})")
        print(f"  Reduction:                     {baseline_rate - defended_rate:5.1f} percentage points")
        print()

        if baseline_rate >= 70 and defended_rate <= 30:
            print("  ✅ PASS — Attack rate reduced from {:.0f}%+ to {:.0f}% (≤30%)".format(
                baseline_rate, defended_rate))
        elif defended_rate <= 30:
            print("  ⚠️  PARTIAL — Defended rate ≤30% but baseline was only {:.0f}%".format(baseline_rate))
        else:
            print("  ❌ FAIL — Defended rate {:.0f}% exceeds 30% target".format(defended_rate))

        # Audit log summary
        summary = audit.summary()
        print()
        print("  Audit Log Summary:")
        print(f"    Total retrievals logged: {summary['total']}")
        print(f"    Trusted: {summary['trusted']}, Untrusted: {summary['untrusted']}")
        print(f"    Average trust score: {summary['avg_score']:.3f}")
        print(f"    Unique queries: {summary['unique_queries']}")
        print("=" * 70)

        audit.close()

    return baseline_rate, defended_rate


if __name__ == "__main__":
    baseline, defended = run_benchmark()
    sys.exit(0 if defended <= 30 else 1)

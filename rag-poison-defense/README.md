# RAG Poison Defense

> Embedding-based trust scoring middleware that defends RAG systems against knowledge base poisoning attacks.

## Architecture

```
                          ┌─────────────────────────────────────────┐
                          │          TrustedRetriever               │
                          │  (LangChain BaseRetriever wrapper)      │
 Query ──▶ Over-fetch ──▶ │                                         │
           (k=10)         │  ┌───────────┐   ┌──────────────────┐  │
                          │  │ TrustScorer│   │  Relevance Score │  │
                          │  │            │   │  (query-doc sim) │  │
                          │  │ IsoForest  │   └──────────────────┘  │
                          │  │ KNN Dens.  │            │            │
                          │  │ Centroid   │            │            │
                          │  └─────┬──────┘            │            │
                          │        │                   │            │
                          │        ▼                   ▼            │
                          │   combined = 0.3×relevance + 0.7×trust  │
                          │        │                                │
                          │        ▼                                │
                          │   Re-rank → Top-K (k=3)                │
                          │        │                                │
                          └────────┼────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼                             ▼
             Trusted Docs                   AuditLog (SQLite)
             (top-3 results)                (query, source, score)
```

## Demo

```
$ uv run python benchmark.py

======================================================================
  RAG Poison Defense — Benchmark
======================================================================

[1/5] Loading embedding model (all-MiniLM-L6-v2)...
[2/5] Building vector store with clean + poisoned documents...
      Clean docs: 50, Poisoned docs: 10
[3/5] Running baseline (no defense)...
      Baseline attack success rate: 80% (8/10)
[4/5] Training trust scorer on clean corpus embeddings...
[5/5] Running defended retrieval...

======================================================================
  RESULTS
======================================================================
  Baseline attack success rate:   80.0%  (8/10)
  Defended attack success rate:   20.0%  (2/10)
  Reduction:                      60.0 percentage points

  ✅ PASS — Attack rate reduced from 80%+ to 20% (≤30%)
======================================================================
```

## Quick Start

```python
from rag_poison_defense import TrustScorer, TrustedRetriever, AuditLog

scorer = TrustScorer().fit(clean_corpus_embeddings)
trusted = TrustedRetriever(base_retriever=my_retriever, scorer=scorer, embed_fn=my_embed_fn)
results = trusted.invoke("What is the capital of France?")  # poisoned docs filtered out
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 벤치마크 실행
uv run python benchmark.py

# 데모 실행
uv run python demo.py
```

## 구조

```
rag-poison-defense/
├── src/rag_poison_defense/
│   ├── __init__.py           # Public API exports
│   ├── scorer.py             # TrustScorer (IsolationForest + KNN + centroid)
│   ├── trusted_retriever.py  # TrustedRetriever (LangChain middleware)
│   ├── audit_log.py          # AuditLog (SQLite storage & queries)
│   └── dataset.py            # Synthetic PoisonedRAG dataset (50 clean + 10 poison)
├── benchmark.py              # Before/after attack rate benchmark
├── demo.py                   # Interactive demo with audit log
├── BUILD_LOG.md              # Build process log
├── STATUS.md                 # Completion status
└── pyproject.toml            # Package config
```

## 원본
prototype-pipeline spec: rag-poison-defense

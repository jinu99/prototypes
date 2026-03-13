"""Embedding model loading and vector generation."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import numpy as np

# Suppress noisy HuggingFace/transformers warnings
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

from sentence_transformers import SentenceTransformer


def load_model(model_name: str) -> SentenceTransformer:
    """Load a sentence-transformers model."""
    return SentenceTransformer(model_name, trust_remote_code=False)


def load_corpus(corpus_path: str) -> list[str]:
    """Load a text corpus from a file (one document per line) or directory of .txt files."""
    p = Path(corpus_path)
    if p.is_file():
        texts = [line.strip() for line in p.read_text().splitlines() if line.strip()]
    elif p.is_dir():
        texts = []
        for f in sorted(p.glob("*.txt")):
            content = f.read_text().strip()
            if content:
                texts.append(content)
    else:
        raise FileNotFoundError(f"Corpus path not found: {corpus_path}")
    if not texts:
        raise ValueError(f"No documents found in: {corpus_path}")
    return texts


def embed_texts(model: SentenceTransformer, texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Embed a list of texts, returns (n, dim) array."""
    start = time.time()
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=True)
    elapsed = time.time() - start
    return np.array(embeddings), elapsed

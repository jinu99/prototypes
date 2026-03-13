"""Embedding-based consistency checker for detecting contradictions."""

import json
import logging
import os
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

from .db import Fact

# Lazy-loaded model
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        # Suppress noisy model loading messages
        for name in ("sentence_transformers", "transformers", "torch", "huggingface_hub"):
            logging.getLogger(name).setLevel(logging.ERROR)
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_fact(fact: Fact) -> list[float]:
    """Create an embedding for a fact's semantic content."""
    model = get_model()
    text = f"{fact.entity} {fact.attribute}: {fact.value}. {fact.raw_sentence}"
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_facts(facts: list[Fact]) -> list[list[float]]:
    """Batch-embed multiple facts."""
    model = get_model()
    texts = [
        f"{f.entity} {f.attribute}: {f.value}. {f.raw_sentence}"
        for f in facts
    ]
    if not texts:
        return []
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    return float(np.dot(va, vb))


@dataclass
class Inconsistency:
    fact_a: Fact
    fact_b: Fact
    similarity: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "fact_a": fact_a.to_dict() if (fact_a := self.fact_a) else None,
            "fact_b": fact_b.to_dict() if (fact_b := self.fact_b) else None,
            "similarity": round(self.similarity, 3),
            "reason": self.reason,
        }

    def report(self) -> str:
        return (
            f"⚠ INCONSISTENCY: {self.reason}\n"
            f"  Fact A: {self.fact_a.summary()} "
            f"(file={self.fact_a.source_file}, {self.fact_a.chapter}, "
            f"line {self.fact_a.line_start})\n"
            f"    → \"{self.fact_a.raw_sentence}\"\n"
            f"  Fact B: {self.fact_b.summary()} "
            f"(file={self.fact_b.source_file}, {self.fact_b.chapter}, "
            f"line {self.fact_b.line_start})\n"
            f"    → \"{self.fact_b.raw_sentence}\"\n"
            f"  Similarity: {self.similarity:.3f}"
        )


# Attributes where differing values indicate contradiction
CONTRADICTABLE_ATTRS = {
    "eye_color", "hair", "age", "height", "build", "location",
    "occupation", "age_description", "skin",
}


def _values_conflict(attr: str, val_a: str, val_b: str) -> bool:
    """Check if two values for the same attribute actually conflict."""
    a = val_a.lower().strip()
    b = val_b.lower().strip()
    if a == b:
        return False
    # One might contain the other (e.g., "dark brown" vs "brown")
    if a in b or b in a:
        return False
    return True


def check_consistency(
    new_facts: list[Fact],
    existing_facts: list[Fact],
    similarity_threshold: float = 0.6,
) -> list[Inconsistency]:
    """Find potential inconsistencies between new and existing facts.

    Strategy:
    1. For same-entity, same-attribute facts: direct value comparison
    2. For high embedding similarity: flag as potential conflict
    """
    inconsistencies: list[Inconsistency] = []

    # Phase 1: Direct attribute comparison (same entity + same attribute)
    for new_f in new_facts:
        for old_f in existing_facts:
            if (new_f.entity.lower() == old_f.entity.lower()
                    and new_f.attribute.lower() == old_f.attribute.lower()
                    and new_f.attribute.lower() in CONTRADICTABLE_ATTRS):
                if _values_conflict(new_f.attribute, new_f.value, old_f.value):
                    sim = 0.0
                    if new_f.embedding and old_f.embedding:
                        sim = cosine_similarity(new_f.embedding, old_f.embedding)
                    inconsistencies.append(Inconsistency(
                        fact_a=old_f,
                        fact_b=new_f,
                        similarity=sim,
                        reason=(
                            f"{new_f.entity}.{new_f.attribute} changed: "
                            f"'{old_f.value}' → '{new_f.value}'"
                        ),
                    ))

    # Phase 2: Embedding similarity for cross-attribute potential conflicts
    if not new_facts or not existing_facts:
        return inconsistencies

    new_embeddings = []
    old_embeddings = []
    for f in new_facts:
        new_embeddings.append(f.embedding or embed_fact(f))
    for f in existing_facts:
        old_embeddings.append(f.embedding or embed_fact(f))

    already_found = {
        (i.fact_a.id, i.fact_b.raw_sentence) for i in inconsistencies
    }

    for i, new_f in enumerate(new_facts):
        for j, old_f in enumerate(existing_facts):
            # Skip if same entity+attr already checked
            if (new_f.entity.lower() == old_f.entity.lower()
                    and new_f.attribute.lower() == old_f.attribute.lower()):
                continue

            sim = cosine_similarity(new_embeddings[i], old_embeddings[j])
            if sim > similarity_threshold:
                # Same entity, different attributes with high similarity
                # might be contradictory descriptions
                if new_f.entity.lower() == old_f.entity.lower():
                    key = (old_f.id, new_f.raw_sentence)
                    if key not in already_found:
                        already_found.add(key)
                        inconsistencies.append(Inconsistency(
                            fact_a=old_f,
                            fact_b=new_f,
                            similarity=sim,
                            reason=(
                                f"High similarity between different attributes "
                                f"for {new_f.entity}: "
                                f"'{old_f.attribute}={old_f.value}' vs "
                                f"'{new_f.attribute}={new_f.value}'"
                            ),
                        ))

    # Sort by severity (direct contradictions first, then by similarity)
    inconsistencies.sort(key=lambda x: (-1 if "changed" in x.reason else 0, -x.similarity))
    return inconsistencies

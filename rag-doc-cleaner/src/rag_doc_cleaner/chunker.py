"""Basic chunking statistics: size distribution and duplication rate."""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class ChunkStats:
    total_chunks: int
    total_chars: int
    avg_size: float
    min_size: int
    max_size: int
    median_size: int
    size_distribution: dict[str, int]  # bucket -> count
    duplicate_count: int
    duplicate_rate: float  # 0.0 to 1.0
    unique_chunks: int

    def to_dict(self) -> dict:
        return {
            "total_chunks": self.total_chunks,
            "total_chars": self.total_chars,
            "avg_size": round(self.avg_size, 1),
            "min_size": self.min_size,
            "max_size": self.max_size,
            "median_size": self.median_size,
            "size_distribution": self.size_distribution,
            "duplicate_count": self.duplicate_count,
            "duplicate_rate": round(self.duplicate_rate, 4),
            "unique_chunks": self.unique_chunks,
        }


def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into chunks with optional overlap (simple character-based)."""
    # Split on paragraph boundaries first, then recombine to chunk_size
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # If paragraph itself is larger than chunk_size, split it
            if len(para) > chunk_size:
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= chunk_size:
                        current = f"{current} {word}" if current else word
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


def compute_stats(text: str, chunk_size: int = 500) -> ChunkStats:
    """Compute chunking statistics for the given text."""
    chunks = split_into_chunks(text, chunk_size=chunk_size)

    if not chunks:
        return ChunkStats(
            total_chunks=0, total_chars=0, avg_size=0, min_size=0,
            max_size=0, median_size=0, size_distribution={},
            duplicate_count=0, duplicate_rate=0.0, unique_chunks=0,
        )

    sizes = sorted(len(c) for c in chunks)
    total_chars = sum(sizes)

    # Size distribution buckets
    buckets = {"0-100": 0, "101-250": 0, "251-500": 0, "501-1000": 0, "1000+": 0}
    for s in sizes:
        if s <= 100:
            buckets["0-100"] += 1
        elif s <= 250:
            buckets["101-250"] += 1
        elif s <= 500:
            buckets["251-500"] += 1
        elif s <= 1000:
            buckets["501-1000"] += 1
        else:
            buckets["1000+"] += 1

    # Duplication detection via content hashing
    hashes = [hashlib.md5(c.encode()).hexdigest() for c in chunks]
    hash_counts = Counter(hashes)
    unique = len(hash_counts)
    duplicates = sum(1 for c in hash_counts.values() if c > 1)
    duplicate_chunks = sum(c - 1 for c in hash_counts.values() if c > 1)

    median_idx = len(sizes) // 2
    median = sizes[median_idx] if sizes else 0

    return ChunkStats(
        total_chunks=len(chunks),
        total_chars=total_chars,
        avg_size=total_chars / len(chunks),
        min_size=sizes[0],
        max_size=sizes[-1],
        median_size=median,
        size_distribution=buckets,
        duplicate_count=duplicate_chunks,
        duplicate_rate=duplicate_chunks / len(chunks) if chunks else 0.0,
        unique_chunks=unique,
    )

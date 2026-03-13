"""Report generation — console and JSON output."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_report(
    old_model: str,
    new_model: str,
    num_docs: int,
    old_dim: int,
    new_dim: int,
    cosine_stats: dict,
    nn_overlap: dict,
    recall: dict,
    embed_time_old: float,
    embed_time_new: float,
) -> dict:
    """Build a structured report dictionary."""
    dim_match = old_dim == new_dim
    mean_recall_1 = recall.get("recall@1", {}).get("mean", 0)
    mean_recall_5 = recall.get("recall@5", {}).get("mean", 0)
    mean_recall_10 = recall.get("recall@10", {}).get("mean", 0)
    nn_mean = nn_overlap.get("mean_jaccard_overlap", 0)

    # Risk assessment
    if mean_recall_10 >= 0.9 and nn_mean >= 0.7:
        risk = "LOW"
        verdict = "Migration appears safe. Minimal recall degradation expected."
    elif mean_recall_10 >= 0.7 and nn_mean >= 0.4:
        risk = "MEDIUM"
        verdict = "Migration has moderate risk. Some recall degradation expected. Consider testing with production queries."
    else:
        risk = "HIGH"
        verdict = "Migration is risky. Significant recall degradation expected. Full re-evaluation recommended."

    return {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "old_model": old_model,
            "new_model": new_model,
            "num_documents": num_docs,
        },
        "dimensions": {
            "old_model_dim": old_dim,
            "new_model_dim": new_dim,
            "match": dim_match,
        },
        "cosine_similarity_distribution": cosine_stats,
        "nearest_neighbor_overlap": nn_overlap,
        "recall": recall,
        "performance": {
            "old_model_embed_time_s": round(embed_time_old, 3),
            "new_model_embed_time_s": round(embed_time_new, 3),
        },
        "risk_assessment": {
            "level": risk,
            "verdict": verdict,
            "recall@10_mean": round(mean_recall_10, 4),
            "nn_overlap_mean": round(nn_mean, 4),
        },
    }


def print_report(report: dict) -> None:
    """Print a human-readable report to console."""
    meta = report["metadata"]
    dims = report["dimensions"]
    cosine = report["cosine_similarity_distribution"]
    nn = report["nearest_neighbor_overlap"]
    recall = report["recall"]
    perf = report["performance"]
    risk = report["risk_assessment"]

    print("\n" + "=" * 60)
    print("  EMBEDDING MIGRATION GUARD — COMPARISON REPORT")
    print("=" * 60)

    print(f"\n  Old model : {meta['old_model']}")
    print(f"  New model : {meta['new_model']}")
    print(f"  Documents : {meta['num_documents']}")
    print(f"  Timestamp : {meta['timestamp']}")

    print(f"\n{'─' * 60}")
    print("  DIMENSIONS")
    print(f"{'─' * 60}")
    print(f"  Old: {dims['old_model_dim']}   New: {dims['new_model_dim']}   Match: {'✓' if dims['match'] else '✗'}")

    print(f"\n{'─' * 60}")
    print("  COSINE SIMILARITY (old ↔ new, per document)")
    print(f"{'─' * 60}")
    print(f"  Mean: {cosine['mean']:.4f}   Std: {cosine['std']:.4f}")
    print(f"  Min:  {cosine['min']:.4f}   Max: {cosine['max']:.4f}")
    print(f"  P5:   {cosine['p5']:.4f}   P25: {cosine['p25']:.4f}   Median: {cosine['median']:.4f}   P75: {cosine['p75']:.4f}   P95: {cosine['p95']:.4f}")

    print(f"\n{'─' * 60}")
    print(f"  NEAREST-NEIGHBOR OVERLAP (k={nn['k']})")
    print(f"{'─' * 60}")
    print(f"  Mean Jaccard: {nn['mean_jaccard_overlap']:.4f}   Std: {nn['std']:.4f}")
    print(f"  Min: {nn['min']:.4f}   Median: {nn['median']:.4f}   Max: {nn['max']:.4f}")

    print(f"\n{'─' * 60}")
    print("  RECALL@K")
    print(f"{'─' * 60}")
    for key, vals in sorted(recall.items(), key=lambda x: int(x[0].split("@")[1])):
        print(f"  {key}: mean={vals['mean']:.4f}  std={vals['std']:.4f}  min={vals['min']:.4f}  max={vals['max']:.4f}")

    print(f"\n{'─' * 60}")
    print("  PERFORMANCE")
    print(f"{'─' * 60}")
    print(f"  Old model embedding: {perf['old_model_embed_time_s']:.3f}s")
    print(f"  New model embedding: {perf['new_model_embed_time_s']:.3f}s")

    print(f"\n{'─' * 60}")
    level_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    print(f"  RISK: {level_icon.get(risk['level'], '⚪')} {risk['level']}")
    print(f"{'─' * 60}")
    print(f"  {risk['verdict']}")
    print("=" * 60 + "\n")


def export_json(report: dict, output_path: str) -> str:
    """Export report to JSON file."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return str(p.resolve())

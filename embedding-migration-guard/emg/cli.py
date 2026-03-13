"""CLI interface for Embedding Migration Guard."""
from __future__ import annotations

import sys
import time

import click
import numpy as np

from emg.comparator import (
    cosine_distribution_stats,
    nearest_neighbor_overlap,
    pairwise_cosine_similarities,
    recall_at_k,
)
from emg.embedder import embed_texts, load_corpus, load_model
from emg.report import build_report, export_json, print_report


def run_comparison(
    old_model_name: str,
    new_model_name: str,
    texts: list[str],
    query_indices: list[int] | None = None,
    k_values: list[int] | None = None,
    nn_k: int = 10,
) -> dict:
    """Run the full comparison pipeline and return a report dict."""
    if k_values is None:
        k_values = [1, 5, 10]

    click.echo(f"\n  Loading old model: {old_model_name}")
    old_model = load_model(old_model_name)
    click.echo(f"  Loading new model: {new_model_name}")
    new_model = load_model(new_model_name)

    click.echo(f"  Embedding {len(texts)} documents with old model...")
    old_emb, old_time = embed_texts(old_model, texts)
    click.echo(f"  Embedding {len(texts)} documents with new model...")
    new_emb, new_time = embed_texts(new_model, texts)

    old_dim = old_emb.shape[1]
    new_dim = new_emb.shape[1]

    # If dimensions differ, we can still compute recall but not per-doc cosine
    if old_dim == new_dim:
        click.echo("  Computing pairwise cosine similarities...")
        pair_sims = pairwise_cosine_similarities(old_emb, new_emb)
        cosine_stats = cosine_distribution_stats(pair_sims)
    else:
        click.echo("  ⚠ Dimensions differ — skipping pairwise cosine similarity")
        cosine_stats = {
            "mean": 0, "std": 0, "min": 0, "max": 0,
            "p5": 0, "p25": 0, "median": 0, "p75": 0, "p95": 0,
            "note": "Dimensions differ, pairwise cosine not comparable",
        }

    click.echo(f"  Computing nearest-neighbor overlap (k={nn_k})...")
    nn = nearest_neighbor_overlap(old_emb, new_emb, k=nn_k)

    if query_indices is None:
        query_indices = list(range(0, len(texts), 5))

    click.echo(f"  Computing recall@k with {len(query_indices)} queries...")
    recall = recall_at_k(old_emb, new_emb, query_indices, k_values=k_values)

    return build_report(
        old_model=old_model_name,
        new_model=new_model_name,
        num_docs=len(texts),
        old_dim=old_dim,
        new_dim=new_dim,
        cosine_stats=cosine_stats,
        nn_overlap=nn,
        recall=recall,
        embed_time_old=old_time,
        embed_time_new=new_time,
    )


@click.group()
def cli():
    """Embedding Migration Guard — predict recall@k drop before switching models."""
    pass


@cli.command()
@click.option("--old", "old_model", required=True, help="Old embedding model name (sentence-transformers)")
@click.option("--new", "new_model", required=True, help="New embedding model name (sentence-transformers)")
@click.option("--corpus", required=True, help="Path to corpus file (one doc per line) or directory of .txt files")
@click.option("--output", default=None, help="Path to save JSON report (optional)")
@click.option("--k", default="1,5,10", help="Comma-separated k values for recall@k (default: 1,5,10)")
@click.option("--nn-k", default=10, help="k for nearest-neighbor overlap (default: 10)")
def check(old_model: str, new_model: str, corpus: str, output: str | None, k: str, nn_k: int):
    """Compare two embedding models on a corpus and report recall@k drop."""
    k_values = [int(x.strip()) for x in k.split(",")]

    try:
        texts = load_corpus(corpus)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    start = time.time()
    report = run_comparison(old_model, new_model, texts, k_values=k_values, nn_k=nn_k)
    total_time = time.time() - start

    print_report(report)
    click.echo(f"  Total time: {total_time:.1f}s")

    if output:
        path = export_json(report, output)
        click.echo(f"  JSON report saved to: {path}")


@cli.command()
@click.option("--output", default=None, help="Path to save JSON report (optional)")
def demo(output: str | None):
    """Run a full demo with built-in sample corpus comparing two small models."""
    from emg.sample_corpus import SAMPLE_DOCS, SAMPLE_QUERY_INDICES

    old_model = "all-MiniLM-L6-v2"
    new_model = "all-MiniLM-L12-v2"

    click.echo(f"\n  EMG Demo — comparing {old_model} vs {new_model}")
    click.echo(f"  Corpus: {len(SAMPLE_DOCS)} built-in sample documents")
    click.echo(f"  Queries: {len(SAMPLE_QUERY_INDICES)} sample queries")

    start = time.time()
    report = run_comparison(
        old_model, new_model, SAMPLE_DOCS,
        query_indices=SAMPLE_QUERY_INDICES,
        k_values=[1, 5, 10],
    )
    total_time = time.time() - start

    print_report(report)
    click.echo(f"  Total time: {total_time:.1f}s")

    if output:
        path = export_json(report, output)
        click.echo(f"  JSON report saved to: {path}")
    else:
        default_path = export_json(report, "emg_demo_report.json")
        click.echo(f"  JSON report saved to: {default_path}")


def main():
    cli()


if __name__ == "__main__":
    main()

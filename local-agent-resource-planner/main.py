"""Local Agent VRAM Resource Planner — Entry point.

Usage:
    uv run main.py              # Start web server on port 8000
    uv run main.py --port 3000  # Custom port
    uv run main.py --cli        # CLI mode: show sample estimates
"""

import argparse

from planner import (
    plan_single_model,
    plan_multi_model,
    plan_grid_search,
    validate_against_llamacpp,
)
from gguf_parser import SAMPLE_PROFILES


def cli_mode():
    """Run in CLI mode — show sample estimations."""
    print("=" * 60)
    print(" Local Agent VRAM Resource Planner — CLI Mode")
    print("=" * 60)

    # Single model estimates
    print("\n--- Single Model Estimates (ctx=4096) ---\n")
    for key in SAMPLE_PROFILES:
        result = plan_single_model(key, 4096)
        est = result["estimate"]
        moe_tag = " [MoE]" if est["is_moe"] else ""
        print(f"  {est['model_name']}{moe_tag}")
        print(f"    Total: {est['total_mb']:,.0f} MB | Weights: {est['weights_mb']:,.0f} | "
              f"KV: {est['kv_cache_mb']:,.0f} | Act: {est['activation_mb']:,.0f} | "
              f"OH: {est['overhead_mb']:,.0f}")

    # Multi-model example
    print("\n--- Multi-Model: Llama-7B + Phi-2 (24GB budget) ---\n")
    result = plan_multi_model([
        {"model_key": "llama-7b-q4km", "context_length": 4096},
        {"model_key": "phi-2-q8", "context_length": 2048},
    ], vram_budget_mb=24576)
    print(f"  Total VRAM: {result['total_vram_mb']:,.0f} MB")
    print(f"  Feasible: {result['feasible']}")
    if result['headroom_mb'] is not None:
        print(f"  Headroom: {result['headroom_mb']:,.0f} MB")

    # Validation
    print("\n--- llama.cpp Reference Validation ---\n")
    validations = validate_against_llamacpp()
    for v in validations:
        status = "PASS" if v["within_20pct"] else "FAIL"
        print(f"  [{status}] {v['model']} {v['quantization']} ctx={v['context_length']}: "
              f"est={v['estimated_mb']:,.0f} ref={v['reference_mb']:,} err={v['error_percent']:.1f}%")

    # Grid search example
    print("\n--- Grid Search: 8GB VRAM Budget ---\n")
    combos = plan_grid_search(list(SAMPLE_PROFILES.keys()), 8192)
    print(f"  {len(combos)} feasible combinations found")
    for c in combos[:5]:
        print(f"    {c['model_name']} {c['quantization']} ctx={c['context_length']}: "
              f"{c['total_mb']:,.0f} MB")
    if len(combos) > 5:
        print(f"    ... and {len(combos) - 5} more")


def web_mode(port):
    """Start web server."""
    from server import run_server
    run_server(port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VRAM Resource Planner")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    parser.add_argument("--cli", action="store_true", help="CLI mode")
    args = parser.parse_args()

    if args.cli:
        cli_mode()
    else:
        web_mode(args.port)

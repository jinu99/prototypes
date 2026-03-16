"""Benchmark VRAM estimates against known real-world measurements.

Reference values from community benchmarks (llama.cpp, Ollama users):
- These are approximate VRAM usage values reported by nvidia-smi while running inference.
"""

from vram_estimator import estimate_vram

# (model_name, params_b, quant, context_length, measured_vram_mb, source)
BENCHMARKS = [
    # LLaMA 3.1 8B Q4_K_M @ 4K context — widely reported ~5.0-5.5GB
    ("llama-8b", 8.03, "Q4_K_M", 4096, 5300, "Ollama community average"),
    # LLaMA 2 13B Q4_K_M @ 4K context — ~10-11GB with full KV cache (no GQA, 40 KV heads)
    ("llama-13b", 13.02, "Q4_K_M", 4096, 10500, "llama.cpp full ctx benchmark"),
    # LLaMA 3.1 70B Q4_K_M @ 4K context — typically ~40-42GB
    ("llama-70b", 70.6, "Q4_K_M", 4096, 41500, "Ollama docs / community"),
    # Mistral 7B Q4_K_M @ 4K — typically ~4.8-5.2GB
    ("mistral-7b", 7.24, "Q4_K_M", 4096, 5000, "HuggingFace benchmark"),
    # LLaMA 3.1 8B F16 @ 4K — typically ~16-17GB
    ("llama-8b", 8.03, "F16", 4096, 16500, "llama.cpp F16 report"),
]


def run_benchmark():
    print("=" * 70)
    print("VRAM Estimation Accuracy Benchmark")
    print("=" * 70)
    results = []

    for model_name, params_b, quant, ctx, measured_mb, source in BENCHMARKS:
        est = estimate_vram(
            params_b=params_b,
            quant=quant,
            context_length=ctx,
            model_name=model_name,
        )
        error_mb = est.total_mb - measured_mb
        error_pct = (error_mb / measured_mb) * 100

        passed = abs(error_pct) <= 15.0
        results.append((model_name, quant, ctx, est.total_mb, measured_mb, error_pct, passed))

        status = "PASS" if passed else "FAIL"
        print(f"\n[{status}] {model_name} {quant} @ {ctx // 1024}K ctx")
        print(f"  Estimated: {est.total_mb:.0f} MB ({est.total_mb / 1024:.2f} GB)")
        print(f"    Weights:  {est.weights_mb:.0f} MB")
        print(f"    KV Cache: {est.kv_cache_mb:.0f} MB")
        print(f"    Overhead: {est.overhead_mb:.0f} MB")
        print(f"  Measured:  {measured_mb:.0f} MB ({measured_mb / 1024:.2f} GB) [{source}]")
        print(f"  Error:     {error_pct:+.1f}%")

    print("\n" + "=" * 70)
    passed_count = sum(1 for *_, p in results if p)
    total = len(results)
    print(f"Results: {passed_count}/{total} within 15% error margin")

    # Check the 3-model requirement (7B/13B/70B)
    core_results = [(n, p) for n, q, c, e, m, ep, p in results if q == "Q4_K_M" and c == 4096]
    core_pass = sum(1 for _, p in core_results if p)
    print(f"Core models (Q4_K_M @ 4K): {core_pass}/{len(core_results)} passed")
    print("=" * 70)

    return passed_count == total


if __name__ == "__main__":
    import sys
    ok = run_benchmark()
    sys.exit(0 if ok else 1)

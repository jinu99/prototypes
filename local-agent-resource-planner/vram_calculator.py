"""VRAM usage calculator for LLM models.

Estimates memory requirements based on model architecture:
- Weight memory (model parameters × bits per weight)
- KV cache (key-value attention cache per context token)
- Activation memory (intermediate computation buffers)
- System overhead (CUDA context, memory allocator, etc.)
"""

import math

# System overhead constants (bytes)
CUDA_CONTEXT_OVERHEAD = 150 * 1024 * 1024  # ~150MB base CUDA context
PER_MODEL_OVERHEAD = 50 * 1024 * 1024  # ~50MB per loaded model
COMPUTE_BUFFER = 100 * 1024 * 1024  # ~100MB compute scratch buffer

# KV cache uses FP16 by default in llama.cpp
KV_CACHE_BYTES_PER_ELEMENT = 2  # FP16


def estimate_vram(model_info: dict, context_length: int = None,
                  batch_size: int = 512) -> dict:
    """Estimate VRAM usage for a single model.

    Returns dict with breakdown:
        weights_mb, kv_cache_mb, activation_mb, overhead_mb, total_mb
    """
    if context_length is None:
        context_length = model_info.get("context_length", 4096)

    d = model_info["embedding_length"]
    n_layers = model_info["block_count"]
    n_heads = model_info["head_count"]
    n_kv_heads = model_info.get("head_count_kv") or n_heads
    ffn = model_info.get("feed_forward_length", d * 4)
    vocab = model_info.get("vocab_size", 32000)
    bpw = model_info.get("bits_per_weight", 4.8)
    n_experts = model_info.get("expert_count", 0) or 1
    head_dim = d // n_heads if n_heads > 0 else 0

    # --- Weight Memory ---
    # Embedding layer
    embed_params = vocab * d
    # Output layer (often tied, but llama.cpp loads separately)
    output_params = vocab * d

    # Attention per layer: Q, K, V projections + O projection
    attn_per_layer = (d * n_heads * head_dim +  # Q
                      d * n_kv_heads * head_dim +  # K
                      d * n_kv_heads * head_dim +  # V
                      n_heads * head_dim * d)  # O

    # FFN per layer: gated = gate+up+down (3 proj), non-gated = up+down (2 proj)
    n_ffn_proj = model_info.get("ffn_projections", 3)
    ffn_per_layer = (d * ffn * n_ffn_proj) * n_experts

    # Layer norms: RMSNorm has d params per norm, 2 per layer + final
    norm_params = d * 2 * n_layers + d

    total_params = embed_params + output_params + (attn_per_layer + ffn_per_layer) * n_layers + norm_params
    weights_bytes = total_params * bpw / 8

    # --- KV Cache ---
    # Per layer: 2 (K+V) × n_kv_heads × head_dim × context_length × bytes
    kv_cache_bytes = (2 * n_kv_heads * head_dim * context_length
                      * KV_CACHE_BYTES_PER_ELEMENT * n_layers)

    # --- Activation Memory ---
    # Scratch buffer for intermediate computations
    # Approximation: largest single-layer activation
    activation_bytes = batch_size * d * 4  # FP32 for compute
    activation_bytes += batch_size * max(ffn, n_heads * head_dim) * 4

    # --- Overhead ---
    overhead_bytes = PER_MODEL_OVERHEAD + COMPUTE_BUFFER

    total_bytes = weights_bytes + kv_cache_bytes + activation_bytes + overhead_bytes

    mb = 1024 * 1024
    return {
        "model_name": model_info.get("name", "unknown"),
        "context_length": context_length,
        "total_params": total_params,
        "bits_per_weight": bpw,
        "weights_mb": weights_bytes / mb,
        "kv_cache_mb": kv_cache_bytes / mb,
        "activation_mb": activation_bytes / mb,
        "overhead_mb": overhead_bytes / mb,
        "total_mb": total_bytes / mb,
        "is_moe": (model_info.get("expert_count", 0) or 0) > 1,
        "expert_count": model_info.get("expert_count", 0) or 0,
        "expert_used_count": model_info.get("expert_used_count", 0) or 0,
    }


def estimate_moe_offloading(model_info: dict, context_length: int = None) -> list:
    """Estimate VRAM/RAM split for different MoE expert offloading options.

    Returns list of scenarios:
        - All experts in VRAM
        - Only active experts in VRAM, rest in RAM
        - Partial offloading options
    """
    n_experts = model_info.get("expert_count", 0) or 0
    n_active = model_info.get("expert_used_count", 0) or 0

    if n_experts <= 1:
        return []

    d = model_info["embedding_length"]
    n_layers = model_info["block_count"]
    ffn = model_info.get("feed_forward_length", d * 4)
    bpw = model_info.get("bits_per_weight", 4.8)

    # FFN params per expert per layer
    n_ffn_proj = model_info.get("ffn_projections", 3)
    ffn_per_expert = d * ffn * n_ffn_proj
    expert_bytes_per_layer = ffn_per_expert * bpw / 8
    total_expert_bytes = expert_bytes_per_layer * n_layers

    # Base model (non-expert parts)
    base_estimate = estimate_vram(model_info, context_length)
    non_expert_vram = base_estimate["total_mb"] - (total_expert_bytes * n_experts / (1024 * 1024))

    mb = 1024 * 1024
    scenarios = []

    for n_gpu_experts in range(n_active, n_experts + 1):
        n_ram_experts = n_experts - n_gpu_experts
        gpu_expert_mb = total_expert_bytes * n_gpu_experts / mb
        ram_expert_mb = total_expert_bytes * n_ram_experts / mb

        scenarios.append({
            "label": f"{n_gpu_experts}/{n_experts} experts in VRAM",
            "gpu_experts": n_gpu_experts,
            "ram_experts": n_ram_experts,
            "vram_mb": non_expert_vram + gpu_expert_mb,
            "ram_mb": ram_expert_mb,
            "note": _offload_note(n_gpu_experts, n_experts, n_active),
        })

    return scenarios


def _offload_note(n_gpu: int, n_total: int, n_active: int) -> str:
    if n_gpu == n_total:
        return "All experts in VRAM — fastest, no offloading latency"
    elif n_gpu == n_active:
        return "Only active experts in VRAM — minimum VRAM, RAM access for expert switching"
    elif n_gpu >= n_active:
        return f"{n_gpu - n_active} extra experts cached in VRAM — reduced expert switching latency"
    return "Below active expert count — performance will degrade"


def estimate_multi_model(models: list, vram_budget_mb: float = None) -> dict:
    """Estimate total VRAM for running multiple models simultaneously.

    Args:
        models: list of (model_info, context_length) tuples
        vram_budget_mb: optional VRAM budget to check feasibility

    Returns dict with per-model breakdown and totals.
    """
    results = []
    total_vram = CUDA_CONTEXT_OVERHEAD / (1024 * 1024)  # Shared CUDA context

    for model_info, ctx_len in models:
        est = estimate_vram(model_info, ctx_len)
        results.append(est)
        total_vram += est["total_mb"]

    feasible = True if vram_budget_mb is None else total_vram <= vram_budget_mb
    headroom = (vram_budget_mb - total_vram) if vram_budget_mb else None

    return {
        "models": results,
        "cuda_context_mb": CUDA_CONTEXT_OVERHEAD / (1024 * 1024),
        "total_vram_mb": total_vram,
        "vram_budget_mb": vram_budget_mb,
        "feasible": feasible,
        "headroom_mb": headroom,
    }


def grid_search_combinations(available_models: list, quant_options: list,
                             context_options: list, vram_budget_mb: float) -> list:
    """Find all feasible model×quantization×context combinations within VRAM budget.

    Args:
        available_models: list of base model profiles (without quantization)
        quant_options: list of (quant_name, bits_per_weight) tuples
        context_options: list of context lengths to try
        vram_budget_mb: VRAM budget in MB

    Returns list of feasible combinations sorted by total VRAM usage.
    """
    from itertools import product

    feasible = []

    for model_base in available_models:
        for quant_name, bpw in quant_options:
            for ctx_len in context_options:
                model_info = dict(model_base)
                model_info["bits_per_weight"] = bpw
                model_info["file_type"] = f"MOSTLY_{quant_name}"

                est = estimate_vram(model_info, ctx_len)
                if est["total_mb"] <= vram_budget_mb:
                    feasible.append({
                        "model_name": model_info["name"],
                        "quantization": quant_name,
                        "context_length": ctx_len,
                        "total_mb": est["total_mb"],
                        "weights_mb": est["weights_mb"],
                        "kv_cache_mb": est["kv_cache_mb"],
                    })

    feasible.sort(key=lambda x: x["total_mb"])
    return feasible


# Known llama.cpp reference values for validation
# Format: (model, quant, context) -> reported VRAM in MB
LLAMACPP_REFERENCE = {
    ("Llama 2 7B", "Q4_K_M", 2048): 5500,
    ("Llama 2 7B", "Q4_K_M", 4096): 6000,
    ("Llama 2 7B", "Q8_0", 4096): 9200,
    ("Llama 2 13B", "Q4_K_M", 2048): 9000,
    ("Llama 2 13B", "Q4_K_M", 4096): 9800,
    ("Mixtral 8x7B", "Q4_K_M", 4096): 26500,
    ("Phi-2", "Q8_0", 2048): 3400,
}

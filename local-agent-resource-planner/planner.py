"""Multi-model resource planner.

Orchestrates VRAM estimation across multiple models and provides
grid search for feasible combinations within a given VRAM budget.
"""

from gguf_parser import SAMPLE_PROFILES, GGUFParser, model_info_from_profile
from vram_calculator import (
    estimate_vram,
    estimate_multi_model,
    estimate_moe_offloading,
    grid_search_combinations,
    LLAMACPP_REFERENCE,
    CUDA_CONTEXT_OVERHEAD,
)

# Default quantization options for grid search
DEFAULT_QUANT_OPTIONS = [
    ("Q4_0", 4.5),
    ("Q4_K_M", 4.8),
    ("Q5_K_M", 5.7),
    ("Q6_K", 6.6),
    ("Q8_0", 8.5),
    ("F16", 16.0),
]

DEFAULT_CONTEXT_OPTIONS = [512, 1024, 2048, 4096, 8192, 16384, 32768]


def get_all_sample_models() -> list:
    """Return all sample model profiles as model_info dicts."""
    return [
        (key, model_info_from_profile(profile))
        for key, profile in SAMPLE_PROFILES.items()
    ]


def plan_single_model(model_key: str, context_length: int = None) -> dict:
    """Plan VRAM for a single model from sample profiles."""
    profile = SAMPLE_PROFILES.get(model_key)
    if not profile:
        raise ValueError(f"Unknown model: {model_key}. Available: {list(SAMPLE_PROFILES.keys())}")
    info = model_info_from_profile(profile)
    est = estimate_vram(info, context_length)

    result = {"estimate": est, "model_info": info}

    # Add MoE offloading info if applicable
    if (info.get("expert_count", 0) or 0) > 1:
        result["moe_offloading"] = estimate_moe_offloading(info, context_length)

    return result


def plan_multi_model(model_configs: list, vram_budget_mb: float = None) -> dict:
    """Plan VRAM for multiple simultaneous models.

    Args:
        model_configs: list of {"model_key": str, "context_length": int}
        vram_budget_mb: optional VRAM budget
    """
    models = []
    for cfg in model_configs:
        key = cfg["model_key"]
        ctx = cfg.get("context_length")
        profile = SAMPLE_PROFILES.get(key)
        if not profile:
            raise ValueError(f"Unknown model: {key}")
        info = model_info_from_profile(profile)
        ctx = ctx or info["context_length"]
        models.append((info, ctx))

    result = estimate_multi_model(models, vram_budget_mb)

    # Add MoE info for any MoE models
    moe_details = []
    for (info, ctx), est in zip(models, result["models"]):
        if (info.get("expert_count", 0) or 0) > 1:
            moe_details.append({
                "model_name": info["name"],
                "offloading_options": estimate_moe_offloading(info, ctx),
            })
    result["moe_details"] = moe_details

    return result


def plan_grid_search(model_keys: list, vram_budget_mb: float,
                     quant_options: list = None,
                     context_options: list = None) -> list:
    """Find feasible single-model configs within VRAM budget."""
    quant_options = quant_options or DEFAULT_QUANT_OPTIONS
    context_options = context_options or DEFAULT_CONTEXT_OPTIONS

    base_models = []
    for key in model_keys:
        profile = SAMPLE_PROFILES.get(key)
        if profile:
            base_models.append(model_info_from_profile(profile))

    return grid_search_combinations(base_models, quant_options,
                                    context_options, vram_budget_mb)


def validate_against_llamacpp() -> list:
    """Compare estimates against known llama.cpp reference values."""
    results = []

    ref_model_map = {
        "Llama 2 7B": "llama-7b-q4km",
        "Llama 2 13B": "llama-13b-q4km",
        "Mixtral 8x7B": "mixtral-8x7b-q4km",
        "Phi-2": "phi-2-q8",
    }

    quant_bpw = {
        "Q4_K_M": 4.8,
        "Q8_0": 8.5,
    }

    for (model_name, quant, ctx), ref_mb in LLAMACPP_REFERENCE.items():
        model_key = ref_model_map.get(model_name)
        if not model_key:
            continue

        profile = SAMPLE_PROFILES[model_key]
        info = model_info_from_profile(profile)

        # Override quantization if different
        if quant in quant_bpw:
            info["bits_per_weight"] = quant_bpw[quant]
            info["file_type"] = f"MOSTLY_{quant}"

        est = estimate_vram(info, ctx)
        estimated = est["total_mb"]
        error_pct = abs(estimated - ref_mb) / ref_mb * 100

        results.append({
            "model": model_name,
            "quantization": quant,
            "context_length": ctx,
            "estimated_mb": round(estimated, 1),
            "reference_mb": ref_mb,
            "error_percent": round(error_pct, 1),
            "within_20pct": error_pct <= 20,
        })

    return results


def plan_from_gguf(filepath: str, context_length: int = None) -> dict:
    """Parse a GGUF file and estimate VRAM."""
    parser = GGUFParser(filepath)
    info = parser.parse()
    est = estimate_vram(info, context_length)

    result = {"estimate": est, "model_info": info}

    if (info.get("expert_count", 0) or 0) > 1:
        result["moe_offloading"] = estimate_moe_offloading(info, context_length)

    return result

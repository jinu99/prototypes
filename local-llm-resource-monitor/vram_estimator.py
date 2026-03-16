"""VRAM estimation engine including KV cache calculations.

Formulas:
- Model weights VRAM = params_billion * 1e9 * bits_per_weight / 8
- KV cache per token = 2 * n_layers * n_kv_heads * head_dim * dtype_bytes
- KV cache total    = kv_per_token * context_length
- Total VRAM        = weights + kv_cache + overhead (CUDA kernels, activations ~500MB)
"""

from dataclasses import dataclass

# Known model architectures: (layers, heads, kv_heads, head_dim)
MODEL_ARCHITECTURES: dict[str, dict] = {
    "llama-7b":  {"params_b": 6.74,  "layers": 32, "heads": 32, "kv_heads": 32, "head_dim": 128},
    "llama-8b":  {"params_b": 8.03,  "layers": 32, "heads": 32, "kv_heads": 8,  "head_dim": 128},
    "llama-13b": {"params_b": 13.02, "layers": 40, "heads": 40, "kv_heads": 40, "head_dim": 128},
    "llama-14b": {"params_b": 14.8,  "layers": 40, "heads": 40, "kv_heads": 8,  "head_dim": 128},
    "llama-70b": {"params_b": 70.6,  "layers": 80, "heads": 64, "kv_heads": 8,  "head_dim": 128},
    "mistral-7b": {"params_b": 7.24, "layers": 32, "heads": 32, "kv_heads": 8,  "head_dim": 128},
    "qwen2-14b": {"params_b": 14.8,  "layers": 40, "heads": 40, "kv_heads": 8,  "head_dim": 128},
    "deepseek-7b": {"params_b": 7.6, "layers": 30, "heads": 32, "kv_heads": 32, "head_dim": 128},
}

# Quantization bits mapping
QUANT_BITS: dict[str, float] = {
    "F32": 32.0, "F16": 16.0, "BF16": 16.0,
    "Q8_0": 8.0, "Q6_K": 6.5, "Q5_K_M": 5.5, "Q5_K_S": 5.25,
    "Q4_K_M": 4.85, "Q4_K_S": 4.5, "Q4_0": 4.0,
    "Q3_K_M": 3.9, "Q3_K_S": 3.5, "Q2_K": 2.8,
    "IQ4_XS": 4.3, "IQ3_M": 3.4, "IQ2_M": 2.7,
}

CUDA_OVERHEAD_MB = 500  # CUDA context, kernels, activations


@dataclass
class VramEstimate:
    model_name: str
    params_b: float
    quant: str
    bits_per_weight: float
    context_length: int
    weights_mb: float
    kv_cache_mb: float
    overhead_mb: float
    total_mb: float

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "params_b": self.params_b,
            "quant": self.quant,
            "bits_per_weight": self.bits_per_weight,
            "context_length": self.context_length,
            "weights_mb": round(self.weights_mb, 1),
            "kv_cache_mb": round(self.kv_cache_mb, 1),
            "overhead_mb": round(self.overhead_mb, 1),
            "total_mb": round(self.total_mb, 1),
            "total_gb": round(self.total_mb / 1024, 2),
        }


def resolve_architecture(model_name: str) -> dict | None:
    """Try to match a model name to a known architecture."""
    name_lower = model_name.lower()
    # Direct match
    if name_lower in MODEL_ARCHITECTURES:
        return MODEL_ARCHITECTURES[name_lower]
    # Fuzzy match by keyword
    for key, arch in MODEL_ARCHITECTURES.items():
        parts = key.split("-")
        family = parts[0]
        size = parts[1] if len(parts) > 1 else ""
        if family in name_lower and size in name_lower:
            return arch
    return None


def resolve_quant_bits(quant: str) -> float:
    """Resolve quantization string to bits per weight."""
    quant_upper = quant.upper().replace(" ", "_")
    if quant_upper in QUANT_BITS:
        return QUANT_BITS[quant_upper]
    # Try partial match
    for key, bits in QUANT_BITS.items():
        if key in quant_upper or quant_upper in key:
            return bits
    return 4.85  # default to Q4_K_M


def estimate_vram(
    params_b: float,
    quant: str = "Q4_K_M",
    context_length: int = 4096,
    n_layers: int | None = None,
    n_kv_heads: int | None = None,
    head_dim: int = 128,
    model_name: str = "custom",
) -> VramEstimate:
    """Estimate total VRAM usage including KV cache.

    Args:
        params_b: Model parameters in billions
        quant: Quantization level (e.g. "Q4_K_M", "F16")
        context_length: Context window size in tokens
        n_layers: Number of transformer layers (auto-detected if possible)
        n_kv_heads: Number of KV attention heads (auto-detected if possible)
        head_dim: Dimension per attention head (usually 128)
        model_name: Model identifier for architecture lookup
    """
    bits = resolve_quant_bits(quant)

    # Try to auto-fill architecture params
    arch = resolve_architecture(model_name)
    if arch:
        if n_layers is None:
            n_layers = arch["layers"]
        if n_kv_heads is None:
            n_kv_heads = arch["kv_heads"]
        if model_name == "custom":
            model_name = next(
                (k for k, v in MODEL_ARCHITECTURES.items() if v == arch), model_name
            )

    # Fallback heuristics if no architecture found
    if n_layers is None:
        n_layers = int(params_b * 4.5)  # rough heuristic
    if n_kv_heads is None:
        n_kv_heads = 8 if params_b > 20 else 32  # GQA for large models

    # Model weights
    weights_bytes = params_b * 1e9 * bits / 8
    weights_mb = weights_bytes / (1024**2)

    # KV cache: 2 (K+V) * layers * kv_heads * head_dim * ctx_len * 2 bytes (FP16)
    kv_per_token = 2 * n_layers * n_kv_heads * head_dim * 2  # bytes
    kv_cache_bytes = kv_per_token * context_length
    kv_cache_mb = kv_cache_bytes / (1024**2)

    total_mb = weights_mb + kv_cache_mb + CUDA_OVERHEAD_MB

    return VramEstimate(
        model_name=model_name,
        params_b=params_b,
        quant=quant,
        bits_per_weight=bits,
        context_length=context_length,
        weights_mb=weights_mb,
        kv_cache_mb=kv_cache_mb,
        overhead_mb=CUDA_OVERHEAD_MB,
        total_mb=total_mb,
    )


@dataclass
class LoadFeasibility:
    can_load: bool
    available_mb: float
    required_mb: float
    margin_mb: float
    verdict: str  # "GO" or "NO-GO"
    detail: str

    def to_dict(self) -> dict:
        return {
            "can_load": self.can_load,
            "available_mb": round(self.available_mb, 1),
            "required_mb": round(self.required_mb, 1),
            "margin_mb": round(self.margin_mb, 1),
            "verdict": self.verdict,
            "detail": self.detail,
        }


def check_load_feasibility(
    available_vram_mb: float,
    estimate: VramEstimate,
    safety_margin_pct: float = 5.0,
) -> LoadFeasibility:
    """Check if a model can be loaded given available VRAM."""
    safety_mb = estimate.total_mb * safety_margin_pct / 100
    required_with_safety = estimate.total_mb + safety_mb
    margin = available_vram_mb - required_with_safety
    can_load = margin >= 0

    if can_load:
        detail = f"{estimate.total_mb:.0f}MB required + {safety_mb:.0f}MB safety margin = {required_with_safety:.0f}MB. Available: {available_vram_mb:.0f}MB. Headroom: {margin:.0f}MB."
    else:
        detail = f"{estimate.total_mb:.0f}MB required + {safety_mb:.0f}MB safety margin = {required_with_safety:.0f}MB. Available: {available_vram_mb:.0f}MB. Short by {-margin:.0f}MB."

    return LoadFeasibility(
        can_load=can_load,
        available_mb=available_vram_mb,
        required_mb=required_with_safety,
        margin_mb=margin,
        verdict="GO" if can_load else "NO-GO",
        detail=detail,
    )


# Convenience: preset models for quick estimation
PRESET_MODELS = [
    {"name": "LLaMA 3.1 8B Q4_K_M", "model_name": "llama-8b", "params_b": 8.03, "quant": "Q4_K_M"},
    {"name": "LLaMA 3.1 8B F16", "model_name": "llama-8b", "params_b": 8.03, "quant": "F16"},
    {"name": "CodeLlama 13B Q4_K_M", "model_name": "llama-13b", "params_b": 13.02, "quant": "Q4_K_M"},
    {"name": "LLaMA 3.1 70B Q4_K_M", "model_name": "llama-70b", "params_b": 70.6, "quant": "Q4_K_M"},
    {"name": "Mistral 7B Q4_K_M", "model_name": "mistral-7b", "params_b": 7.24, "quant": "Q4_K_M"},
    {"name": "Qwen2.5 14B Q4_K_M", "model_name": "qwen2-14b", "params_b": 14.8, "quant": "Q4_K_M"},
    {"name": "DeepSeek-R1 7B Q4_K_M", "model_name": "deepseek-7b", "params_b": 7.6, "quant": "Q4_K_M"},
]

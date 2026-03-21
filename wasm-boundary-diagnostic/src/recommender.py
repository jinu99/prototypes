"""Optimization recommendations for high-cost boundary functions."""

from dataclasses import dataclass

from .cost_model import CostLevel, FunctionCost


@dataclass
class Recommendation:
    pattern: str       # e.g. "opaque_handle", "serde_wasm_bindgen", "batch"
    title: str
    description: str
    applies_when: str  # human-readable condition


# All known optimization patterns
PATTERNS: list[Recommendation] = [
    Recommendation(
        pattern="opaque_handle",
        title="Use Opaque Handle Instead of Serialization",
        description=(
            "Instead of passing serialized data (String/Vec<u8>) across the boundary, "
            "keep the data on the WASM side and return an integer handle (pointer/index). "
            "JS only holds the handle and calls WASM methods to operate on it. "
            "This eliminates serialization entirely for intermediate operations."
        ),
        applies_when="Function takes or returns String/Vec<u8> that represents structured data",
    ),
    Recommendation(
        pattern="serde_wasm_bindgen",
        title="Use serde-wasm-bindgen for Structured Data",
        description=(
            "Replace manual String JSON serialization with `serde-wasm-bindgen`, which "
            "converts Rust structs directly to/from JsValue without going through a "
            "JSON string intermediate. This avoids the UTF-8 encode/decode overhead "
            "and uses the structured clone algorithm instead."
        ),
        applies_when="Function serializes structured data as JSON strings across the boundary",
    ),
    Recommendation(
        pattern="batch_processing",
        title="Batch Multiple Calls into One Boundary Crossing",
        description=(
            "If this function is called in a loop or with multiple items, combine "
            "the calls into a single boundary crossing. Pass an array/buffer of "
            "inputs and process them all on the WASM side. Each boundary crossing "
            "has fixed overhead, so batching amortizes it."
        ),
        applies_when="Function processes individual items that could be batched",
    ),
    Recommendation(
        pattern="typed_array",
        title="Use TypedArray View Instead of Copying",
        description=(
            "Instead of copying byte arrays across the boundary, create a TypedArray "
            "view directly into WASM linear memory. This gives JS zero-copy access "
            "to WASM data. Caveat: the view is invalidated if WASM memory grows."
        ),
        applies_when="Function copies byte arrays (Vec<u8>) across the boundary",
    ),
    Recommendation(
        pattern="cache_boundary",
        title="Cache Results to Reduce Boundary Crossings",
        description=(
            "If this function returns data that doesn't change frequently, cache "
            "the result on the JS side to avoid repeated boundary crossings. "
            "Especially important for String returns which involve malloc + UTF-8 decode."
        ),
        applies_when="Function returns String/structured data that could be cached",
    ),
]


def get_recommendations(cost: FunctionCost) -> list[Recommendation]:
    """Get applicable optimization recommendations for a function."""
    if cost.overall in (CostLevel.ZERO, CostLevel.LOW):
        return []

    recs: list[Recommendation] = []
    has_string = _has_type(cost, "string") or _has_type(cost, "string_ptr")
    has_bytes = _has_type(cost, "bytes") or _has_type(cost, "bytes_ptr")
    has_jsvalue_array = _has_type(cost, "jsvalue_array")
    has_jsvalue = _has_type(cost, "jsvalue")
    returns_string = cost.function.return_type == "string"

    # Opaque handle: when passing structured data as String/bytes
    if has_string or has_bytes:
        recs.append(_find_pattern("opaque_handle"))

    # serde-wasm-bindgen: when using String for structured data
    if has_string or (has_jsvalue and has_string):
        recs.append(_find_pattern("serde_wasm_bindgen"))

    # Batch processing: when there's an array parameter or multiple costly params
    if has_jsvalue_array or _count_costly_params(cost) >= 2:
        recs.append(_find_pattern("batch_processing"))

    # TypedArray view: when copying byte arrays
    if has_bytes:
        recs.append(_find_pattern("typed_array"))

    # Cache: when returning strings or jsvalues
    if returns_string or cost.function.return_type == "jsvalue":
        recs.append(_find_pattern("cache_boundary"))

    return recs


def _has_type(cost: FunctionCost, type_name: str) -> bool:
    """Check if any param or return has the given type."""
    for pc in cost.param_costs:
        if pc.param.inferred_type == type_name:
            return True
    return cost.function.return_type == type_name


def _count_costly_params(cost: FunctionCost) -> int:
    """Count params with medium or high cost."""
    return sum(
        1 for pc in cost.param_costs
        if pc.level in (CostLevel.MEDIUM, CostLevel.HIGH)
    )


def _find_pattern(name: str) -> Recommendation:
    """Find a recommendation pattern by name."""
    for p in PATTERNS:
        if p.pattern == name:
            return p
    raise ValueError(f"Unknown pattern: {name}")

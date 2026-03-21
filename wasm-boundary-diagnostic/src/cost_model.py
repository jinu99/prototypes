"""Cost model for JS↔WASM boundary serialization."""

from dataclasses import dataclass
from enum import Enum

from .parser import BoundaryFunction, BoundaryParam


class CostLevel(str, Enum):
    ZERO = "zero"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ParamCost:
    param: BoundaryParam
    level: CostLevel
    reason: str


@dataclass
class FunctionCost:
    function: BoundaryFunction
    param_costs: list[ParamCost]
    return_cost: CostLevel
    return_reason: str
    overall: CostLevel
    total_score: int  # numeric score for sorting


# Type → (cost level, reason, numeric score)
TYPE_COSTS: dict[str, tuple[CostLevel, str, int]] = {
    "i32": (CostLevel.ZERO, "Raw numeric — direct WASM ABI, no serialization", 0),
    "f32": (CostLevel.ZERO, "Raw float — direct WASM ABI, no serialization", 0),
    "f64": (CostLevel.ZERO, "Raw float64 — direct WASM ABI, no serialization", 0),
    "string": (CostLevel.HIGH, "String — UTF-8 encode/decode + malloc + memory copy", 10),
    "bytes": (CostLevel.MEDIUM, "Byte array — malloc + memory copy (no encoding)", 5),
    "jsvalue": (CostLevel.LOW, "JsValue — heap slot allocation (O(1) but ref-counted)", 2),
    "jsvalue_array": (CostLevel.HIGH, "JsValue array — per-element heap allocation + malloc", 12),
    "void": (CostLevel.ZERO, "No return value", 0),
    "string_ptr": (CostLevel.HIGH, "String ptr — part of ptr+len pair for string decoding", 5),
    "string_len": (CostLevel.ZERO, "String len — paired with string ptr", 0),
    "bytes_ptr": (CostLevel.MEDIUM, "Bytes ptr — part of ptr+len pair for byte array", 3),
    "bytes_len": (CostLevel.ZERO, "Bytes len — paired with bytes ptr", 0),
    "unknown": (CostLevel.LOW, "Unknown type — assumed low cost", 1),
}


def analyze_function(func: BoundaryFunction) -> FunctionCost:
    """Compute cost analysis for a single boundary function."""
    param_costs = []
    total = 0

    for param in func.params:
        level, reason, score = TYPE_COSTS.get(
            param.inferred_type,
            (CostLevel.LOW, f"Unknown type '{param.inferred_type}'", 1),
        )
        param_costs.append(ParamCost(param=param, level=level, reason=reason))
        total += score

    ret_level, ret_reason, ret_score = TYPE_COSTS.get(
        func.return_type,
        (CostLevel.LOW, "Unknown return type", 1),
    )
    total += ret_score

    # Overall cost based on total score
    if total == 0:
        overall = CostLevel.ZERO
    elif total <= 2:
        overall = CostLevel.LOW
    elif total <= 10:
        overall = CostLevel.MEDIUM
    else:
        overall = CostLevel.HIGH

    return FunctionCost(
        function=func,
        param_costs=param_costs,
        return_cost=ret_level,
        return_reason=ret_reason,
        overall=overall,
        total_score=total,
    )


def analyze_all(functions: list[BoundaryFunction]) -> list[FunctionCost]:
    """Analyze all boundary functions, sorted by cost (highest first)."""
    results = [analyze_function(f) for f in functions]
    results.sort(key=lambda r: r.total_score, reverse=True)
    return results

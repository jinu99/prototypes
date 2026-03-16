"""Parse LoRA adapter config and map adapter keys to base model keys.

A typical adapter_config.json contains:
  - r: LoRA rank
  - lora_alpha: scaling factor
  - target_modules: list of module names (e.g., ["q_proj", "v_proj"])

Adapter tensor naming convention (PEFT):
  base_model.model.{base_key}.lora_A.weight
  base_model.model.{base_key}.lora_B.weight
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from safetensors import safe_open


@dataclass
class AdapterConfig:
    rank: int
    alpha: int
    target_modules: list[str]
    scaling: float  # alpha / rank


@dataclass
class LoraLayer:
    base_key: str  # e.g., "model.layers.0.self_attn.q_proj.weight"
    lora_a_key: str  # key in adapter safetensors
    lora_b_key: str
    scaling: float


def load_adapter_config(adapter_dir: Path) -> AdapterConfig:
    config_path = adapter_dir / "adapter_config.json"
    raw = json.loads(config_path.read_text())
    rank = raw["r"]
    alpha = raw["lora_alpha"]
    return AdapterConfig(
        rank=rank,
        alpha=alpha,
        target_modules=raw["target_modules"],
        scaling=alpha / rank,
    )


def map_adapter_to_base(
    adapter_dir: Path, base_keys: set[str]
) -> list[LoraLayer]:
    """Map each LoRA A/B pair in the adapter to its corresponding base key.

    The adapter tensor key is like:
      base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight
    The base model key is:
      model.layers.0.self_attn.q_proj.weight
    """
    config = load_adapter_config(adapter_dir)
    adapter_path = adapter_dir / "adapter_model.safetensors"

    with safe_open(str(adapter_path), framework="pt") as f:
        adapter_keys = list(f.keys())

    # Group by base key: find all lora_A keys, derive lora_B and base key
    lora_a_pattern = re.compile(r"(.+)\.lora_A\.weight$")
    layers = []

    for key in adapter_keys:
        m = lora_a_pattern.match(key)
        if not m:
            continue

        adapter_prefix = m.group(1)  # e.g., base_model.model.model.layers.0.self_attn.q_proj
        lora_b_key = f"{adapter_prefix}.lora_B.weight"

        # Strip "base_model.model." prefix to get base key
        base_prefix = adapter_prefix
        if base_prefix.startswith("base_model.model."):
            base_prefix = base_prefix[len("base_model.model."):]

        base_key = f"{base_prefix}.weight"

        if base_key not in base_keys:
            continue  # Skip keys not in the base model

        layers.append(LoraLayer(
            base_key=base_key,
            lora_a_key=key,
            lora_b_key=lora_b_key,
            scaling=config.scaling,
        ))

    return layers

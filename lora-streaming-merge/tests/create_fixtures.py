"""Generate fake model shards + LoRA adapter for testing.

Creates a small model that mimics the structure of a real LLaMA-like model:
- 2 safetensors shards (like 70B model's model-00001-of-00002.safetensors)
- LoRA adapter with adapter_config.json + adapter_model.safetensors
"""

import json
import os
from pathlib import Path

import torch
from safetensors.torch import save_file


NUM_LAYERS = 4
HIDDEN_SIZE = 64
INTERMEDIATE_SIZE = 128  # FFN intermediate
LORA_RANK = 8
LORA_ALPHA = 16

# Which modules LoRA targets (mimics real adapter_config.json)
TARGET_MODULES = ["q_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def create_base_model(output_dir: Path) -> None:
    """Create a fake base model split into 2 shards."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build all tensors
    tensors_by_layer: dict[int, dict[str, torch.Tensor]] = {}
    for i in range(NUM_LAYERS):
        prefix = f"model.layers.{i}.self_attn"
        ffn_prefix = f"model.layers.{i}.mlp"
        tensors_by_layer[i] = {
            f"{prefix}.q_proj.weight": torch.randn(HIDDEN_SIZE, HIDDEN_SIZE),
            f"{prefix}.k_proj.weight": torch.randn(HIDDEN_SIZE, HIDDEN_SIZE),
            f"{prefix}.v_proj.weight": torch.randn(HIDDEN_SIZE, HIDDEN_SIZE),
            f"{prefix}.o_proj.weight": torch.randn(HIDDEN_SIZE, HIDDEN_SIZE),
            f"{ffn_prefix}.gate_proj.weight": torch.randn(INTERMEDIATE_SIZE, HIDDEN_SIZE),
            f"{ffn_prefix}.up_proj.weight": torch.randn(INTERMEDIATE_SIZE, HIDDEN_SIZE),
            f"{ffn_prefix}.down_proj.weight": torch.randn(HIDDEN_SIZE, INTERMEDIATE_SIZE),
        }

    # Split into 2 shards: layers 0-1 in shard 1, layers 2-3 in shard 2
    shard1 = {}
    shard2 = {}
    for i in range(NUM_LAYERS):
        target = shard1 if i < NUM_LAYERS // 2 else shard2
        target.update(tensors_by_layer[i])

    # Add embed_tokens to shard1, lm_head to shard2
    shard1["model.embed_tokens.weight"] = torch.randn(100, HIDDEN_SIZE)
    shard2["lm_head.weight"] = torch.randn(100, HIDDEN_SIZE)

    save_file(shard1, output_dir / "model-00001-of-00002.safetensors")
    save_file(shard2, output_dir / "model-00002-of-00002.safetensors")

    # Create model.safetensors.index.json (weight map)
    weight_map = {}
    for key in shard1:
        weight_map[key] = "model-00001-of-00002.safetensors"
    for key in shard2:
        weight_map[key] = "model-00002-of-00002.safetensors"

    index = {
        "metadata": {"total_size": sum(t.numel() * 4 for t in {**shard1, **shard2}.values())},
        "weight_map": weight_map,
    }
    (output_dir / "model.safetensors.index.json").write_text(json.dumps(index, indent=2))


def create_lora_adapter(output_dir: Path) -> None:
    """Create a fake LoRA adapter."""
    output_dir.mkdir(parents=True, exist_ok=True)

    tensors = {}
    for i in range(NUM_LAYERS):
        for module in TARGET_MODULES:
            if module in ("gate_proj", "up_proj"):
                in_dim, out_dim = HIDDEN_SIZE, INTERMEDIATE_SIZE
            elif module == "down_proj":
                in_dim, out_dim = INTERMEDIATE_SIZE, HIDDEN_SIZE
            else:
                in_dim, out_dim = HIDDEN_SIZE, HIDDEN_SIZE

            prefix = f"base_model.model.model.layers.{i}"
            if module in ("q_proj", "k_proj", "v_proj", "o_proj"):
                prefix += f".self_attn.{module}"
            else:
                prefix += f".mlp.{module}"

            # LoRA A: (rank, in_features), LoRA B: (out_features, rank)
            tensors[f"{prefix}.lora_A.weight"] = torch.randn(LORA_RANK, in_dim)
            tensors[f"{prefix}.lora_B.weight"] = torch.randn(out_dim, LORA_RANK)

    save_file(tensors, output_dir / "adapter_model.safetensors")

    config = {
        "base_model_name_or_path": "fake-model",
        "bias": "none",
        "fan_in_fan_out": False,
        "lora_alpha": LORA_ALPHA,
        "lora_dropout": 0.0,
        "r": LORA_RANK,
        "target_modules": TARGET_MODULES,
        "task_type": "CAUSAL_LM",
    }
    (output_dir / "adapter_config.json").write_text(json.dumps(config, indent=2))


def main() -> None:
    fixtures = Path(__file__).parent / "fixtures"
    if fixtures.exists():
        import shutil
        shutil.rmtree(fixtures)

    create_base_model(fixtures / "base_model")
    create_lora_adapter(fixtures / "adapter")
    print(f"Fixtures created in {fixtures}")

    # Print sizes for reference
    for p in sorted(fixtures.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(fixtures)}: {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

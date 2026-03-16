"""Verify streaming merge results against a naive full-memory merge.

The naive merge loads the entire model + adapter into memory and applies
LoRA the same way PEFT's merge_and_unload does. Then we compare tensor-by-tensor
with allclose(rtol=1e-5).
"""

from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file

from .adapter import map_adapter_to_base
from .shard_map import build_shard_map


@torch.no_grad()
def naive_merge(base_dir: Path, adapter_dir: Path) -> dict[str, torch.Tensor]:
    """Full-memory merge (reference implementation, like PEFT merge_and_unload)."""
    shard_map = build_shard_map(base_dir)
    base_keys = set(shard_map.keys())
    lora_layers = map_adapter_to_base(adapter_dir, base_keys)
    lora_by_base = {ll.base_key: ll for ll in lora_layers}

    adapter_path = adapter_dir / "adapter_model.safetensors"
    adapter_handle = safe_open(str(adapter_path), framework="pt")

    # Load ALL base tensors into memory
    all_tensors = {}
    opened_files: dict[str, object] = {}

    for key, shard_path in shard_map.items():
        sp = str(shard_path)
        if sp not in opened_files:
            opened_files[sp] = safe_open(sp, framework="pt")
        all_tensors[key] = opened_files[sp].get_tensor(key)

    # Apply LoRA to all targets
    for key, ll in lora_by_base.items():
        lora_a = adapter_handle.get_tensor(ll.lora_a_key)
        lora_b = adapter_handle.get_tensor(ll.lora_b_key)
        all_tensors[key] = all_tensors[key] + ll.scaling * (lora_b @ lora_a)

    return all_tensors


def verify_merge(
    output_dir: Path,
    reference: dict[str, torch.Tensor],
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> tuple[bool, list[str]]:
    """Compare streaming merge output against reference tensors.

    Returns (all_passed, list_of_failure_messages).
    """
    # Load merged tensors from output
    merged = {}
    for sf in sorted(output_dir.glob("*.safetensors")):
        with safe_open(str(sf), framework="pt") as f:
            for key in f.keys():
                merged[key] = f.get_tensor(key)

    failures = []

    # Check all reference keys exist
    for key in reference:
        if key not in merged:
            failures.append(f"MISSING: {key}")
            continue

        if not torch.allclose(merged[key], reference[key], rtol=rtol, atol=atol):
            diff = (merged[key] - reference[key]).abs()
            failures.append(
                f"MISMATCH: {key} — max_diff={diff.max().item():.2e}, "
                f"mean_diff={diff.mean().item():.2e}"
            )

    # Check for extra keys
    for key in merged:
        if key not in reference:
            failures.append(f"EXTRA: {key}")

    return len(failures) == 0, failures

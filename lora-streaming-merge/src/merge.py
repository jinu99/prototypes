"""Core streaming LoRA merge: load one tensor at a time, apply LoRA, save.

The key insight: safetensors safe_open + get_tensor() loads only the
requested tensor into memory. We write each tensor to its own small shard,
so peak RAM stays proportional to a single tensor, not the whole model.

Merge formula: W' = W + scaling * (B @ A)
  where W is base weight, A is lora_A, B is lora_B, scaling = alpha/rank
"""

import json
import tracemalloc
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file
from tqdm import tqdm

from .adapter import LoraLayer, map_adapter_to_base
from .shard_map import build_shard_map, get_shard_files

# Default: 1 tensor per output shard for minimal memory
DEFAULT_BATCH_SIZE = 1


@torch.no_grad()
def streaming_merge(
    base_dir: Path,
    adapter_dir: Path,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    verbose: bool = True,
) -> dict:
    """Perform tensor-by-tensor streaming LoRA merge.

    Processes tensors in small batches (batch_size at a time),
    writes each batch to its own output shard, then frees memory.
    This ensures peak RAM ~ batch_size * max_tensor_size.

    Returns a stats dict with peak memory, tensor counts, etc.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track memory
    tracemalloc.start()

    # Build mappings
    shard_map = build_shard_map(base_dir)
    base_keys = set(shard_map.keys())
    lora_layers = map_adapter_to_base(adapter_dir, base_keys)
    lora_by_base = {ll.base_key: ll for ll in lora_layers}

    # Open adapter file once (lazy, no full load)
    adapter_path = adapter_dir / "adapter_model.safetensors"
    adapter_handle = safe_open(str(adapter_path), framework="pt")

    # Collect all keys in deterministic order, grouped by source shard
    shard_files = get_shard_files(shard_map)
    all_keys_ordered = []
    for sf in shard_files:
        keys = [k for k, v in shard_map.items() if v == sf]
        keys.sort()  # deterministic order within shard
        all_keys_ordered.extend(keys)

    # Open handles for each source shard (lazy, no memory cost)
    source_handles: dict[str, object] = {}
    for sf in shard_files:
        source_handles[str(sf)] = safe_open(str(sf), framework="pt")

    total_tensors = len(all_keys_ordered)
    merged_count = 0
    peak_mem = 0
    output_shard_idx = 0
    weight_map = {}  # for output index.json

    pbar = tqdm(total=total_tensors, desc="Merging", disable=not verbose)

    # Process in small batches
    for batch_start in range(0, total_tensors, batch_size):
        batch_keys = all_keys_ordered[batch_start:batch_start + batch_size]
        batch_tensors = {}

        for key in batch_keys:
            # Load base tensor from its source shard
            source_path = str(shard_map[key])
            w = source_handles[source_path].get_tensor(key)

            if key in lora_by_base:
                ll = lora_by_base[key]
                lora_a = adapter_handle.get_tensor(ll.lora_a_key)
                lora_b = adapter_handle.get_tensor(ll.lora_b_key)

                # W' = W + scaling * (B @ A)
                w = w + ll.scaling * (lora_b @ lora_a)
                merged_count += 1
                del lora_a, lora_b

            batch_tensors[key] = w

            # Track peak memory after each tensor
            _, peak = tracemalloc.get_traced_memory()
            peak_mem = max(peak_mem, peak)

            pbar.update(1)

        # Write this batch to its own shard
        output_shard_idx += 1
        num_shards_placeholder = "PLACEHOLDER"
        shard_name = f"model-{output_shard_idx:05d}-of-{num_shards_placeholder}.safetensors"
        save_file(batch_tensors, output_dir / shard_name)

        for key in batch_keys:
            weight_map[key] = shard_name

        # Free batch memory
        del batch_tensors

    pbar.close()

    # Close handles
    del adapter_handle
    source_handles.clear()

    # Rename shard files with correct total count
    total_shards = output_shard_idx
    final_weight_map = {}
    for key, old_name in weight_map.items():
        new_name = old_name.replace(num_shards_placeholder, f"{total_shards:05d}")
        final_weight_map[key] = new_name

    for i in range(1, total_shards + 1):
        old_name = f"model-{i:05d}-of-{num_shards_placeholder}.safetensors"
        new_name = f"model-{i:05d}-of-{total_shards:05d}.safetensors"
        (output_dir / old_name).rename(output_dir / new_name)

    # Write output index
    total_size = sum(f.stat().st_size for f in output_dir.glob("*.safetensors"))
    index = {
        "metadata": {"total_size": total_size},
        "weight_map": final_weight_map,
    }
    (output_dir / "model.safetensors.index.json").write_text(
        json.dumps(index, indent=2)
    )

    _, final_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mem = max(peak_mem, final_peak)

    stats = {
        "total_tensors": total_tensors,
        "merged_tensors": merged_count,
        "output_shards": total_shards,
        "peak_mem_bytes": peak_mem,
        "peak_mem_mb": peak_mem / (1024 * 1024),
        "total_model_bytes": total_size,
        "total_model_mb": total_size / (1024 * 1024),
        "output_dir": str(output_dir),
    }

    if verbose:
        print(f"\nDone! Merged {merged_count}/{total_tensors} tensors → {total_shards} shards")
        print(f"Peak RAM:      {stats['peak_mem_mb']:.1f} MB")
        print(f"Output size:   {stats['total_model_mb']:.1f} MB")
        print(f"RAM savings:   {(1 - stats['peak_mem_mb'] / stats['total_model_mb']) * 100:.0f}% vs full load")
        print(f"Output:        {output_dir}")

    return stats

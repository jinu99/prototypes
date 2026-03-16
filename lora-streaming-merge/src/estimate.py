"""Pre-merge estimation: predict peak RAM, disk usage, and time.

Reads tensor metadata (shapes, dtypes) without loading actual data
to estimate resource requirements. Reflects the true streaming approach
where we process one tensor at a time.
"""

from pathlib import Path

from safetensors import safe_open

from .adapter import load_adapter_config, map_adapter_to_base
from .shard_map import build_shard_map, get_shard_files

DTYPE_SIZES = {
    "F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I16": 2, "I8": 1,
}

# Empirical: ~50 MB/s for safetensors read+write on NVMe SSD
THROUGHPUT_MBS = 50.0


def _tensor_bytes(f, key: str) -> int:
    shape = f.get_slice(key).get_shape()
    dtype_str = str(f.get_slice(key).get_dtype())
    elem_size = DTYPE_SIZES.get(dtype_str, 4)
    result = elem_size
    for d in shape:
        result *= d
    return result


def estimate_merge(base_dir: Path, adapter_dir: Path, batch_size: int = 1) -> dict:
    """Estimate resources needed for streaming merge without loading tensors."""
    shard_map = build_shard_map(base_dir)
    base_keys = set(shard_map.keys())
    lora_layers = map_adapter_to_base(adapter_dir, base_keys)
    lora_by_base = {ll.base_key: ll for ll in lora_layers}
    config = load_adapter_config(adapter_dir)

    shard_files = get_shard_files(shard_map)
    keys_by_shard: dict[Path, list[str]] = {sf: [] for sf in shard_files}
    for key, sf in shard_map.items():
        keys_by_shard[sf].append(key)

    # Per-tensor analysis
    tensor_sizes = []  # (key, bytes, is_lora_target, merge_step_bytes)
    total_disk = 0
    max_single_step = 0

    for shard_file in shard_files:
        keys = keys_by_shard[shard_file]
        with safe_open(str(shard_file), framework="pt", device="cpu") as f:
            for key in keys:
                tb = _tensor_bytes(f, key)
                total_disk += tb

                if key in lora_by_base:
                    shape = f.get_slice(key).get_shape()
                    dtype_str = str(f.get_slice(key).get_dtype())
                    elem_size = DTYPE_SIZES.get(dtype_str, 4)
                    lora_a_bytes = config.rank * shape[-1] * elem_size
                    lora_b_bytes = shape[0] * config.rank * elem_size
                    # During merge: base + A + B + result (in-place reuse possible but conservative)
                    step_mem = tb + lora_a_bytes + lora_b_bytes + tb
                    tensor_sizes.append((key, tb, True, step_mem))
                else:
                    tensor_sizes.append((key, tb, False, tb))

                max_single_step = max(max_single_step, tensor_sizes[-1][3])

    # Peak RAM = max across batches of batch_size tensors
    # In a batch, all tensors are held in memory simultaneously before save
    sorted_sizes = sorted([t[1] for t in tensor_sizes], reverse=True)
    batch_peak = sum(sorted_sizes[:batch_size])
    peak_ram = max(batch_peak, max_single_step)

    # Per-shard summary
    shard_reports = []
    for shard_file in shard_files:
        keys = keys_by_shard[shard_file]
        shard_size = sum(t[1] for t in tensor_sizes if t[0] in keys)
        shard_reports.append({
            "file": shard_file.name,
            "num_tensors": len(keys),
            "shard_size_mb": shard_size / (1024 ** 2),
        })

    time_seconds = (total_disk * 2) / (THROUGHPUT_MBS * 1024 * 1024)

    return {
        "total_tensors": len(shard_map),
        "merge_targets": len(lora_layers),
        "lora_rank": config.rank,
        "lora_alpha": config.alpha,
        "scaling": config.scaling,
        "num_shards": len(shard_files),
        "batch_size": batch_size,
        "per_shard": shard_reports,
        "peak_ram_mb": peak_ram / (1024 ** 2),
        "total_disk_mb": total_disk / (1024 ** 2),
        "estimated_time_s": time_seconds,
    }


def format_report(est: dict) -> str:
    """Format estimation as a human-readable report."""
    lines = [
        "═══ LoRA Merge Estimation Report ═══",
        "",
        f"  Base model:    {est['num_shards']} shard(s), {est['total_tensors']} tensors",
        f"  LoRA targets:  {est['merge_targets']} tensors (rank={est['lora_rank']}, alpha={est['lora_alpha']}, scaling={est['scaling']:.2f})",
        f"  Batch size:    {est['batch_size']} tensor(s) per output shard",
        "",
        "─── Source Shards ───",
    ]

    for sr in est["per_shard"]:
        lines.append(
            f"  {sr['file']}: {sr['num_tensors']} tensors, "
            f"{sr['shard_size_mb']:.1f} MB"
        )

    lines += [
        "",
        "─── Resource Estimate ───",
        f"  Peak RAM (streaming):  {est['peak_ram_mb']:.2f} MB",
        f"  Full model in-memory:  {est['total_disk_mb']:.1f} MB",
        f"  Total disk output:     {est['total_disk_mb']:.1f} MB",
        f"  Estimated time:        {est['estimated_time_s']:.1f}s",
        "",
        f"  ★ Memory savings: {(1 - est['peak_ram_mb'] / est['total_disk_mb']) * 100:.0f}% vs full load",
        "═══════════════════════════════════",
    ]

    return "\n".join(lines)

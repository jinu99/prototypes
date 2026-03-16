"""Build a mapping from tensor keys to their shard files.

For multi-file safetensors models (e.g., 70B split into model-00001-of-000XX),
this reads model.safetensors.index.json to know which tensor lives in which file.
For single-file models, all tensors come from the single .safetensors file.
"""

import json
from pathlib import Path

from safetensors import safe_open


def build_shard_map(base_dir: Path) -> dict[str, Path]:
    """Return {tensor_key: absolute_path_to_shard_file}.

    Handles both:
    - Multi-shard: reads model.safetensors.index.json
    - Single-file: reads model.safetensors directly
    """
    index_path = base_dir / "model.safetensors.index.json"

    if index_path.exists():
        index = json.loads(index_path.read_text())
        weight_map = index["weight_map"]
        return {key: base_dir / filename for key, filename in weight_map.items()}

    # Single file fallback
    single = base_dir / "model.safetensors"
    if single.exists():
        with safe_open(str(single), framework="pt") as f:
            return {key: single for key in f.keys()}

    raise FileNotFoundError(
        f"No model.safetensors.index.json or model.safetensors in {base_dir}"
    )


def get_shard_files(shard_map: dict[str, Path]) -> list[Path]:
    """Return unique shard files in order."""
    seen = set()
    result = []
    for path in shard_map.values():
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result

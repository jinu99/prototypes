"""Generate minimal test GGUF files for validating the parser.

Creates small GGUF files with correct metadata structure
(no actual tensor data) to test the parser without needing
real multi-GB model files.
"""

import struct
from pathlib import Path

GGUF_MAGIC = 0x46554747
GGUF_VERSION = 3

# Type IDs
TYPE_UINT32 = 4
TYPE_INT32 = 5
TYPE_STRING = 8
TYPE_UINT64 = 10


def write_string(f, s: str):
    encoded = s.encode("utf-8")
    f.write(struct.pack("<Q", len(encoded)))
    f.write(encoded)


def write_kv_string(f, key: str, value: str):
    write_string(f, key)
    f.write(struct.pack("<I", TYPE_STRING))
    write_string(f, value)


def write_kv_uint32(f, key: str, value: int):
    write_string(f, key)
    f.write(struct.pack("<I", TYPE_UINT32))
    f.write(struct.pack("<I", value))


def write_kv_int32(f, key: str, value: int):
    write_string(f, key)
    f.write(struct.pack("<I", TYPE_INT32))
    f.write(struct.pack("<i", value))


def write_kv_uint64(f, key: str, value: int):
    write_string(f, key)
    f.write(struct.pack("<I", TYPE_UINT64))
    f.write(struct.pack("<Q", value))


def create_test_gguf(filepath: str, model_config: dict):
    """Create a minimal GGUF file with model metadata."""
    arch = model_config.get("architecture", "llama")

    # Build KV pairs
    kvs = [
        ("string", "general.architecture", arch),
        ("string", "general.name", model_config["name"]),
        ("uint32", "general.file_type", model_config.get("file_type_id", 15)),
        ("uint32", f"{arch}.block_count", model_config["block_count"]),
        ("uint32", f"{arch}.embedding_length", model_config["embedding_length"]),
        ("uint32", f"{arch}.attention.head_count", model_config["head_count"]),
        ("uint32", f"{arch}.attention.head_count_kv", model_config.get("head_count_kv", model_config["head_count"])),
        ("uint32", f"{arch}.feed_forward_length", model_config.get("feed_forward_length", model_config["embedding_length"] * 4)),
        ("uint32", f"{arch}.context_length", model_config.get("context_length", 4096)),
    ]

    # MoE fields
    if model_config.get("expert_count", 0) > 0:
        kvs.append(("uint32", f"{arch}.expert_count", model_config["expert_count"]))
        kvs.append(("uint32", f"{arch}.expert_used_count", model_config.get("expert_used_count", 2)))

    with open(filepath, "wb") as f:
        # Header
        f.write(struct.pack("<I", GGUF_MAGIC))
        f.write(struct.pack("<I", GGUF_VERSION))
        f.write(struct.pack("<Q", 0))  # tensor_count
        f.write(struct.pack("<Q", len(kvs)))  # metadata_kv_count

        for kv_type, key, value in kvs:
            if kv_type == "string":
                write_kv_string(f, key, value)
            elif kv_type == "uint32":
                write_kv_uint32(f, key, value)
            elif kv_type == "uint64":
                write_kv_uint64(f, key, value)

    print(f"Created test GGUF: {filepath}")


def create_all_test_files(output_dir: str = "test_models"):
    """Create test GGUF files for all sample profiles."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    configs = [
        {
            "name": "Llama-2-7B-Test",
            "architecture": "llama",
            "block_count": 32,
            "embedding_length": 4096,
            "head_count": 32,
            "head_count_kv": 32,
            "feed_forward_length": 11008,
            "context_length": 4096,
            "file_type_id": 15,  # Q4_K_M
        },
        {
            "name": "Mixtral-8x7B-Test",
            "architecture": "llama",
            "block_count": 32,
            "embedding_length": 4096,
            "head_count": 32,
            "head_count_kv": 8,
            "feed_forward_length": 14336,
            "context_length": 32768,
            "file_type_id": 15,
            "expert_count": 8,
            "expert_used_count": 2,
        },
    ]

    files = []
    for cfg in configs:
        filename = cfg["name"].lower().replace(" ", "-") + ".gguf"
        filepath = out / filename
        create_test_gguf(str(filepath), cfg)
        files.append(str(filepath))

    return files


if __name__ == "__main__":
    files = create_all_test_files()
    print(f"\nCreated {len(files)} test files")

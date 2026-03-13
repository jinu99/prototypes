"""GGUF file metadata parser.

Parses the GGUF binary format to extract model structure metadata:
- Architecture, parameter count, layer count, hidden dimensions
- GQA head counts, MoE expert configuration
- Quantization type
"""

import struct
from pathlib import Path

# GGUF metadata value types
GGUF_TYPE_UINT8 = 0
GGUF_TYPE_INT8 = 1
GGUF_TYPE_UINT16 = 2
GGUF_TYPE_INT16 = 3
GGUF_TYPE_UINT32 = 4
GGUF_TYPE_INT32 = 5
GGUF_TYPE_FLOAT32 = 6
GGUF_TYPE_BOOL = 7
GGUF_TYPE_STRING = 8
GGUF_TYPE_ARRAY = 9
GGUF_TYPE_UINT64 = 10
GGUF_TYPE_INT64 = 11
GGUF_TYPE_FLOAT64 = 12

GGUF_MAGIC = 0x46554747  # "GGUF" in little-endian

# Quantization type names and bits-per-weight
QUANT_INFO = {
    0: ("F32", 32.0),
    1: ("F16", 16.0),
    2: ("Q4_0", 4.5),
    3: ("Q4_1", 5.0),
    6: ("Q5_0", 5.5),
    7: ("Q5_1", 6.0),
    8: ("Q8_0", 8.5),
    9: ("Q8_1", 9.0),
    10: ("Q2_K", 3.35),
    11: ("Q3_K_S", 3.5),
    12: ("Q3_K_M", 3.9),
    13: ("Q3_K_L", 4.3),
    14: ("Q4_K_S", 4.5),
    15: ("Q4_K_M", 4.8),
    16: ("Q5_K_S", 5.5),
    17: ("Q5_K_M", 5.7),
    18: ("Q6_K", 6.6),
    19: ("IQ2_XXS", 2.06),
    20: ("IQ2_XS", 2.31),
    28: ("Q4_0_4_4", 4.5),
    29: ("Q4_0_4_8", 4.5),
    30: ("Q4_0_8_8", 4.5),
}

# file_type -> (name, approx bits per weight)
FILE_TYPE_INFO = {
    0: ("ALL_F32", 32.0),
    1: ("MOSTLY_F16", 16.0),
    2: ("MOSTLY_Q4_0", 4.5),
    3: ("MOSTLY_Q4_1", 5.0),
    7: ("MOSTLY_Q8_0", 8.5),
    8: ("MOSTLY_Q5_0", 5.5),
    9: ("MOSTLY_Q5_1", 6.0),
    10: ("MOSTLY_Q2_K", 3.35),
    11: ("MOSTLY_Q3_K_S", 3.5),
    12: ("MOSTLY_Q3_K_M", 3.9),
    13: ("MOSTLY_Q3_K_L", 4.3),
    14: ("MOSTLY_Q4_K_S", 4.5),
    15: ("MOSTLY_Q4_K_M", 4.8),
    16: ("MOSTLY_Q5_K_S", 5.5),
    17: ("MOSTLY_Q5_K_M", 5.7),
    18: ("MOSTLY_Q6_K", 6.6),
    19: ("MOSTLY_IQ2_XXS", 2.06),
    20: ("MOSTLY_IQ2_XS", 2.31),
}


class GGUFParser:
    """Parses GGUF file headers to extract model metadata."""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.metadata: dict = {}
        self.tensor_count = 0
        self.version = 0

    def parse(self) -> dict:
        """Parse the GGUF file and return structured metadata."""
        with open(self.filepath, "rb") as f:
            magic = struct.unpack("<I", f.read(4))[0]
            if magic != GGUF_MAGIC:
                raise ValueError(
                    f"Not a valid GGUF file: magic={hex(magic)}"
                )

            self.version = struct.unpack("<I", f.read(4))[0]
            if self.version not in (2, 3):
                raise ValueError(f"Unsupported GGUF version: {self.version}")

            self.tensor_count = struct.unpack("<Q", f.read(8))[0]
            metadata_kv_count = struct.unpack("<Q", f.read(8))[0]

            for _ in range(metadata_kv_count):
                key = self._read_string(f)
                value = self._read_value(f)
                self.metadata[key] = value

        return self._extract_model_info()

    def _read_string(self, f) -> str:
        length = struct.unpack("<Q", f.read(8))[0]
        return f.read(length).decode("utf-8", errors="replace")

    def _read_value(self, f):
        vtype = struct.unpack("<I", f.read(4))[0]
        return self._read_typed_value(f, vtype)

    def _read_typed_value(self, f, vtype):
        if vtype == GGUF_TYPE_UINT8:
            return struct.unpack("<B", f.read(1))[0]
        elif vtype == GGUF_TYPE_INT8:
            return struct.unpack("<b", f.read(1))[0]
        elif vtype == GGUF_TYPE_UINT16:
            return struct.unpack("<H", f.read(2))[0]
        elif vtype == GGUF_TYPE_INT16:
            return struct.unpack("<h", f.read(2))[0]
        elif vtype == GGUF_TYPE_UINT32:
            return struct.unpack("<I", f.read(4))[0]
        elif vtype == GGUF_TYPE_INT32:
            return struct.unpack("<i", f.read(4))[0]
        elif vtype == GGUF_TYPE_FLOAT32:
            return struct.unpack("<f", f.read(4))[0]
        elif vtype == GGUF_TYPE_BOOL:
            return struct.unpack("<?", f.read(1))[0]
        elif vtype == GGUF_TYPE_STRING:
            return self._read_string(f)
        elif vtype == GGUF_TYPE_ARRAY:
            arr_type = struct.unpack("<I", f.read(4))[0]
            arr_len = struct.unpack("<Q", f.read(8))[0]
            return [self._read_typed_value(f, arr_type) for _ in range(arr_len)]
        elif vtype == GGUF_TYPE_UINT64:
            return struct.unpack("<Q", f.read(8))[0]
        elif vtype == GGUF_TYPE_INT64:
            return struct.unpack("<q", f.read(8))[0]
        elif vtype == GGUF_TYPE_FLOAT64:
            return struct.unpack("<d", f.read(8))[0]
        else:
            raise ValueError(f"Unknown GGUF value type: {vtype}")

    def _extract_model_info(self) -> dict:
        """Extract structured model info from raw metadata."""
        arch = self.metadata.get("general.architecture", "unknown")
        name = self.metadata.get("general.name", self.filepath.stem)
        file_type = self.metadata.get("general.file_type", 0)

        ft_name, bpw = FILE_TYPE_INFO.get(file_type, (f"type_{file_type}", 4.5))

        info = {
            "name": name,
            "filename": self.filepath.name,
            "architecture": arch,
            "tensor_count": self.tensor_count,
            "version": self.version,
            "file_type": ft_name,
            "bits_per_weight": bpw,
            "block_count": self._get_arch_key(arch, "block_count", 0),
            "embedding_length": self._get_arch_key(arch, "embedding_length", 0),
            "head_count": self._get_arch_key(arch, "attention.head_count", 0),
            "head_count_kv": self._get_arch_key(arch, "attention.head_count_kv", 0),
            "feed_forward_length": self._get_arch_key(arch, "feed_forward_length", 0),
            "expert_count": self._get_arch_key(arch, "expert_count", 0),
            "expert_used_count": self._get_arch_key(arch, "expert_used_count", 0),
            "context_length": self._get_arch_key(arch, "context_length", 2048),
            "vocab_size": self.metadata.get(f"{arch}.vocab_size",
                          self.metadata.get("tokenizer.ggml.tokens", []).__len__()
                          if isinstance(self.metadata.get("tokenizer.ggml.tokens"), list)
                          else 0),
            "raw_metadata": {k: v for k, v in self.metadata.items()
                            if not k.startswith("tokenizer.ggml.tokens")
                            and not k.startswith("tokenizer.ggml.scores")
                            and not k.startswith("tokenizer.ggml.token_type")
                            and not isinstance(v, list)},
        }

        # Estimate total parameters
        info["estimated_params"] = self._estimate_params(info)

        return info

    def _get_arch_key(self, arch: str, key: str, default=None):
        return self.metadata.get(f"{arch}.{key}", default)

    def _estimate_params(self, info: dict) -> int:
        """Estimate total parameter count from model dimensions."""
        d = info["embedding_length"]
        n_layers = info["block_count"]
        ffn = info["feed_forward_length"]
        n_heads = info["head_count"]
        n_kv_heads = info["head_count_kv"] or n_heads
        vocab = info["vocab_size"]
        n_experts = info["expert_count"] or 1

        if d == 0 or n_layers == 0:
            return 0

        head_dim = d // n_heads if n_heads > 0 else 0

        # Embedding + output layer
        params = vocab * d * 2

        # Per layer: attention (Q, K, V, O) + FFN
        attn_params = (d * (n_heads * head_dim)  # Q
                       + d * (n_kv_heads * head_dim)  # K
                       + d * (n_kv_heads * head_dim)  # V
                       + (n_heads * head_dim) * d)  # O

        n_ffn_proj = info.get("ffn_projections", 3)
        ffn_params = (d * ffn * n_ffn_proj) * n_experts

        # Layer norms (2 per layer, + final)
        norm_params = d * 2 * n_layers + d

        params += (attn_params + ffn_params) * n_layers + norm_params
        return params


def model_info_from_profile(profile: dict) -> dict:
    """Create model info from a predefined profile (for testing without GGUF files)."""
    d = profile["embedding_length"]
    n_heads = profile["head_count"]
    head_dim = d // n_heads if n_heads > 0 else 0

    info = {
        "name": profile["name"],
        "filename": profile.get("filename", "profile"),
        "architecture": profile.get("architecture", "llama"),
        "tensor_count": 0,
        "version": 3,
        "file_type": profile.get("file_type", "MOSTLY_Q4_K_M"),
        "bits_per_weight": profile.get("bits_per_weight", 4.8),
        "block_count": profile["block_count"],
        "embedding_length": d,
        "head_count": n_heads,
        "head_count_kv": profile.get("head_count_kv", n_heads),
        "feed_forward_length": profile.get("feed_forward_length", d * 4),
        "expert_count": profile.get("expert_count", 0),
        "expert_used_count": profile.get("expert_used_count", 0),
        "context_length": profile.get("context_length", 4096),
        "vocab_size": profile.get("vocab_size", 32000),
        "ffn_projections": profile.get("ffn_projections", 3),
        "raw_metadata": {},
    }
    info["estimated_params"] = 0  # Will be calculated by vram_calculator
    return info


# Predefined model profiles for testing
SAMPLE_PROFILES = {
    "llama-7b-q4km": {
        "name": "Llama 2 7B Q4_K_M",
        "architecture": "llama",
        "block_count": 32,
        "embedding_length": 4096,
        "head_count": 32,
        "head_count_kv": 32,
        "feed_forward_length": 11008,
        "vocab_size": 32000,
        "file_type": "MOSTLY_Q4_K_M",
        "bits_per_weight": 4.8,
        "context_length": 4096,
        "expert_count": 0,
        "expert_used_count": 0,
    },
    "llama-13b-q4km": {
        "name": "Llama 2 13B Q4_K_M",
        "architecture": "llama",
        "block_count": 40,
        "embedding_length": 5120,
        "head_count": 40,
        "head_count_kv": 40,
        "feed_forward_length": 13824,
        "vocab_size": 32000,
        "file_type": "MOSTLY_Q4_K_M",
        "bits_per_weight": 4.8,
        "context_length": 4096,
        "expert_count": 0,
        "expert_used_count": 0,
    },
    "mixtral-8x7b-q4km": {
        "name": "Mixtral 8x7B Q4_K_M",
        "architecture": "llama",
        "block_count": 32,
        "embedding_length": 4096,
        "head_count": 32,
        "head_count_kv": 8,
        "feed_forward_length": 14336,
        "vocab_size": 32000,
        "file_type": "MOSTLY_Q4_K_M",
        "bits_per_weight": 4.8,
        "context_length": 32768,
        "expert_count": 8,
        "expert_used_count": 2,
    },
    "phi-2-q8": {
        "name": "Phi-2 Q8_0",
        "architecture": "phi2",
        "block_count": 32,
        "embedding_length": 2560,
        "head_count": 32,
        "head_count_kv": 32,
        "feed_forward_length": 10240,
        "vocab_size": 51200,
        "file_type": "MOSTLY_Q8_0",
        "bits_per_weight": 8.5,
        "context_length": 2048,
        "expert_count": 0,
        "expert_used_count": 0,
        "ffn_projections": 2,  # Phi-2 uses non-gated MLP (up + down)
    },
    "qwen-1.5-7b-q4km": {
        "name": "Qwen 1.5 7B Q4_K_M",
        "architecture": "qwen2",
        "block_count": 32,
        "embedding_length": 4096,
        "head_count": 32,
        "head_count_kv": 32,
        "feed_forward_length": 11008,
        "vocab_size": 151936,
        "file_type": "MOSTLY_Q4_K_M",
        "bits_per_weight": 4.8,
        "context_length": 32768,
        "expert_count": 0,
        "expert_used_count": 0,
    },
}

"""GPU monitoring via nvidia-smi with mock fallback."""

import subprocess
import random
from dataclasses import dataclass


@dataclass
class GpuInfo:
    index: int
    name: str
    memory_total_mb: float
    memory_used_mb: float
    memory_free_mb: float
    utilization_pct: float

    @property
    def memory_used_pct(self) -> float:
        return (self.memory_used_mb / self.memory_total_mb) * 100 if self.memory_total_mb else 0

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "memory_total_mb": round(self.memory_total_mb, 1),
            "memory_used_mb": round(self.memory_used_mb, 1),
            "memory_free_mb": round(self.memory_free_mb, 1),
            "memory_used_pct": round(self.memory_used_pct, 1),
            "utilization_pct": round(self.utilization_pct, 1),
        }


def query_nvidia_smi() -> list[GpuInfo] | None:
    """Try to get GPU info from nvidia-smi. Returns None if unavailable."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append(GpuInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    memory_total_mb=float(parts[2]),
                    memory_used_mb=float(parts[3]),
                    memory_free_mb=float(parts[4]),
                    utilization_pct=float(parts[5]),
                ))
        return gpus if gpus else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# Mock state that drifts slightly each call to simulate real usage
_mock_base_used = 6144.0


def get_mock_gpus() -> list[GpuInfo]:
    """Return realistic mock GPU data (simulates RTX 4090 24GB)."""
    global _mock_base_used
    # Drift usage randomly within bounds
    _mock_base_used += random.uniform(-200, 200)
    _mock_base_used = max(2000, min(18000, _mock_base_used))
    total = 24564.0
    used = round(_mock_base_used, 1)
    free = round(total - used, 1)
    util = round(random.uniform(15, 65), 1)
    return [GpuInfo(
        index=0,
        name="NVIDIA GeForce RTX 4090 (Mock)",
        memory_total_mb=total,
        memory_used_mb=used,
        memory_free_mb=free,
        utilization_pct=util,
    )]


_use_mock: bool | None = None


def get_gpu_info() -> list[GpuInfo]:
    """Get GPU info from nvidia-smi, falling back to mock data."""
    global _use_mock
    if _use_mock is None:
        real = query_nvidia_smi()
        if real is not None:
            _use_mock = False
            return real
        _use_mock = True
    elif not _use_mock:
        real = query_nvidia_smi()
        if real is not None:
            return real
        _use_mock = True
    return get_mock_gpus()


def is_mock_mode() -> bool:
    """Check if we're using mock data."""
    if _use_mock is None:
        get_gpu_info()  # trigger detection
    return bool(_use_mock)

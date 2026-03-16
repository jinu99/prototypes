"""Ollama REST API client with mock fallback."""

import httpx
import random
from dataclasses import dataclass

OLLAMA_BASE = "http://localhost:11434"


@dataclass
class OllamaModel:
    name: str
    size_bytes: int
    parameter_size: str
    quantization: str
    family: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size_gb": round(self.size_bytes / (1024**3), 2),
            "parameter_size": self.parameter_size,
            "quantization": self.quantization,
            "family": self.family,
        }


@dataclass
class RunningModel:
    name: str
    size_bytes: int
    vram_bytes: int
    expires_at: str

    @property
    def status(self) -> str:
        return "active"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size_gb": round(self.size_bytes / (1024**3), 2),
            "vram_gb": round(self.vram_bytes / (1024**3), 2),
            "status": self.status,
            "expires_at": self.expires_at,
        }


_ollama_available: bool | None = None


async def check_ollama() -> bool:
    """Check if Ollama is reachable."""
    global _ollama_available
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            _ollama_available = resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        _ollama_available = False
    return _ollama_available


async def get_available_models() -> list[OllamaModel]:
    """Get list of locally available models from Ollama."""
    if _ollama_available is False:
        return _get_mock_available_models()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            if resp.status_code != 200:
                return _get_mock_available_models()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                details = m.get("details", {})
                models.append(OllamaModel(
                    name=m["name"],
                    size_bytes=m.get("size", 0),
                    parameter_size=details.get("parameter_size", "unknown"),
                    quantization=details.get("quantization_level", "unknown"),
                    family=details.get("family", "unknown"),
                ))
            return models
    except (httpx.ConnectError, httpx.TimeoutException):
        return _get_mock_available_models()


async def get_running_models() -> list[RunningModel]:
    """Get list of currently loaded/running models."""
    if _ollama_available is False:
        return _get_mock_running_models()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/ps")
            if resp.status_code != 200:
                return _get_mock_running_models()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                models.append(RunningModel(
                    name=m["name"],
                    size_bytes=m.get("size", 0),
                    vram_bytes=m.get("size_vram", 0),
                    expires_at=m.get("expires_at", ""),
                ))
            return models
    except (httpx.ConnectError, httpx.TimeoutException):
        return _get_mock_running_models()


def _get_mock_available_models() -> list[OllamaModel]:
    return [
        OllamaModel("llama3.1:8b-instruct-q4_K_M", 4_920_000_000, "8.0B", "Q4_K_M", "llama"),
        OllamaModel("llama3.1:70b-instruct-q4_K_M", 39_500_000_000, "70.6B", "Q4_K_M", "llama"),
        OllamaModel("codellama:13b-instruct-q4_K_M", 7_370_000_000, "13.0B", "Q4_K_M", "llama"),
        OllamaModel("mistral:7b-instruct-q4_K_M", 4_370_000_000, "7.2B", "Q4_K_M", "mistral"),
        OllamaModel("qwen2.5:14b-instruct-q4_K_M", 8_990_000_000, "14.8B", "Q4_K_M", "qwen2"),
        OllamaModel("deepseek-r1:7b-q4_K_M", 4_700_000_000, "7.6B", "Q4_K_M", "deepseek"),
    ]


def _get_mock_running_models() -> list[RunningModel]:
    return [
        RunningModel(
            name="llama3.1:8b-instruct-q4_K_M",
            size_bytes=4_920_000_000,
            vram_bytes=5_200_000_000,
            expires_at="2026-03-14T12:30:00Z",
        ),
    ]


def is_mock_mode() -> bool:
    return _ollama_available is False or _ollama_available is None

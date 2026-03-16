"""FastAPI backend for Local LLM Resource Monitor."""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from gpu_monitor import get_gpu_info, is_mock_mode as gpu_mock
from ollama_client import (
    check_ollama,
    get_available_models,
    get_running_models,
    is_mock_mode as ollama_mock,
)
from vram_estimator import (
    estimate_vram,
    check_load_feasibility,
    PRESET_MODELS,
    MODEL_ARCHITECTURES,
    QUANT_BITS,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_ollama()
    yield


app = FastAPI(title="Local LLM Resource Monitor", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(html_path.read_text())


@app.get("/api/gpu")
async def api_gpu():
    gpus = get_gpu_info()
    return {
        "mock": gpu_mock(),
        "gpus": [g.to_dict() for g in gpus],
    }


@app.get("/api/ollama/models")
async def api_ollama_models():
    models = await get_available_models()
    return {
        "mock": ollama_mock(),
        "models": [m.to_dict() for m in models],
    }


@app.get("/api/ollama/running")
async def api_ollama_running():
    running = await get_running_models()
    return {
        "mock": ollama_mock(),
        "models": [m.to_dict() for m in running],
    }


@app.get("/api/estimate")
async def api_estimate(
    params_b: float = Query(..., description="Parameters in billions"),
    quant: str = Query("Q4_K_M", description="Quantization level"),
    context_length: int = Query(4096, description="Context length in tokens"),
    model_name: str = Query("custom", description="Model architecture name"),
):
    est = estimate_vram(
        params_b=params_b,
        quant=quant,
        context_length=context_length,
        model_name=model_name,
    )
    return est.to_dict()


@app.get("/api/check-load")
async def api_check_load(
    params_b: float = Query(..., description="Parameters in billions"),
    quant: str = Query("Q4_K_M"),
    context_length: int = Query(4096),
    model_name: str = Query("custom"),
):
    gpus = get_gpu_info()
    available_mb = gpus[0].memory_free_mb if gpus else 0

    est = estimate_vram(
        params_b=params_b,
        quant=quant,
        context_length=context_length,
        model_name=model_name,
    )
    feasibility = check_load_feasibility(available_mb, est)
    return {
        "estimate": est.to_dict(),
        "feasibility": feasibility.to_dict(),
        "gpu_free_mb": round(available_mb, 1),
    }


@app.get("/api/presets")
async def api_presets():
    return {"presets": PRESET_MODELS}


@app.get("/api/meta")
async def api_meta():
    return {
        "architectures": list(MODEL_ARCHITECTURES.keys()),
        "quantizations": list(QUANT_BITS.keys()),
        "gpu_mock": gpu_mock(),
        "ollama_mock": ollama_mock(),
    }

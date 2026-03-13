"""Main FastAPI application — wires all components together."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .admission import AdmissionController
from .backends import BackendManager
from .config import AppConfig, load_config
from .metrics import MetricsStore
from .proxy import create_proxy_routes
from .vram_monitor import VramMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_config: AppConfig | None = None
_vram_monitor: VramMonitor | None = None
_metrics: MetricsStore | None = None
_backend_mgr: BackendManager | None = None
_admission: AdmissionController | None = None


def get_config_path() -> str:
    candidates = ["config.yaml", "config.yml"]
    for c in candidates:
        if Path(c).exists():
            return c
    return "config.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _vram_monitor, _metrics, _backend_mgr, _admission

    config_path = get_config_path()
    _config = load_config(config_path)
    logger.info("Loaded config from %s", config_path)
    logger.info("Backends: %s", [b.name for b in _config.backends])

    # Initialize components
    _metrics = MetricsStore(
        db_path=_config.metrics.db_path,
        retention_hours=_config.metrics.retention_hours,
    )
    await _metrics.init()

    _vram_monitor = VramMonitor(
        poll_interval=_config.vram.poll_interval_seconds,
    )

    _admission = AdmissionController(
        threshold_percent=_config.vram.threshold_percent,
        critical_percent=_config.vram.critical_percent,
        max_queue_size=_config.admission.max_queue_size,
        queue_timeout=_config.admission.queue_timeout_seconds,
    )

    _backend_mgr = BackendManager(_config.backends)

    # Wire VRAM updates to admission controller and metrics
    async def on_vram(status):
        await _admission.on_vram_update(status)
        await _metrics.record_vram(
            status.used_mb, status.total_mb, status.utilization_percent,
        )

    _vram_monitor.on_update(on_vram)

    # Start background tasks
    await _vram_monitor.start()
    await _backend_mgr.start()
    logger.info(
        "Serve Guard started — proxy on %s:%d (mock_vram=%s)",
        _config.proxy.host, _config.proxy.port, _vram_monitor.is_mock,
    )

    # Create proxy routes
    create_proxy_routes(app, _admission, _backend_mgr, _metrics)

    yield

    # Shutdown
    await _vram_monitor.stop()
    await _backend_mgr.stop()
    await _metrics.close()
    logger.info("Serve Guard stopped")


app = FastAPI(title="Local LLM Serve Guard", lifespan=lifespan)


@app.get("/health")
async def health():
    vram = _vram_monitor.latest if _vram_monitor else None
    return {
        "status": "ok",
        "vram": {
            "used_mb": vram.used_mb,
            "total_mb": vram.total_mb,
            "utilization_percent": vram.utilization_percent,
            "mock": _vram_monitor.is_mock,
        } if vram else None,
        "backends": _backend_mgr.get_all_status() if _backend_mgr else [],
        "admission": _admission.stats if _admission else {},
    }


@app.get("/metrics")
async def get_metrics():
    if not _metrics:
        return JSONResponse(status_code=503, content={"error": "not ready"})
    return {
        "vram": await _metrics.get_recent_vram(30),
        "requests": await _metrics.get_recent_requests(50),
        "admission": _admission.stats if _admission else {},
    }


@app.post("/debug/set-mock-vram")
async def set_mock_vram(request: dict):
    """Debug endpoint: override mock VRAM utilization for testing."""
    if not _vram_monitor or not _vram_monitor.is_mock:
        return JSONResponse(status_code=400, content={"error": "not in mock mode"})
    pct = request.get("utilization_percent", 50.0)
    total = 24576.0
    used = total * pct / 100
    from .vram_monitor import VramStatus
    import time
    status = VramStatus(used_mb=used, total_mb=total, utilization_percent=pct, timestamp=time.time())
    _vram_monitor._latest = status
    await _admission.on_vram_update(status)
    await _metrics.record_vram(used, total, pct)
    return {"set": pct, "status": "ok"}

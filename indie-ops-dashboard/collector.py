"""Background metric collector using psutil."""

import asyncio
import time

import psutil

from database import insert_metric

COLLECT_INTERVAL = 30  # seconds


async def collect_once():
    """Collect a single snapshot of system metrics."""
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    net = psutil.net_io_counters()
    ts = time.time()
    await insert_metric(ts, cpu, mem, net.bytes_sent, net.bytes_recv)
    return {"ts": ts, "cpu": cpu, "mem": mem}


async def run_collector():
    """Run the metric collector loop (call from FastAPI lifespan)."""
    while True:
        try:
            await collect_once()
        except Exception as e:
            print(f"[collector] error: {e}")
        await asyncio.sleep(COLLECT_INTERVAL)

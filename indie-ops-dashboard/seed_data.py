"""Generate 24h+ of realistic demo metric data."""

import math
import random
import time

import aiosqlite

from database import DB_PATH


async def seed_if_empty():
    """Seed 36 hours of demo data if DB has fewer than 100 rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM metrics")
        (count,) = await cursor.fetchone()
        if count >= 100:
            return False  # already has enough data

    await generate_demo_data()
    return True


async def generate_demo_data():
    """Insert 36h of synthetic metrics with realistic daily patterns.

    Pattern: high activity 9am-6pm, low activity overnight,
    with random spikes simulating deploys and cron jobs.
    """
    now = time.time()
    start = now - 36 * 3600  # 36 hours ago
    interval = 30  # seconds
    rows = []

    t = start
    net_sent = 1_000_000
    net_recv = 5_000_000

    while t <= now:
        hour = (time.localtime(t).tm_hour + time.localtime(t).tm_min / 60)

        # Base CPU pattern: active during work hours (9-18), idle overnight
        if 9 <= hour < 18:
            base_cpu = random.gauss(35, 15)  # work hours: ~35% avg
        elif 7 <= hour < 9 or 18 <= hour < 22:
            base_cpu = random.gauss(15, 8)   # transition hours
        else:
            base_cpu = random.gauss(3, 2)    # night: ~3% avg

        # Random spikes (simulating deploys, CI, etc.)
        if random.random() < 0.02:
            base_cpu += random.uniform(30, 60)

        cpu = max(0, min(100, base_cpu))

        # Memory: more stable, correlates loosely with CPU
        mem = max(10, min(95, 40 + cpu * 0.3 + random.gauss(0, 5)))

        # Network: proportional to activity
        activity_factor = cpu / 100
        net_sent += int(activity_factor * random.uniform(5000, 50000))
        net_recv += int(activity_factor * random.uniform(10000, 100000))

        rows.append((t, round(cpu, 1), round(mem, 1), net_sent, net_recv))
        t += interval

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO metrics (ts, cpu_percent, memory_percent, net_sent_bytes, net_recv_bytes) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        # Also seed some uptime checks
        uptime_rows = []
        for i in range(20):
            check_ts = now - i * 300  # every 5 minutes
            status = "up" if random.random() > 0.05 else "down"
            resp_ms = random.uniform(50, 300) if status == "up" else None
            error = "Connection timeout" if status == "down" else None
            uptime_rows.append((check_ts, "https://example.com", status, resp_ms, error))

        await db.executemany(
            "INSERT INTO uptime_checks (ts, url, status, response_ms, error) VALUES (?, ?, ?, ?, ?)",
            uptime_rows,
        )

        # Seed some heartbeats
        heartbeat_rows = []
        jobs = ["backup-daily", "cleanup-logs", "sync-data"]
        for job in jobs:
            for i in range(5):
                hb_ts = now - i * 3600 * random.uniform(4, 8)
                heartbeat_rows.append((hb_ts, job))

        await db.executemany(
            "INSERT INTO cron_heartbeats (ts, job_name) VALUES (?, ?)",
            heartbeat_rows,
        )

        await db.commit()

    print(f"[seed] Inserted {len(rows)} metric rows, {len(uptime_rows)} uptime checks, {len(heartbeat_rows)} heartbeats")

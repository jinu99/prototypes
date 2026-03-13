"""Generate sample log files and deploy events for testing."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SAMPLE_DIR = Path(__file__).parent / "sample_data"

# Normal log templates (always present)
NORMAL_TEMPLATES = [
    "INFO {ts} [web] Request {method} {path} completed in {ms}ms",
    "INFO {ts} [db] Query executed in {ms}ms rows={rows}",
    "INFO {ts} [auth] User {user} authenticated successfully",
    "DEBUG {ts} [cache] Cache hit for key={key}",
    "DEBUG {ts} [worker] Job {job_id} processed successfully",
    "INFO {ts} [web] Health check OK",
    "INFO {ts} [metrics] Memory usage: {mem}MB CPU: {cpu}%",
    "WARN {ts} [web] Slow request {path} took {ms}ms",
    "INFO {ts} [scheduler] Cron job {job} completed",
    "DEBUG {ts} [web] Connection pool: active={active} idle={idle}",
]

# Error templates that appear AFTER specific deploys
POST_DEPLOY_ERRORS = {
    "deploy-1": [
        "ERROR {ts} [payment] NullPointerException in PaymentProcessor.charge() at line 142",
        "ERROR {ts} [payment] Failed to process payment for order={order_id}: missing field 'currency'",
        "WARN {ts} [payment] Retry attempt {n}/3 for transaction {tx_id}",
    ],
    "deploy-2": [
        "ERROR {ts} [auth] LDAP connection timeout after 30s to ldap.internal:389",
        "ERROR {ts} [auth] Failed to validate token: certificate expired",
    ],
    "deploy-3": [
        "ERROR {ts} [db] Connection pool exhausted: max=50 active=50 waiting=23",
        "FATAL {ts} [db] Deadlock detected on table 'orders' between tx {tx1} and {tx2}",
        "ERROR {ts} [web] 503 Service Unavailable: upstream db connection failed",
    ],
}

METHODS = ["GET", "POST", "PUT", "DELETE"]
PATHS = ["/api/users", "/api/orders", "/api/products", "/api/payments", "/health", "/api/search"]
USERS = ["alice", "bob", "carol", "dave", "eve"]
KEYS = ["user:123", "product:456", "session:abc", "config:main"]
JOBS = ["cleanup", "sync", "report", "backup", "notify"]


def _rand_params():
    return {
        "method": random.choice(METHODS),
        "path": random.choice(PATHS),
        "ms": random.randint(1, 2000),
        "rows": random.randint(0, 500),
        "user": random.choice(USERS),
        "key": random.choice(KEYS),
        "job_id": f"job-{random.randint(1000, 9999)}",
        "job": random.choice(JOBS),
        "mem": random.randint(200, 800),
        "cpu": random.randint(5, 95),
        "active": random.randint(1, 50),
        "idle": random.randint(0, 20),
        "order_id": f"ORD-{random.randint(10000, 99999)}",
        "n": random.randint(1, 3),
        "tx_id": f"tx-{random.randint(100000, 999999)}",
        "tx1": f"tx-{random.randint(100000, 999999)}",
        "tx2": f"tx-{random.randint(100000, 999999)}",
    }


def generate(num_lines: int = 12000, seed: int = 42) -> tuple[Path, Path]:
    """Generate sample log file and deploy events.

    Creates a realistic scenario:
    - Base time: 2026-03-12 00:00:00
    - 3 deploys spread across the day
    - Normal logs throughout
    - Specific error patterns appear after each deploy

    Returns (log_file_path, deploy_file_path)
    """
    random.seed(seed)
    SAMPLE_DIR.mkdir(exist_ok=True)

    base_time = datetime(2026, 3, 12, 0, 0, 0)
    total_hours = 24
    seconds_per_line = (total_hours * 3600) / num_lines

    # Deploy events at specific times
    deploys = [
        {"timestamp": (base_time + timedelta(hours=3)).isoformat(),
         "commit_hash": "a1b2c3d", "description": "Payment module refactor v2.1"},
        {"timestamp": (base_time + timedelta(hours=10)).isoformat(),
         "commit_hash": "e4f5g6h", "description": "Auth service certificate rotation"},
        {"timestamp": (base_time + timedelta(hours=18)).isoformat(),
         "commit_hash": "i7j8k9l", "description": "Database connection pool upgrade"},
    ]

    deploy_times = {
        "deploy-1": datetime.fromisoformat(deploys[0]["timestamp"]),
        "deploy-2": datetime.fromisoformat(deploys[1]["timestamp"]),
        "deploy-3": datetime.fromisoformat(deploys[2]["timestamp"]),
    }

    lines = []
    for i in range(num_lines):
        ts = base_time + timedelta(seconds=i * seconds_per_line)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
        params = _rand_params()
        params["ts"] = ts_str

        # Check if we should inject post-deploy errors
        error_injected = False
        for deploy_key, deploy_ts in deploy_times.items():
            # Errors appear 1-20 minutes after deploy
            if timedelta(minutes=1) <= (ts - deploy_ts) <= timedelta(minutes=20):
                # 15% chance of error log in this window
                if random.random() < 0.15:
                    template = random.choice(POST_DEPLOY_ERRORS[deploy_key])
                    lines.append(template.format(**params))
                    error_injected = True
                    break

        if not error_injected:
            template = random.choice(NORMAL_TEMPLATES)
            lines.append(template.format(**params))

    log_path = SAMPLE_DIR / "sample.log"
    deploy_path = SAMPLE_DIR / "deploys.json"

    log_path.write_text("\n".join(lines) + "\n")
    deploy_path.write_text(json.dumps(deploys, indent=2))

    return log_path, deploy_path


if __name__ == "__main__":
    log_path, deploy_path = generate()
    print(f"Generated {log_path} ({log_path.stat().st_size // 1024}KB)")
    print(f"Generated {deploy_path}")

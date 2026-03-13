"""Pattern analysis: active/idle classification and cost comparison."""

from datetime import datetime, timezone

# ── Thresholds ──
CPU_ACTIVE_THRESHOLD = 10.0  # CPU% above this = "active"

# ── Hardcoded pricing (us-east-1, monthly) ──
PRICING = {
    "ec2_t3_micro": {
        "label": "EC2 t3.micro (24/7)",
        "hourly": 0.0104,
        "monthly": 0.0104 * 730,  # ~$7.59
    },
    "ec2_t3_small": {
        "label": "EC2 t3.small (24/7)",
        "hourly": 0.0208,
        "monthly": 0.0208 * 730,
    },
    "ec2_t3_medium": {
        "label": "EC2 t3.medium (24/7)",
        "hourly": 0.0416,
        "monthly": 0.0416 * 730,
    },
    "lambda": {
        "label": "Lambda (pay-per-use)",
        "per_request": 0.0000002,  # $0.20 per 1M requests
        "per_gb_second": 0.0000166667,
        "free_requests": 1_000_000,
        "free_gb_seconds": 400_000,
    },
}


def classify_metrics(metrics: list[dict]) -> dict:
    """Classify each metric point as active or idle, compute summary."""
    if not metrics:
        return {"segments": [], "daily_hours": {}, "total_active_pct": 0}

    segments = []
    current_state = None
    segment_start = None

    for m in metrics:
        state = "active" if m["cpu_percent"] >= CPU_ACTIVE_THRESHOLD else "idle"
        if state != current_state:
            if current_state is not None:
                segments.append({
                    "state": current_state,
                    "start": segment_start,
                    "end": m["ts"],
                })
            current_state = state
            segment_start = m["ts"]

    # Close last segment
    if current_state is not None:
        segments.append({
            "state": current_state,
            "start": segment_start,
            "end": metrics[-1]["ts"],
        })

    # Compute daily active hours
    daily_active_seconds: dict[str, float] = {}
    for m in metrics:
        dt = datetime.fromtimestamp(m["ts"], tz=timezone.utc)
        day_key = dt.strftime("%Y-%m-%d")
        if m["cpu_percent"] >= CPU_ACTIVE_THRESHOLD:
            daily_active_seconds.setdefault(day_key, 0.0)
            daily_active_seconds[day_key] += 30  # each sample covers 30s

    daily_hours = {
        day: round(secs / 3600, 1)
        for day, secs in daily_active_seconds.items()
    }

    total_points = len(metrics)
    active_points = sum(1 for m in metrics if m["cpu_percent"] >= CPU_ACTIVE_THRESHOLD)
    total_active_pct = round(active_points / total_points * 100, 1) if total_points else 0

    return {
        "segments": segments,
        "daily_hours": daily_hours,
        "total_active_pct": total_active_pct,
    }


def compute_cost_comparison(daily_hours: dict[str, float]) -> dict:
    """Compare EC2 24/7 cost vs Lambda pay-per-use based on active hours."""
    if not daily_hours:
        return {"ec2": {}, "lambda": {}, "savings": {}}

    avg_active_hours = sum(daily_hours.values()) / len(daily_hours)

    # EC2: fixed monthly cost regardless of usage
    ec2 = PRICING["ec2_t3_micro"]
    ec2_monthly = ec2["monthly"]

    # Lambda estimate:
    # A typical solo-dev server handles ~5000 req/active-hour
    # Average function: 256MB memory, 500ms duration (API + DB)
    requests_per_hour = 5000
    memory_gb = 0.256
    avg_duration_sec = 0.5

    daily_requests = avg_active_hours * requests_per_hour
    monthly_requests = daily_requests * 30
    monthly_gb_seconds = daily_requests * 30 * memory_gb * avg_duration_sec

    # Note: Free tier excluded — most accounts with multiple services have exhausted it
    lam = PRICING["lambda"]
    lambda_request_cost = monthly_requests * lam["per_request"]
    lambda_compute_cost = monthly_gb_seconds * lam["per_gb_second"]
    lambda_monthly = lambda_request_cost + lambda_compute_cost

    savings_monthly = ec2_monthly - lambda_monthly
    savings_pct = round(savings_monthly / ec2_monthly * 100, 1) if ec2_monthly > 0 else 0

    # Format lambda cost: show cents precision for small amounts
    lambda_display = round(lambda_monthly, 2) if lambda_monthly >= 0.01 else round(lambda_monthly, 4)

    return {
        "avg_active_hours_per_day": round(avg_active_hours, 1),
        "ec2": {
            "label": ec2["label"],
            "monthly_cost": round(ec2_monthly, 2),
        },
        "lambda": {
            "label": lam["label"],
            "monthly_requests": int(monthly_requests),
            "monthly_gb_seconds": round(monthly_gb_seconds, 1),
            "monthly_cost": lambda_display,
        },
        "savings": {
            "monthly": round(savings_monthly, 2),
            "percent": savings_pct,
            "recommendation": (
                f"이 서버는 하루 평균 {round(avg_active_hours, 1)}시간만 활성입니다. "
                f"서버리스 전환 시 월 ${round(savings_monthly, 2)} ({savings_pct}%) 절감 가능합니다."
                if savings_monthly > 0
                else "현재 사용량에서는 서버리스 전환의 비용 이점이 없습니다."
            ),
        },
    }

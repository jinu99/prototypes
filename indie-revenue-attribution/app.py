"""FastAPI server: Stripe webhook, analytics API, dashboard serving."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from database import get_db, init_db
from matching import match_payments, derive_channel

app = FastAPI(title="Indie Revenue Attribution")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
def startup():
    init_db()


# --- Stripe Webhook (Test Mode) ---

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Receive Stripe payment events and store in SQLite."""
    body = await request.json()
    event_type = body.get("type", "")

    if event_type != "checkout.session.completed":
        return {"status": "ignored", "type": event_type}

    data = body.get("data", {}).get("object", {})
    payment_id = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO payments (id, stripe_payment_id, amount_cents, currency,
                customer_email, customer_id, product_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payment_id,
            data.get("payment_intent", f"pi_{uuid.uuid4().hex[:24]}"),
            data.get("amount_total", 0),
            data.get("currency", "usd"),
            data.get("customer_email"),
            data.get("customer", ""),
            data.get("metadata", {}).get("product_name", "Unknown"),
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
    finally:
        conn.close()

    return {"status": "stored", "payment_id": payment_id}


# --- Analytics API (Mock Umami-style) ---

@app.post("/api/sync-sessions")
async def sync_sessions():
    """Simulate pulling sessions from Umami/Plausible API.
    In production, this would call the analytics API.
    For the prototype, sessions are pre-seeded."""
    return {"status": "ok", "message": "Sessions are pre-seeded in SQLite (mock Umami sync)"}


# --- Attribution Engine ---

@app.post("/api/match")
async def run_matching():
    """Run the UTM-to-payment matching engine."""
    conn = get_db()
    try:
        stats = match_payments(conn)
    finally:
        conn.close()
    return stats


# --- Dashboard Data API ---

@app.get("/api/dashboard")
async def dashboard_data():
    """Return aggregated attribution data for the dashboard."""
    conn = get_db()
    try:
        # Channel revenue attribution
        channels = conn.execute("""
            SELECT
                COALESCE(matched_channel, 'unmatched') as channel,
                COUNT(*) as payments,
                SUM(amount_cents) as revenue_cents,
                COUNT(DISTINCT customer_email) as customers
            FROM payments
            GROUP BY matched_channel
            ORDER BY revenue_cents DESC
        """).fetchall()

        # Channel costs for CAC
        costs = conn.execute("SELECT * FROM channel_costs").fetchall()
        cost_map = {r["channel"]: dict(r) for r in costs}

        # Build response
        result = []
        total_revenue = sum(ch["revenue_cents"] or 0 for ch in channels)

        for ch in channels:
            channel_name = ch["channel"]
            revenue = ch["revenue_cents"] or 0
            cost_info = cost_map.get(channel_name, {})

            ad_spend = cost_info.get("ad_spend", 0)
            tool_cost = cost_info.get("tool_cost", 0)
            hours = cost_info.get("hours_spent", 0)
            rate = cost_info.get("hourly_rate", 50)
            time_cost = hours * rate

            total_cost = ad_spend + tool_cost + time_cost
            num_customers = ch["customers"]
            true_cac = total_cost / num_customers if num_customers > 0 else 0
            roi = ((revenue / 100) - total_cost) / total_cost * 100 if total_cost > 0 else float('inf')

            result.append({
                "channel": channel_name,
                "payments": ch["payments"],
                "revenue_cents": revenue,
                "revenue_display": f"${revenue / 100:,.2f}",
                "customers": num_customers,
                "pct_of_total": round(revenue / total_revenue * 100, 1) if total_revenue > 0 else 0,
                "costs": {
                    "ad_spend": ad_spend,
                    "tool_cost": tool_cost,
                    "hours_spent": hours,
                    "hourly_rate": rate,
                    "time_cost": time_cost,
                    "total": total_cost,
                },
                "true_cac": round(true_cac, 2),
                "roi_pct": round(roi, 1) if roi != float('inf') else None,
            })

        # Summary
        total_costs = sum(r["costs"]["total"] for r in result)
        summary = {
            "total_revenue_cents": total_revenue,
            "total_revenue_display": f"${total_revenue / 100:,.2f}",
            "total_payments": sum(ch["payments"] for ch in channels),
            "total_customers": len(set(
                r["customer_email"] for r in conn.execute("SELECT DISTINCT customer_email FROM payments").fetchall()
            )),
            "total_costs": total_costs,
            "blended_cac": round(total_costs / sum(ch["customers"] for ch in channels), 2) if channels else 0,
        }
    finally:
        conn.close()

    return {"channels": result, "summary": summary}


@app.get("/api/payments")
async def list_payments():
    """List all payments with attribution info."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT p.*, s.utm_source, s.utm_medium, s.utm_campaign
            FROM payments p
            LEFT JOIN sessions s ON p.matched_session_id = s.id
            ORDER BY p.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Cost Management ---

@app.put("/api/costs/{channel}")
async def update_costs(channel: str, request: Request):
    """Update channel costs for CAC calculation."""
    body = await request.json()
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO channel_costs (channel, ad_spend, tool_cost, hours_spent, hourly_rate, period)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel) DO UPDATE SET
                ad_spend=excluded.ad_spend, tool_cost=excluded.tool_cost,
                hours_spent=excluded.hours_spent, hourly_rate=excluded.hourly_rate
        """, (
            channel,
            body.get("ad_spend", 0),
            body.get("tool_cost", 0),
            body.get("hours_spent", 0),
            body.get("hourly_rate", 50),
            body.get("period", "2026-03"),
        ))
        conn.commit()
    finally:
        conn.close()
    return {"status": "updated"}


# --- Dashboard HTML ---

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Dashboard not found. Run seed_data.py first.</h1>"

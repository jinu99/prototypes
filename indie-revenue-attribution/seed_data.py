"""Generate sample data: 5 channels, 20 payments, matching sessions."""
import uuid
import random
from datetime import datetime, timedelta
from database import get_db, init_db

random.seed(42)

# 5 distinct channels with UTM configs
CHANNELS = [
    {"utm_source": "google", "utm_medium": "cpc", "channel": "paid-search"},
    {"utm_source": "twitter", "utm_medium": "paid", "channel": "paid-social"},
    {"utm_source": "producthunt", "utm_medium": "referral", "channel": "producthunt"},
    {"utm_source": "newsletter", "utm_medium": "email", "channel": "email"},
    {"utm_source": None, "utm_medium": None, "channel": "direct"},  # direct traffic
]

PRODUCTS = ["Pro Plan", "Starter Plan", "Enterprise Plan"]
EMAILS = [f"user{i}@example.com" for i in range(1, 25)]

BASE_TIME = datetime(2026, 3, 1, 10, 0, 0)


def seed():
    init_db()
    conn = get_db()

    # Clear existing data
    conn.execute("DELETE FROM payments")
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM channel_costs")

    sessions_data = []
    payments_data = []

    # Generate 20 payments spread across 5 channels
    # Distribution: paid-search(6), paid-social(4), producthunt(4), email(3), direct(3)
    channel_counts = [6, 4, 4, 3, 3]

    payment_idx = 0
    for ch_idx, count in enumerate(channel_counts):
        channel_cfg = CHANNELS[ch_idx]
        for i in range(count):
            email = EMAILS[payment_idx]
            # Session happens 1-48 hours before payment
            session_offset = timedelta(hours=random.randint(1, 48))
            payment_offset = timedelta(days=random.randint(0, 17), hours=random.randint(0, 23))
            payment_time = BASE_TIME + payment_offset
            session_time = payment_time - session_offset

            session_id = str(uuid.uuid4())
            sessions_data.append((
                session_id,
                email,  # visitor_id = email for matching
                channel_cfg["utm_source"],
                channel_cfg["utm_medium"],
                None,  # utm_campaign
                None,  # utm_content
                None,  # referrer
                "/",   # landing_page
                session_time.isoformat(),
                (session_time + timedelta(minutes=random.randint(1, 30))).isoformat(),
                random.choice(["US", "KR", "DE", "JP", "GB"]),
                random.choice(["desktop", "mobile"]),
            ))

            amount = random.choice([2900, 4900, 9900, 14900, 29900])
            payments_data.append((
                str(uuid.uuid4()),
                f"pi_{uuid.uuid4().hex[:24]}",
                amount,
                "usd",
                email,
                f"cus_{uuid.uuid4().hex[:14]}",
                random.choice(PRODUCTS),
                payment_time.isoformat(),
                None,  # matched_session_id (to be filled by matching)
                None,  # matched_channel (to be filled by matching)
            ))
            payment_idx += 1

    conn.executemany(
        "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        sessions_data
    )
    conn.executemany(
        "INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?,?)",
        payments_data
    )

    # Channel costs for CAC calculation
    costs = [
        ("paid-search", 500, 30, 10, 50, "2026-03"),
        ("paid-social", 300, 20, 8, 50, "2026-03"),
        ("producthunt", 0, 0, 15, 50, "2026-03"),
        ("email", 0, 29, 5, 50, "2026-03"),
        ("direct", 0, 0, 0, 50, "2026-03"),
    ]
    conn.executemany(
        "INSERT INTO channel_costs VALUES (NULL,?,?,?,?,?,?)",
        costs
    )

    conn.commit()

    # Auto-run matching so data is ready to view
    from matching import match_payments
    stats = match_payments(conn)
    print(f"Matching: {stats['matched']}/{stats['total']} payments matched")

    conn.close()
    print(f"Seeded: {len(sessions_data)} sessions, {len(payments_data)} payments, {len(costs)} channel costs")


if __name__ == "__main__":
    seed()

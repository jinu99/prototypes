"""Generate realistic mock email data for testing without a real IMAP server."""

import random
import time
from datetime import datetime, timedelta

NEWSLETTER_SENDERS = [
    ("newsletter@medium.com", "Medium Daily Digest"),
    ("noreply@substack.com", "Substack"),
    ("digest@hackernewsletter.com", "Hacker Newsletter"),
    ("weekly@pythonweekly.com", "Python Weekly"),
    ("news@tldrnewsletter.com", "TLDR Newsletter"),
    ("hello@morningbrew.com", "Morning Brew"),
    ("digest@techmeme.com", "Techmeme"),
    ("weekly@nodeweekly.com", "Node Weekly"),
]

MARKETING_SENDERS = [
    ("deals@amazon.com", "Amazon"),
    ("promo@coupang.com", "Coupang"),
    ("marketing@nike.com", "Nike"),
    ("offers@uber.com", "Uber"),
    ("sales@apple.com", "Apple"),
    ("noreply@spotify.com", "Spotify"),
    ("promo@airbnb.com", "Airbnb"),
]

NOTIFICATION_SENDERS = [
    ("noreply@github.com", "GitHub"),
    ("notifications@slack.com", "Slack"),
    ("noreply@google.com", "Google"),
    ("security@paypal.com", "PayPal"),
    ("noreply@linkedin.com", "LinkedIn"),
    ("no-reply@accounts.google.com", "Google Accounts"),
]

PERSONAL_SENDERS = [
    ("alice@example.com", "Alice Kim"),
    ("bob@company.com", "Bob Park"),
    ("charlie@university.edu", "Charlie Lee"),
    ("diana@startup.io", "Diana Choi"),
    ("evan@freelance.dev", "Evan Jung"),
]

NEWSLETTER_SUBJECTS = [
    "Your weekly digest is here",
    "Top stories this week",
    "This week in tech",
    "Don't miss these articles",
    "Weekly roundup: {}",
    "Issue #{}: The best reads",
    "Your {} update",
]

MARKETING_SUBJECTS = [
    "🔥 Flash sale — up to 70% off!",
    "Special offer just for you",
    "Don't miss out — ends tonight!",
    "Your exclusive discount inside",
    "New arrivals you'll love",
    "Last chance: {} sale ending",
    "We miss you — here's 20% off",
    "Free shipping on orders over $50",
]

NOTIFICATION_SUBJECTS = [
    "[GitHub] New issue on {}",
    "Security alert for your account",
    "Someone mentioned you in #{}",
    "Your order has shipped",
    "Login from a new device",
    "PR #{} needs your review",
    "Weekly activity summary",
]

PERSONAL_SUBJECTS = [
    "Re: Meeting tomorrow",
    "Quick question about the project",
    "Hey, are you free this weekend?",
    "Fwd: Interesting article",
    "Re: Lunch plans",
    "Updated proposal attached",
    "Thanks for your help!",
]

X_MAILERS = [
    "Mailchimp", "SendGrid", "Amazon SES", "Postmark",
    "Mandrill", "Sparkpost", "Campaign Monitor",
]


def _rand_date(days_back: int = 365) -> tuple[str, int]:
    offset = random.randint(0, days_back * 24 * 3600)
    dt = datetime.now() - timedelta(seconds=offset)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000"), int(dt.timestamp())


def _rand_subject(templates: list[str]) -> str:
    tpl = random.choice(templates)
    if "{}" in tpl:
        fillers = ["backend", "frontend", "general", "DevOps", "123", "456", "ML"]
        return tpl.format(random.choice(fillers))
    return tpl


def generate_mock_emails(count: int = 12000, seed: int = 42) -> list[dict]:
    """Generate mock email header records.

    Distribution: ~30% newsletter, ~25% marketing, ~20% notification,
    ~15% personal, ~10% old personal (>6 months).
    """
    random.seed(seed)
    emails = []

    distribution = [
        (int(count * 0.30), NEWSLETTER_SENDERS, NEWSLETTER_SUBJECTS, "newsletter"),
        (int(count * 0.25), MARKETING_SENDERS, MARKETING_SUBJECTS, "marketing"),
        (int(count * 0.20), NOTIFICATION_SENDERS, NOTIFICATION_SUBJECTS, "notification"),
        (int(count * 0.15), PERSONAL_SENDERS, PERSONAL_SUBJECTS, "personal"),
        (int(count * 0.10), PERSONAL_SENDERS, PERSONAL_SUBJECTS, "old"),
    ]

    uid_counter = 1
    for n, senders, subjects, category in distribution:
        for _ in range(n):
            sender_email, sender_name = random.choice(senders)
            date_str, date_ts = _rand_date(
                days_back=180 if category != "old" else 730
            )
            is_read = random.random() < (0.3 if category in ("newsletter", "marketing") else 0.7)
            has_unsub = category in ("newsletter", "marketing")

            emails.append({
                "uid": str(uid_counter),
                "mailbox": "INBOX",
                "sender": sender_email,
                "sender_name": sender_name,
                "subject": _rand_subject(subjects),
                "date": date_str,
                "date_ts": date_ts,
                "is_read": int(is_read),
                "size": random.randint(2000, 150000),
                "has_attachment": int(random.random() < 0.1),
                "list_unsubscribe": f"<mailto:unsub-{uid_counter}@list.example.com>" if has_unsub else "",
                "x_mailer": random.choice(X_MAILERS) if category in ("newsletter", "marketing") else "",
                "precedence": "bulk" if category in ("newsletter", "marketing") else ("list" if category == "notification" else ""),
                "content_type": "text/html" if category != "personal" else "text/plain",
                "category": "",  # will be classified later
            })
            uid_counter += 1

    random.shuffle(emails)
    return emails


if __name__ == "__main__":
    data = generate_mock_emails()
    print(f"Generated {len(data)} mock emails")
    from collections import Counter
    # Show original intended categories for verification
    cats = Counter()
    for e in data:
        # Detect by sender list membership
        for _, senders, _, cat in [
            (0, NEWSLETTER_SENDERS, None, "newsletter"),
            (0, MARKETING_SENDERS, None, "marketing"),
            (0, NOTIFICATION_SENDERS, None, "notification"),
        ]:
            if (e["sender"], e["sender_name"]) in senders:
                cats[cat] += 1
                break
        else:
            cats["personal/old"] += 1
    for cat, n in cats.most_common():
        print(f"  {cat}: {n}")

"""Generate realistic sample emails for demo/testing without a real IMAP server."""
import email.utils
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

SAMPLE_EMAILS = [
    {
        "from": "GitHub <notifications@github.com>",
        "subject": "[frontend-app] PR #432: Fix authentication redirect loop",
        "body": "minjae requested your review on this pull request.\n\nThis PR fixes the infinite redirect loop that occurs when users try to access protected routes after their session expires. The fix adds a check for expired tokens before redirecting to the login page.\n\nFiles changed: 3\n+45 -12",
        "thread": "pr-432",
        "category": "work",
    },
    {
        "from": "Stripe <receipts@stripe.com>",
        "subject": "Your payment receipt from Letsur Inc",
        "body": "Payment confirmation\n\nAmount: $149.00\nDate: March 15, 2026\nDescription: Pro Plan - Monthly\nCard ending in: 4242\n\nView your receipt: https://pay.stripe.com/...\n\nIf you have any questions, contact support@letsur.com",
        "thread": "stripe-receipt-march",
        "category": "finance",
    },
    {
        "from": "Jira <jira@letsur.atlassian.net>",
        "subject": "[PROD-1234] Critical: API latency spike in payment service",
        "body": "Priority: Critical\nAssigned to: You\nReporter: SRE Bot\n\nThe payment service is experiencing p99 latency > 5s since 14:30 KST. Grafana dashboard shows connection pool exhaustion. This is affecting checkout flow.\n\nPlease investigate immediately.",
        "thread": "prod-1234",
        "category": "work",
    },
    {
        "from": "Google <no-reply@accounts.google.com>",
        "subject": "Security alert: New sign-in from Windows",
        "body": "New sign-in to your Google Account\n\nWe noticed a new sign-in to your Google Account on a Windows device. If this was you, you don't need to do anything. If not, we'll help you secure your account.\n\nDevice: Windows PC\nLocation: Seoul, South Korea\nTime: March 17, 2026 at 9:23 PM KST",
        "thread": None,
        "category": "security",
    },
    {
        "from": "Amazon <ship-confirm@amazon.co.kr>",
        "subject": "Your Amazon order has shipped! (Order #304-1234567-8901234)",
        "body": "Your package is on the way!\n\nOrder #304-1234567-8901234\nItem: Sony WH-1000XM5 Wireless Headphones\nEstimated delivery: March 20, 2026\nCarrier: CJ Logistics\nTracking: 1234567890\n\nTrack your package at amazon.co.kr/orders",
        "thread": None,
        "category": "shopping",
    },
    {
        "from": "Substack <noreply@substack.com>",
        "subject": "The Pragmatic Engineer: How Big Tech Does Code Review",
        "body": "New post from The Pragmatic Engineer\n\nHow Big Tech Does Code Review\n\nI interviewed 20+ engineers at Google, Meta, and Stripe about their code review practices. Here's what I learned:\n\n1. Google's readability reviews are unique...\n2. Meta's diff-based review culture...\n3. Stripe's thorough review process...\n\nRead the full post: https://newsletter.pragmaticengineer.com/...\n\nYou're receiving this because you subscribed. Unsubscribe here.",
        "thread": None,
        "category": "newsletter",
    },
    {
        "from": "김민재 <minjae@letsur.com>",
        "subject": "Re: [frontend-app] PR #432: Fix authentication redirect loop",
        "body": "LGTM! Just one minor comment - can we add a test case for the edge case where the token is expired but the refresh token is still valid?\n\nOtherwise this looks good to merge.",
        "thread": "pr-432",
        "category": "work",
    },
    {
        "from": "Slack <feedback@slack.com>",
        "subject": "50% off Slack Pro - Limited time offer",
        "body": "Upgrade to Slack Pro at 50% off!\n\nFor a limited time, get Slack Pro for your team at half the price. Enjoy unlimited message history, advanced search, and more.\n\nUse code: SPRING50\nOffer expires: March 31, 2026\n\nUpgrade now: slack.com/pricing",
        "thread": None,
        "category": "marketing",
    },
    {
        "from": "LinkedIn <notifications-noreply@linkedin.com>",
        "subject": "3 people viewed your profile this week",
        "body": "Your weekly profile update\n\nYour profile was viewed 3 times this week. Here's who viewed you:\n\n- Senior Recruiter at Kakao\n- Engineering Manager at Toss\n- CTO at Startup X\n\nSee all views: linkedin.com/me/profile-views",
        "thread": None,
        "category": "social",
    },
    {
        "from": "Korean Air <noreply@koreanair.com>",
        "subject": "E-ticket confirmation: Seoul → Tokyo (ICN-NRT)",
        "body": "Booking Confirmed\n\nPassenger: Jinwoo Choi\nFlight: KE701\nDate: April 5, 2026\nDeparture: ICN 09:30 → NRT 11:50\nBooking ref: ABCDEF\nSeat: 23A (Window)\n\nPlease check in online 48 hours before departure at koreanair.com",
        "thread": None,
        "category": "travel",
    },
    {
        "from": "이서연 <seoyeon@letsur.com>",
        "subject": "위클리 미팅 안건 공유",
        "body": "안녕하세요 진우님,\n\n이번 주 위클리 안건입니다:\n\n1. Q2 로드맵 확정 - OKR 기반\n2. 온콜 로테이션 개선안 논의\n3. 신규 입사자 온보딩 프로세스\n\n금요일 14시에 뵙겠습니다.\n\n서연",
        "thread": "weekly-agenda",
        "category": "work",
    },
    {
        "from": "이서연 <seoyeon@letsur.com>",
        "subject": "Re: 위클리 미팅 안건 공유",
        "body": "추가 안건:\n4. 프론트엔드 성능 개선 진행상황 공유\n5. 디자인 시스템 v2 마이그레이션 일정\n\n서연",
        "thread": "weekly-agenda",
        "category": "work",
    },
    {
        "from": "GitHub <notifications@github.com>",
        "subject": "[backend-api] Deploy failed: staging (Run #5678)",
        "body": "Run #5678 (deploy-staging) failed.\n\nCommit: abc1234 - Update database migration\nTriggered by: push to main\nFailed step: Run migrations\nError: relation 'user_preferences' already exists\n\nView run: https://github.com/letsur/backend-api/actions/runs/5678",
        "thread": None,
        "category": "work",
    },
    {
        "from": "Coupang <no-reply@coupang.com>",
        "subject": "로켓배송 도착 완료 - 주문번호 2026031712345",
        "body": "배송이 완료되었습니다!\n\n주문번호: 2026031712345\n상품: 삼성 충전기 45W\n배송지: 서울시 강남구...\n수령: 문 앞\n\n수령 확인 부탁드립니다.",
        "thread": None,
        "category": "shopping",
    },
    {
        "from": "AWS <no-reply@sns.amazonaws.com>",
        "subject": "AWS Billing Alert: Estimated charges exceed $100",
        "body": "Dear AWS Customer,\n\nYour estimated charges for this billing period have exceeded the $100 threshold you set.\n\nCurrent estimated charges: $127.45\nForecasted month-end charges: $185.00\n\nTop services:\n- EC2: $65.20\n- RDS: $35.10\n- S3: $12.15\n\nReview your charges at: console.aws.amazon.com/billing",
        "thread": None,
        "category": "finance",
    },
    {
        "from": "Netflix <info@members.netflix.com>",
        "subject": "New on Netflix: Shows you might like",
        "body": "Based on your viewing history, we think you'll love:\n\n- Squid Game Season 3 (New!)\n- The Three-Body Problem Season 2\n- Money Heist: Berlin\n\nStart watching now at netflix.com\n\nUnsubscribe from marketing emails",
        "thread": None,
        "category": "marketing",
    },
    {
        "from": "박성민 <sungmin@letsur.com>",
        "subject": "Re: [PROD-1234] Critical: API latency spike in payment service",
        "body": "원인 파악했습니다.\n\nDB 커넥션 풀이 max 10으로 설정되어 있었는데, 오후 트래픽 급증으로 exhaustion 발생. max 50으로 올리고 모니터링 중입니다.\n\n현재 p99 800ms로 안정화됨.",
        "thread": "prod-1234",
        "category": "work",
    },
    {
        "from": "GitHub <notifications@github.com>",
        "subject": "Re: [frontend-app] PR #432: Fix authentication redirect loop",
        "body": "minjae approved this pull request.\n\nAdded the test case as requested. Merging now.\n\nSquash and merge: 3 commits → 1",
        "thread": "pr-432",
        "category": "work",
    },
    {
        "from": "Google Calendar <calendar-notification@google.com>",
        "subject": "Reminder: 1:1 with CTO @ 3:00 PM",
        "body": "Reminder\n\n1:1 with CTO\nWhen: Today, 3:00 PM - 3:30 PM KST\nWhere: Google Meet (link)\n\nAgenda:\n- Q2 hiring plan\n- Architecture review process\n- Team health check",
        "thread": None,
        "category": "notification",
    },
    {
        "from": "진우 <jinwoo@letsur.com>",
        "subject": "Re: 위클리 미팅 안건 공유",
        "body": "서연님 감사합니다.\n\n저도 하나 추가요:\n6. 온콜 gap predetector 프로토타입 데모\n\n금요일에 뵙겠습니다.\n\n진우",
        "thread": "weekly-agenda",
        "category": "work",
    },
]


def generate_demo_emails() -> list[tuple[str, bytes]]:
    """Generate MIME-formatted demo emails with realistic headers."""
    base_time = datetime.now() - timedelta(hours=len(SAMPLE_EMAILS))
    results = []
    thread_roots: dict[str, str] = {}

    for i, sample in enumerate(SAMPLE_EMAILS):
        msg_time = base_time + timedelta(hours=i, minutes=i * 7)
        msg_id = f"<demo-{i+1:03d}@email-classify.local>"
        thread_key = sample.get("thread")

        msg = MIMEMultipart()
        msg["From"] = sample["from"]
        msg["To"] = "jinwoo@letsur.com"
        msg["Subject"] = sample["subject"]
        msg["Date"] = email.utils.format_datetime(msg_time)
        msg["Message-ID"] = msg_id

        if thread_key:
            if thread_key not in thread_roots:
                thread_roots[thread_key] = msg_id
            else:
                msg["In-Reply-To"] = thread_roots[thread_key]
                msg["References"] = thread_roots[thread_key]

        msg.attach(MIMEText(sample["body"], "plain", "utf-8"))
        results.append((str(i + 1), msg.as_bytes()))

    return results

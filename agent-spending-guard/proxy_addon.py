"""mitmproxy addon that intercepts payment API calls and enforces spending policy."""

import json
import os
import re
import sys
import yaml
from pathlib import Path
from urllib.parse import urlparse, unquote_plus

from mitmproxy import http, ctx

# Add project root to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))
import db
from pii import detect_pii


def load_policy() -> dict:
    policy_path = Path(__file__).parent / "policy.yaml"
    with open(policy_path) as f:
        return yaml.safe_load(f)


def extract_nested(data: dict, field_path: str):
    """Extract a value from nested dict using dot notation (e.g. 'a.0.b')."""
    parts = field_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def parse_amount(raw_amount, unit: str) -> float | None:
    """Convert raw amount to dollars."""
    try:
        val = float(raw_amount)
        if unit == "cents":
            return val / 100.0
        return val
    except (TypeError, ValueError):
        return None


def parse_request_body(flow: http.HTTPFlow) -> dict:
    """Parse request body as JSON or form data."""
    content = flow.request.get_text()
    if not content:
        return {}

    # Try JSON first
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try form-encoded
    if flow.request.urlencoded_form:
        return dict(flow.request.urlencoded_form)

    return {}


class SpendingGuard:
    def __init__(self):
        self.policy = load_policy()
        self._non_interactive = os.environ.get("SPENDING_GUARD_NON_INTERACTIVE") == "1"

    def _match_pattern(self, flow: http.HTTPFlow) -> dict | None:
        """Check if flow matches any payment API pattern."""
        path = flow.request.path
        method = flow.request.method.upper()

        for pattern in self.policy.get("patterns", []):
            if method != pattern.get("method", "POST").upper():
                continue
            if pattern["url_pattern"] in path:
                return pattern
        return None

    def _check_limits(self, amount: float, pattern: dict) -> tuple[bool, str]:
        """Check transaction against policy limits. Returns (allowed, reason)."""
        limits = self.policy.get("limits", {})

        # Per-transaction limit
        per_tx = limits.get("per_transaction", float("inf"))
        if amount > per_tx:
            return False, f"exceeds per-transaction limit (${amount:.2f} > ${per_tx:.2f})"

        # Daily cumulative limit
        daily_limit = limits.get("daily", float("inf"))
        daily_total = db.get_daily_total()
        if daily_total + amount > daily_limit:
            return False, (
                f"exceeds daily limit (${daily_total:.2f} + ${amount:.2f} "
                f"= ${daily_total + amount:.2f} > ${daily_limit:.2f})"
            )

        # Monthly cumulative limit
        monthly_limit = limits.get("monthly", float("inf"))
        monthly_total = db.get_monthly_total()
        if monthly_total + amount > monthly_limit:
            return False, (
                f"exceeds monthly limit (${monthly_total:.2f} + ${amount:.2f} "
                f"= ${monthly_total + amount:.2f} > ${monthly_limit:.2f})"
            )

        return True, "within limits"

    def _request_approval(self, flow: http.HTTPFlow, amount: float,
                          reason: str, pii_findings: list) -> bool:
        """Request human approval via CLI. Blocks until response."""
        print("\n" + "=" * 60)
        print("🚨 SPENDING GUARD — APPROVAL REQUIRED")
        print("=" * 60)
        print(f"  URL:    {flow.request.method} {flow.request.url}")
        print(f"  Amount: ${amount:.2f}")
        print(f"  Reason: {reason}")
        if pii_findings:
            names = [f["name"] for f in pii_findings]
            print(f"  PII:    {', '.join(names)} detected in request")
        print("-" * 60)

        # Non-interactive mode: auto-deny (for testing)
        if getattr(self, '_non_interactive', False):
            print("  [non-interactive mode] Auto-denied.")
            return False

        try:
            response = input("  Approve? [y/N]: ").strip().lower()
            approved = response in ("y", "yes")
            print(f"  → {'APPROVED' if approved else 'DENIED'}")
            print("=" * 60 + "\n")
            return approved
        except (EOFError, KeyboardInterrupt):
            print("\n  → DENIED (no input)")
            return False

    def request(self, flow: http.HTTPFlow):
        pattern = self._match_pattern(flow)
        if pattern is None:
            return  # Not a payment request, pass through

        body = parse_request_body(flow)
        body_text = flow.request.get_text() or ""
        # Decode URL-encoded body for PII scanning
        body_text_decoded = unquote_plus(body_text)

        # Extract amount
        amount_raw = extract_nested(body, pattern["amount_field"])
        amount = parse_amount(amount_raw, pattern.get("amount_unit", "dollars"))
        currency = extract_nested(body, pattern.get("currency_field", "currency"))

        # PII detection (use decoded text so URL-encoded chars like %40 are readable)
        pii_config = self.policy.get("pii", {})
        pii_findings = detect_pii(body_text_decoded, pii_config)

        ctx.log.info(
            f"[SpendingGuard] Intercepted {pattern['name']}: "
            f"${amount:.2f} {currency}" if amount else
            f"[SpendingGuard] Intercepted {pattern['name']}: amount unknown"
        )

        decision = "approved"
        reason = ""

        # Check PII — block if action is "block"
        if pii_findings and pii_config.get("action") == "block":
            decision = "blocked"
            reason = f"PII detected: {', '.join(f['name'] for f in pii_findings)}"
        elif amount is not None:
            allowed, reason = self._check_limits(amount, pattern)
            if not allowed:
                # Request human approval
                approved = self._request_approval(flow, amount, reason, pii_findings)
                decision = "approved" if approved else "blocked"
                if not approved:
                    reason = f"human denied: {reason}"
        else:
            reason = "amount not parseable, allowing"

        # PII warning (even if allowed)
        if pii_findings and decision == "approved" and pii_config.get("action") == "warn":
            pii_names = [f["name"] for f in pii_findings]
            ctx.log.warn(
                f"[SpendingGuard] ⚠ PII detected in request: {', '.join(pii_names)}"
            )

        # Log to audit DB
        db.log_transaction(
            api_pattern=pattern["name"],
            method=flow.request.method,
            url=flow.request.url,
            amount=amount,
            currency=currency,
            decision=decision,
            reason=reason,
            pii_detected=[f["name"] for f in pii_findings] if pii_findings else None,
            request_body=body_text[:2000],  # Truncate for safety
        )

        if decision == "blocked":
            flow.response = http.Response.make(
                403,
                json.dumps({
                    "error": {
                        "type": "spending_guard_blocked",
                        "message": f"Transaction blocked: {reason}",
                    }
                }),
                {"Content-Type": "application/json"},
            )
            ctx.log.warn(f"[SpendingGuard] BLOCKED: {reason}")
        else:
            ctx.log.info(f"[SpendingGuard] APPROVED: ${amount:.2f}" if amount else
                        "[SpendingGuard] APPROVED")


addons = [SpendingGuard()]

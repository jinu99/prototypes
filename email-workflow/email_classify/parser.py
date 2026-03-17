"""MIME multipart parsing → meaningful text extraction + token trimming."""
import email
import email.policy
import re
from email.message import EmailMessage
from typing import Optional


MAX_BODY_CHARS = 2000  # ~500 tokens for LLM


def parse_raw_email(raw_bytes: bytes) -> dict:
    """Parse raw email bytes into structured dict."""
    msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)
    return {
        "message_id": msg.get("Message-ID", "").strip("<>"),
        "subject": msg.get("Subject", "(no subject)"),
        "sender": _extract_sender(msg),
        "sender_full": msg.get("From", ""),
        "date": msg.get("Date", ""),
        "thread_id": _extract_thread_id(msg),
        "body": _extract_body(msg),
    }


def _extract_sender(msg: EmailMessage) -> str:
    from_header = msg.get("From", "")
    # Try to get just the name or email
    if "<" in from_header:
        name = from_header.split("<")[0].strip().strip('"')
        addr = from_header.split("<")[1].rstrip(">")
        return name if name else addr
    return from_header


def _extract_thread_id(msg: EmailMessage) -> str:
    """Extract thread ID from References or In-Reply-To headers."""
    refs = msg.get("References", "")
    if refs:
        # First message-id in References is the thread root
        ids = re.findall(r"<([^>]+)>", refs)
        if ids:
            return ids[0]
    reply_to = msg.get("In-Reply-To", "")
    if reply_to:
        match = re.search(r"<([^>]+)>", reply_to)
        if match:
            return match.group(1)
    # Standalone message — its own ID is the thread
    return msg.get("Message-ID", "").strip("<>")


def _extract_body(msg: EmailMessage) -> str:
    """Extract text body from MIME message, prefer plain text."""
    body = _get_text_part(msg)
    if not body:
        return "(no text content)"
    body = _clean_text(body)
    return body[:MAX_BODY_CHARS]


def _get_text_part(msg: EmailMessage) -> Optional[str]:
    """Walk MIME parts to find text/plain or text/html."""
    if msg.is_multipart():
        # Prefer text/plain
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    return part.get_content()
                except Exception:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
        # Fallback to text/html
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                try:
                    content = part.get_content()
                except Exception:
                    content = part.get_payload(decode=True).decode("utf-8", errors="replace")
                return _strip_html(content)
    else:
        ct = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            content = msg.get_payload(decode=True)
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
        if ct == "text/html":
            return _strip_html(content)
        return content
    return None


def _strip_html(html: str) -> str:
    """Basic HTML tag removal."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return text.strip()


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and quoted reply chains."""
    # Remove common reply markers
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # Stop at quoted content
        if line.strip().startswith(">") and len(cleaned) > 3:
            break
        if re.match(r"^On .+ wrote:$", line.strip()):
            break
        cleaned.append(line)
    text = "\n".join(cleaned)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

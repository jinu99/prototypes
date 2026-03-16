"""IMAP client: real IMAP connection or mock mode."""

import email
import email.utils
import imaplib
import time
from datetime import datetime

from src.db import get_connection, init_db, upsert_emails


def parse_header_bytes(raw: bytes, uid: str, mailbox: str) -> dict:
    """Parse raw email header bytes into a dict for DB storage."""
    msg = email.message_from_bytes(raw)

    sender_full = msg.get("From", "")
    sender_name, sender_email = email.utils.parseaddr(sender_full)
    sender_email = sender_email.lower()

    date_str = msg.get("Date", "")
    date_tuple = email.utils.parsedate_tz(date_str)
    date_ts = int(email.utils.mktime_tz(date_tuple)) if date_tuple else 0

    size_str = msg.get("Content-Length", "0")
    try:
        size = int(size_str)
    except ValueError:
        size = 0

    return {
        "uid": f"{mailbox}:{uid}",
        "mailbox": mailbox,
        "sender": sender_email,
        "sender_name": sender_name,
        "subject": msg.get("Subject", ""),
        "date": date_str,
        "date_ts": date_ts,
        "is_read": 0,  # updated after FLAGS fetch
        "size": size,
        "has_attachment": int("attachment" in msg.get("Content-Disposition", "").lower()),
        "list_unsubscribe": msg.get("List-Unsubscribe", ""),
        "x_mailer": msg.get("X-Mailer", ""),
        "precedence": msg.get("Precedence", ""),
        "content_type": msg.get("Content-Type", "").split(";")[0].strip(),
        "category": "",
    }


def fetch_from_imap(
    host: str,
    user: str,
    password: str,
    port: int = 993,
    mailbox: str = "INBOX",
    batch_size: int = 500,
    use_ssl: bool = True,
    db_path=None,
) -> int:
    """Connect to real IMAP server and fetch all headers into SQLite.

    Returns total emails fetched.
    """
    conn = get_connection(db_path)
    init_db(conn)

    if use_ssl:
        imap = imaplib.IMAP4_SSL(host, port)
    else:
        imap = imaplib.IMAP4(host, port)

    imap.login(user, password)
    imap.select(mailbox, readonly=True)

    # Get all UIDs
    status, data = imap.uid("SEARCH", None, "ALL")
    if status != "OK":
        raise RuntimeError(f"IMAP SEARCH failed: {status}")

    uids = data[0].split()
    total = len(uids)
    fetched = 0

    # Batch fetch
    for i in range(0, total, batch_size):
        batch_uids = uids[i : i + batch_size]
        uid_range = b",".join(batch_uids)

        status, data = imap.uid(
            "FETCH", uid_range, "(FLAGS BODY.PEEK[HEADER] RFC822.SIZE)"
        )
        if status != "OK":
            continue

        rows = []
        # data comes as pairs: (envelope, header_bytes)
        j = 0
        while j < len(data):
            if isinstance(data[j], tuple):
                envelope = data[j][0].decode("utf-8", errors="replace")
                raw_header = data[j][1]

                # Extract UID from envelope
                uid_str = ""
                for part in envelope.split():
                    if part.startswith("UID"):
                        # UID comes after "UID" keyword
                        pass
                # Simpler: use the uid from our list
                idx = i + len(rows)
                if idx < total:
                    uid_str = uids[idx].decode()

                row = parse_header_bytes(raw_header, uid_str, mailbox)
                row["size"] = _extract_size(envelope)
                row["is_read"] = int("\\Seen" in envelope)
                rows.append(row)
            j += 1

        upsert_emails(conn, rows)
        fetched += len(rows)

    imap.logout()
    conn.close()
    return fetched


def _extract_size(envelope: str) -> int:
    """Extract RFC822.SIZE from FETCH envelope string."""
    import re
    m = re.search(r"RFC822\.SIZE\s+(\d+)", envelope)
    return int(m.group(1)) if m else 0


def load_mock_data(count: int = 12000, db_path=None) -> int:
    """Load mock email data into SQLite. Returns count loaded."""
    from mock_data import generate_mock_emails

    conn = get_connection(db_path)
    init_db(conn)

    emails = generate_mock_emails(count=count)
    inserted = upsert_emails(conn, emails)
    conn.close()
    return inserted

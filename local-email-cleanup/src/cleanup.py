"""Execute cleanup actions: delete or archive emails via IMAP or locally."""

import imaplib

from src.db import get_connection, delete_emails, get_emails_by_category
from src.analyzer import format_size


def dry_run(db_path=None) -> dict:
    """Preview cleanup impact without making changes."""
    conn = get_connection(db_path)

    results = {}
    for category in ("newsletter", "marketing", "notification", "old"):
        rows = get_emails_by_category(conn, category)
        if rows:
            total_size = sum(r["size"] for r in rows)
            senders = {}
            for r in rows:
                senders[r["sender"]] = senders.get(r["sender"], 0) + 1
            results[category] = {
                "count": len(rows),
                "size": total_size,
                "size_human": format_size(total_size),
                "top_senders": sorted(senders.items(), key=lambda x: -x[1])[:5],
                "uids": [r["uid"] for r in rows],
            }

    conn.close()
    return results


def execute_cleanup_local(categories: list[str], db_path=None) -> dict:
    """Delete emails from local SQLite cache by category."""
    conn = get_connection(db_path)
    results = {}

    for cat in categories:
        rows = get_emails_by_category(conn, cat)
        uids = [r["uid"] for r in rows]
        deleted = delete_emails(conn, uids)
        results[cat] = {"deleted": deleted, "size": sum(r["size"] for r in rows)}

    conn.close()
    return results


def execute_cleanup_imap(
    host: str,
    user: str,
    password: str,
    uids: list[str],
    action: str = "delete",
    port: int = 993,
    mailbox: str = "INBOX",
    use_ssl: bool = True,
) -> dict:
    """Execute DELETE or ARCHIVE on real IMAP server.

    action: 'delete' = mark as \\Deleted + EXPUNGE
            'archive' = move to [Gmail]/All Mail or Archive folder
    """
    if use_ssl:
        imap = imaplib.IMAP4_SSL(host, port)
    else:
        imap = imaplib.IMAP4(host, port)

    imap.login(user, password)
    imap.select(mailbox)

    success = 0
    failed = 0

    # Process in batches of 100
    for i in range(0, len(uids), 100):
        batch = uids[i : i + 100]
        uid_str = ",".join(batch)

        if action == "delete":
            status, _ = imap.uid("STORE", uid_str, "+FLAGS", "(\\Deleted)")
            if status == "OK":
                success += len(batch)
            else:
                failed += len(batch)
        elif action == "archive":
            # Try common archive folder names
            for archive_folder in ("[Gmail]/All Mail", "Archive", "Archives"):
                try:
                    status, _ = imap.uid("COPY", uid_str, archive_folder)
                    if status == "OK":
                        imap.uid("STORE", uid_str, "+FLAGS", "(\\Deleted)")
                        success += len(batch)
                        break
                except imaplib.IMAP4.error:
                    continue
            else:
                failed += len(batch)

    if action == "delete":
        imap.expunge()

    imap.logout()
    return {"success": success, "failed": failed, "action": action}

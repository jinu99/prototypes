"""IMAP EXAMINE-mode client for read-only email fetching."""
import imaplib
import logging
from typing import Optional

log = logging.getLogger(__name__)


class ImapReader:
    """Read-only IMAP client using EXAMINE (never SELECT)."""

    def __init__(self, host: str, port: int, username: str, password: str,
                 use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self._conn: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None
        self.imap_log: list[str] = []

    def connect(self) -> str:
        """Connect and authenticate. Returns server greeting."""
        self._log("CONNECT", f"{self.host}:{self.port} (SSL={self.use_ssl})")
        if self.use_ssl:
            self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self._conn = imaplib.IMAP4(self.host, self.port)
        self._log("AUTH", f"user={self.username}")
        self._conn.login(self.username, self.password)
        greeting = self._conn.welcome.decode() if self._conn.welcome else "OK"
        self._log("GREETING", greeting)
        return greeting

    def examine_inbox(self) -> int:
        """Open INBOX in EXAMINE (read-only) mode. Returns message count."""
        assert self._conn, "Not connected"
        self._log("EXAMINE", "INBOX")
        status, data = self._conn.examine("INBOX")
        count = int(data[0])
        self._log("EXAMINE_OK", f"{count} messages")
        return count

    def fetch_recent(self, count: int = 50) -> list[tuple[str, bytes]]:
        """Fetch the most recent `count` emails as (uid, raw_bytes) pairs."""
        assert self._conn, "Not connected"
        # Search for all messages
        self._log("SEARCH", "ALL")
        status, data = self._conn.search(None, "ALL")
        all_ids = data[0].split()

        # Take the last `count`
        target_ids = all_ids[-count:] if len(all_ids) > count else all_ids
        self._log("FETCH", f"{len(target_ids)} messages (of {len(all_ids)} total)")

        results = []
        for msg_id in target_ids:
            status, msg_data = self._conn.fetch(msg_id, "(RFC822)")
            if status == "OK" and msg_data[0]:
                raw = msg_data[0][1]
                results.append((msg_id.decode(), raw))
        self._log("FETCH_OK", f"got {len(results)} messages")
        return results

    def disconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            try:
                self._conn.logout()
            except Exception:
                pass
            self._log("DISCONNECT", "OK")
            self._conn = None

    def _log(self, cmd: str, detail: str):
        entry = f"[IMAP] {cmd}: {detail}"
        self.imap_log.append(entry)
        log.debug(entry)

    def get_log(self) -> str:
        return "\n".join(self.imap_log)

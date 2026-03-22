"""SQLite-based audit log for retrieval results."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RetrievalRecord:
    query: str
    doc_id: str
    content_preview: str
    source: str
    trust_score: float
    is_trusted: bool


class AuditLog:
    """Stores and queries retrieval audit records in SQLite."""

    def __init__(self, db_path: str | Path = "audit_log.db"):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                query TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                content_preview TEXT,
                source TEXT,
                trust_score REAL,
                is_trusted INTEGER
            )
        """)
        self._conn.commit()

    def log(self, records: list[RetrievalRecord]) -> None:
        """Log a batch of retrieval records."""
        self._conn.executemany(
            """INSERT INTO retrieval_log
               (query, doc_id, content_preview, source, trust_score, is_trusted)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (r.query, r.doc_id, r.content_preview, r.source,
                 r.trust_score, int(r.is_trusted))
                for r in records
            ],
        )
        self._conn.commit()

    def query_by_query(self, query: str) -> list[dict]:
        """Get all retrieval records for a specific query."""
        rows = self._conn.execute(
            "SELECT * FROM retrieval_log WHERE query = ? ORDER BY trust_score DESC",
            (query,),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_by_source(self, source: str) -> list[dict]:
        """Get all retrieval records from a specific source."""
        rows = self._conn.execute(
            "SELECT * FROM retrieval_log WHERE source = ? ORDER BY timestamp DESC",
            (source,),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_low_trust(self, threshold: float = 0.5) -> list[dict]:
        """Get all records with trust score below threshold."""
        rows = self._conn.execute(
            "SELECT * FROM retrieval_log WHERE trust_score < ? ORDER BY trust_score ASC",
            (threshold,),
        ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        """Return summary statistics of the audit log."""
        row = self._conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_trusted = 1 THEN 1 ELSE 0 END) as trusted,
                SUM(CASE WHEN is_trusted = 0 THEN 1 ELSE 0 END) as untrusted,
                AVG(trust_score) as avg_score,
                COUNT(DISTINCT query) as unique_queries
            FROM retrieval_log
        """).fetchone()
        return dict(row)

    def close(self) -> None:
        self._conn.close()

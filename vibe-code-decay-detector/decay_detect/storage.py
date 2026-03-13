"""SQLite storage for per-commit architecture metrics."""

import sqlite3
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CommitMetrics:
    commit_hash: str
    timestamp: int
    author: str
    message: str
    edge_count: int
    cyclic_dep_count: int
    file_count: int
    churn_additions: int
    churn_deletions: int
    churn_files_changed: int


@dataclass
class RevertPattern:
    commit_hash: str
    file_path: str
    pattern_type: str  # "add-delete" or "rapid-edit"
    detail: str


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS commit_metrics (
    commit_hash TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    author TEXT,
    message TEXT,
    edge_count INTEGER DEFAULT 0,
    cyclic_dep_count INTEGER DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    churn_additions INTEGER DEFAULT 0,
    churn_deletions INTEGER DEFAULT 0,
    churn_files_changed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS revert_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_ts ON commit_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_revert_commit ON revert_patterns(commit_hash);
"""


class MetricsDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(DB_SCHEMA)
        self.conn.commit()

    def upsert_metrics(self, m: CommitMetrics):
        self.conn.execute(
            """INSERT OR REPLACE INTO commit_metrics
               (commit_hash, timestamp, author, message,
                edge_count, cyclic_dep_count, file_count,
                churn_additions, churn_deletions, churn_files_changed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (m.commit_hash, m.timestamp, m.author, m.message,
             m.edge_count, m.cyclic_dep_count, m.file_count,
             m.churn_additions, m.churn_deletions, m.churn_files_changed),
        )
        self.conn.commit()

    def insert_revert_pattern(self, p: RevertPattern):
        self.conn.execute(
            """INSERT INTO revert_patterns (commit_hash, file_path, pattern_type, detail)
               VALUES (?, ?, ?, ?)""",
            (p.commit_hash, p.file_path, p.pattern_type, p.detail),
        )
        self.conn.commit()

    def get_all_metrics(self) -> list[CommitMetrics]:
        rows = self.conn.execute(
            "SELECT * FROM commit_metrics ORDER BY timestamp ASC"
        ).fetchall()
        return [CommitMetrics(**dict(r)) for r in rows]

    def get_all_revert_patterns(self) -> list[RevertPattern]:
        rows = self.conn.execute(
            "SELECT commit_hash, file_path, pattern_type, detail FROM revert_patterns"
        ).fetchall()
        return [RevertPattern(**dict(r)) for r in rows]

    def has_commit(self, commit_hash: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM commit_metrics WHERE commit_hash = ?", (commit_hash,)
        ).fetchone()
        return row is not None

    def close(self):
        self.conn.close()

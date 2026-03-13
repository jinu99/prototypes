"""SQLite-based fact database for storing extracted facts."""

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Fact:
    entity: str
    attribute: str
    value: str
    source_file: str
    chapter: str
    line_start: int
    line_end: int
    raw_sentence: str
    id: Optional[int] = None
    embedding: Optional[list[float]] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("embedding", None)
        d.pop("id", None)
        return d

    def summary(self) -> str:
        return f"{self.entity}.{self.attribute} = {self.value}"


DB_NAME = ".consistency.db"


def db_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / DB_NAME


def init_db(project_dir: str | Path) -> sqlite3.Connection:
    """Create or open the fact database."""
    path = db_path(project_dir)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            attribute TEXT NOT NULL,
            value TEXT NOT NULL,
            source_file TEXT NOT NULL,
            chapter TEXT NOT NULL,
            line_start INTEGER,
            line_end INTEGER,
            raw_sentence TEXT,
            embedding BLOB
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity ON facts(entity)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_source ON facts(source_file)
    """)
    conn.commit()
    return conn


def insert_fact(conn: sqlite3.Connection, fact: Fact) -> int:
    embedding_blob = None
    if fact.embedding is not None:
        embedding_blob = json.dumps(fact.embedding).encode()
    cur = conn.execute(
        """INSERT INTO facts (entity, attribute, value, source_file, chapter,
           line_start, line_end, raw_sentence, embedding)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fact.entity, fact.attribute, fact.value, fact.source_file,
         fact.chapter, fact.line_start, fact.line_end, fact.raw_sentence,
         embedding_blob),
    )
    conn.commit()
    return cur.lastrowid


def get_all_facts(conn: sqlite3.Connection) -> list[Fact]:
    rows = conn.execute("SELECT * FROM facts").fetchall()
    facts = []
    for row in rows:
        emb = json.loads(row[9]) if row[9] else None
        facts.append(Fact(
            id=row[0], entity=row[1], attribute=row[2], value=row[3],
            source_file=row[4], chapter=row[5], line_start=row[6],
            line_end=row[7], raw_sentence=row[8], embedding=emb,
        ))
    return facts


def get_facts_by_entity(conn: sqlite3.Connection, entity: str) -> list[Fact]:
    rows = conn.execute(
        "SELECT * FROM facts WHERE LOWER(entity) = LOWER(?)", (entity,)
    ).fetchall()
    facts = []
    for row in rows:
        emb = json.loads(row[9]) if row[9] else None
        facts.append(Fact(
            id=row[0], entity=row[1], attribute=row[2], value=row[3],
            source_file=row[4], chapter=row[5], line_start=row[6],
            line_end=row[7], raw_sentence=row[8], embedding=emb,
        ))
    return facts


def clear_facts_for_file(conn: sqlite3.Connection, source_file: str):
    conn.execute("DELETE FROM facts WHERE source_file = ?", (source_file,))
    conn.commit()


def fact_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

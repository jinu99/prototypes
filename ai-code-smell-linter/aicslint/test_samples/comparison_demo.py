"""Comparison demo: patterns aicslint catches that Pylint misses.

Run: pylint comparison_demo.py  →  no relevant warnings
Run: aicslint scan comparison_demo.py  →  catches both patterns
"""

from abc import ABC, abstractmethod


# ── Pattern 1: Catch-and-rethrow (ACS002) ────────────────────
# Pylint does NOT flag this. It's syntactically valid Python.
# But it's a useless pattern that AI commonly generates.
def save_user(user_data):
    try:
        db = get_connection()
        db.execute("INSERT INTO users VALUES (?)", user_data)
        db.commit()
    except Exception as e:
        raise e  # ← Pylint says nothing. aicslint flags ACS002.


# ── Pattern 2: Unnecessary abstraction (ACS005) ─────────────
# Pylint has no concept of "single implementation abstract class".
# This is premature abstraction that AI loves to generate.
class IDataStore(ABC):
    @abstractmethod
    def get(self, key: str): ...

    @abstractmethod
    def set(self, key: str, value: str): ...

class RedisDataStore(IDataStore):
    def get(self, key: str):
        return f"value_for_{key}"

    def set(self, key: str, value: str):
        pass  # stub


# Stubs
def get_connection():
    return type('DB', (), {'execute': lambda *a: None, 'commit': lambda: None})()

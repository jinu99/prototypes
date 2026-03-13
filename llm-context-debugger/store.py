"""In-memory store for intercepted API call analyses."""

from __future__ import annotations
import time
from dataclasses import dataclass, field


@dataclass
class CallRecord:
    id: int
    timestamp: float
    model: str
    components: dict
    total_tokens: int
    warnings: list
    messages: list


class Store:
    def __init__(self) -> None:
        self._records: list[CallRecord] = []
        self._next_id = 1

    def add(self, analysis: dict) -> CallRecord:
        record = CallRecord(
            id=self._next_id,
            timestamp=time.time(),
            model=analysis["model"],
            components=analysis["components"],
            total_tokens=analysis["total_tokens"],
            warnings=analysis["warnings"],
            messages=analysis["messages"],
        )
        self._next_id += 1
        self._records.append(record)
        return record

    def get_all(self) -> list[dict]:
        return [self._to_dict(r) for r in self._records]

    def get(self, call_id: int) -> dict | None:
        for r in self._records:
            if r.id == call_id:
                return self._to_dict(r)
        return None

    def get_diff(self, id_a: int, id_b: int) -> dict | None:
        a = next((r for r in self._records if r.id == id_a), None)
        b = next((r for r in self._records if r.id == id_b), None)
        if not a or not b:
            return None
        return self._compute_diff(a, b)

    def _compute_diff(self, a: CallRecord, b: CallRecord) -> dict:
        """Compute context diff between two calls."""
        a_msgs = {self._msg_key(m): m for m in a.messages}
        b_msgs = {self._msg_key(m): m for m in b.messages}

        a_keys = set(a_msgs.keys())
        b_keys = set(b_msgs.keys())

        added = [b_msgs[k] for k in (b_keys - a_keys)]
        removed = [a_msgs[k] for k in (a_keys - b_keys)]
        unchanged = [b_msgs[k] for k in (a_keys & b_keys)]

        comp_diff = {}
        for comp in a.components:
            comp_diff[comp] = {
                "before": a.components[comp],
                "after": b.components.get(comp, 0),
                "delta": b.components.get(comp, 0) - a.components[comp],
            }

        return {
            "call_a": a.id,
            "call_b": b.id,
            "added": sorted(added, key=lambda m: m["index"]),
            "removed": sorted(removed, key=lambda m: m["index"]),
            "unchanged_count": len(unchanged),
            "component_diff": comp_diff,
            "total_before": a.total_tokens,
            "total_after": b.total_tokens,
        }

    @staticmethod
    def _msg_key(msg: dict) -> str:
        return f"{msg['role']}:{msg['preview']}"

    @staticmethod
    def _to_dict(r: CallRecord) -> dict:
        return {
            "id": r.id,
            "timestamp": r.timestamp,
            "model": r.model,
            "components": r.components,
            "total_tokens": r.total_tokens,
            "warnings": r.warnings,
            "messages": r.messages,
        }


store = Store()

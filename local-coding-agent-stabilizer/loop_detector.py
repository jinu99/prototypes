"""Loop detection: consecutive similar tool calls."""

import json
from dataclasses import dataclass, field

LOOP_THRESHOLD = 3  # Block after N consecutive similar calls


@dataclass
class SessionTracker:
    history: list[tuple[str, str]] = field(default_factory=list)
    consecutive_count: int = 0

    def check_and_record(self, tool_name: str, arguments: dict) -> tuple[bool, str | None]:
        """Check if this call creates a loop, then record it.

        Returns:
            (is_loop, reason)
        """
        # Normalize arguments to a comparable key
        arg_key = _normalize_args(arguments)
        current = (tool_name, arg_key)

        if self.history and self.history[-1] == current:
            self.consecutive_count += 1
        else:
            self.consecutive_count = 1

        self.history.append(current)

        # Keep history bounded
        if len(self.history) > 100:
            self.history = self.history[-50:]

        if self.consecutive_count >= LOOP_THRESHOLD:
            return True, (
                f"Loop detected: tool '{tool_name}' called {self.consecutive_count} times "
                f"consecutively with similar arguments"
            )

        return False, None


def _normalize_args(arguments: dict) -> str:
    """Create a normalized string key from arguments for comparison.

    Ignores minor differences like whitespace changes in content.
    """
    # Sort keys and create a stable representation
    simplified = {}
    for k, v in sorted(arguments.items()):
        if isinstance(v, str) and len(v) > 200:
            # For long strings, use a simplified version
            simplified[k] = v[:100].strip() + "..." + v[-50:].strip()
        else:
            simplified[k] = v
    return json.dumps(simplified, sort_keys=True)


# Per-session trackers
_trackers: dict[str, SessionTracker] = {}


def get_tracker(session_id: str) -> SessionTracker:
    if session_id not in _trackers:
        _trackers[session_id] = SessionTracker()
    return _trackers[session_id]


def clear_tracker(session_id: str):
    _trackers.pop(session_id, None)

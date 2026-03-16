"""Load chaos scenarios from YAML files."""

import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Scenario:
    name: str
    type: str  # duplicate, delay, reorder
    description: str = ""
    payload: dict = field(default_factory=dict)
    payloads: list[dict] = field(default_factory=list)  # for reorder
    count: int = 3  # for duplicate
    delay_seconds: float = 2.0  # for delay
    headers: dict = field(default_factory=dict)


def load_scenarios(path: str) -> list[Scenario]:
    """Load scenarios from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    scenarios = []
    for item in data.get("scenarios", []):
        s = Scenario(
            name=item["name"],
            type=item["type"],
            description=item.get("description", ""),
            payload=item.get("payload", {"event": "test", "data": "hello"}),
            payloads=item.get("payloads", []),
            count=item.get("count", 3),
            delay_seconds=item.get("delay_seconds", 2.0),
            headers=item.get("headers", {}),
        )
        scenarios.append(s)
    return scenarios


def get_default_scenarios() -> list[Scenario]:
    """Return the built-in 3 core scenarios."""
    return [
        Scenario(
            name="duplicate-delivery",
            type="duplicate",
            description="Send same webhook 3 times to verify idempotent handling",
            payload={
                "event": "payment.completed",
                "id": "evt_001",
                "amount": 5000,
                "currency": "KRW",
            },
            count=3,
        ),
        Scenario(
            name="delayed-delivery",
            type="delay",
            description="Send webhook after 2s delay to test timeout resilience",
            payload={
                "event": "order.shipped",
                "id": "evt_002",
                "tracking": "TRACK123",
            },
            delay_seconds=2.0,
        ),
        Scenario(
            name="out-of-order",
            type="reorder",
            description="Send 3 sequential events in reverse order",
            payloads=[
                {"event": "order.created", "id": "evt_010", "seq": 1},
                {"event": "order.paid", "id": "evt_011", "seq": 2},
                {"event": "order.shipped", "id": "evt_012", "seq": 3},
            ],
        ),
    ]


DEFAULT_SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"

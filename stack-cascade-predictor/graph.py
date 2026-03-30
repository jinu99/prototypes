"""Dependency graph: YAML parsing + BFS cascade propagation."""

from __future__ import annotations

import yaml
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Strength(Enum):
    HARD = "hard"
    SOFT = "soft"


class Status(Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"


@dataclass
class Dependency:
    target: str  # service id this depends on
    strength: Strength


@dataclass
class Service:
    id: str
    display_name: str
    type: str  # "external" or "internal"
    status_feed: str | None = None
    depends_on: list[Dependency] = field(default_factory=list)
    status: Status = Status.OPERATIONAL
    # Cascade-derived status (propagated from upstream)
    cascade_status: Status = Status.OPERATIONAL


@dataclass
class CascadeResult:
    """Result of a BFS cascade propagation."""
    affected: dict[str, Status]  # service_id -> propagated status
    path: dict[str, list[str]]  # service_id -> chain of services that caused it


class DependencyGraph:
    def __init__(self) -> None:
        self.services: dict[str, Service] = {}
        # Reverse adjacency: service_id -> list of (dependent_id, strength)
        self._dependents: dict[str, list[tuple[str, Strength]]] = {}

    def load_yaml(self, path: str | Path) -> None:
        """Parse YAML file and build graph."""
        with open(path) as f:
            data = yaml.safe_load(f)

        self.services.clear()
        self._dependents.clear()

        for sid, sdata in data.get("services", {}).items():
            deps = []
            for dep in sdata.get("depends_on", []):
                deps.append(Dependency(
                    target=dep["service"],
                    strength=Strength(dep["strength"]),
                ))
            svc = Service(
                id=sid,
                display_name=sdata.get("display_name", sid),
                type=sdata.get("type", "internal"),
                status_feed=sdata.get("status_feed"),
                depends_on=deps,
            )
            self.services[sid] = svc

        # Build reverse adjacency
        for sid, svc in self.services.items():
            for dep in svc.depends_on:
                self._dependents.setdefault(dep.target, []).append(
                    (sid, dep.strength)
                )

    def set_status(self, service_id: str, status: Status) -> CascadeResult:
        """Set direct status of a service and propagate via BFS."""
        if service_id not in self.services:
            raise KeyError(f"Unknown service: {service_id}")

        svc = self.services[service_id]
        svc.status = status
        svc.cascade_status = status

        return self._propagate(service_id, status)

    def _propagate(self, origin: str, origin_status: Status) -> CascadeResult:
        """BFS propagation from origin to all dependents."""
        affected: dict[str, Status] = {origin: origin_status}
        path: dict[str, list[str]] = {origin: [origin]}

        queue: deque[str] = deque([origin])

        while queue:
            current = queue.popleft()
            current_status = affected[current]

            for dependent_id, strength in self._dependents.get(current, []):
                # Determine propagated status based on dependency strength
                if strength == Strength.HARD:
                    prop_status = current_status
                else:  # SOFT
                    if current_status == Status.OUTAGE:
                        prop_status = Status.DEGRADED
                    elif current_status == Status.DEGRADED:
                        prop_status = Status.DEGRADED
                    else:
                        continue  # operational soft deps don't propagate

                # Only propagate if it worsens the current known status
                existing = affected.get(dependent_id)
                if existing and _severity(existing) >= _severity(prop_status):
                    continue

                affected[dependent_id] = prop_status
                path[dependent_id] = path[current] + [dependent_id]
                self.services[dependent_id].cascade_status = prop_status
                queue.append(dependent_id)

        return CascadeResult(affected=affected, path=path)

    def clear_all(self) -> None:
        """Reset all services to operational."""
        for svc in self.services.values():
            svc.status = Status.OPERATIONAL
            svc.cascade_status = Status.OPERATIONAL

    def to_dict(self) -> dict:
        """Serialize graph for API response."""
        nodes = []
        edges = []
        for svc in self.services.values():
            nodes.append({
                "id": svc.id,
                "display_name": svc.display_name,
                "type": svc.type,
                "status": svc.status.value,
                "cascade_status": svc.cascade_status.value,
                "has_feed": svc.status_feed is not None,
            })
            for dep in svc.depends_on:
                edges.append({
                    "source": dep.target,
                    "target": svc.id,
                    "strength": dep.strength.value,
                })
        return {"nodes": nodes, "edges": edges}


def _severity(status: Status) -> int:
    return {Status.OPERATIONAL: 0, Status.DEGRADED: 1, Status.OUTAGE: 2}[status]

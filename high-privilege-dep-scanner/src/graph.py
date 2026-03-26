"""Dependency graph and blast radius scoring."""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyzer import PackageCapabilities, CAPABILITY_WEIGHTS
from .deps import DepNode


DECAY_FACTOR = 0.5  # Each hop halves the propagated score


@dataclass
class ScoredPackage:
    name: str
    version: str
    direct_score: float  # from own capabilities
    propagated_score: float  # from transitive deps
    blast_radius: float  # combined
    capabilities: dict[str, int]  # category -> hit count
    dep_count: int  # number of transitive deps
    reverse_dep_count: int  # how many packages depend on this


def compute_blast_radius(
    dep_graph: dict[str, DepNode],
    capabilities: dict[str, PackageCapabilities],
) -> list[ScoredPackage]:
    """
    Compute blast radius for each package.

    Blast Radius = direct_score + propagated_score + reverse_dep_bonus

    Where:
    - direct_score: weighted sum of own capability hits
    - propagated_score: sum of children's scores * decay^depth
    - reverse_dep_bonus: log(1 + reverse_dep_count) * 5
    """
    import math

    # Build reverse dependency map
    reverse_deps: dict[str, set[str]] = {}
    for name, node in dep_graph.items():
        for child in node.children:
            if child not in reverse_deps:
                reverse_deps[child] = set()
            reverse_deps[child].add(name)

    # Count transitive deps for each package
    def count_transitive(name: str, visited: set[str] | None = None) -> int:
        if visited is None:
            visited = set()
        if name in visited or name not in dep_graph:
            return 0
        visited.add(name)
        count = 0
        for child in dep_graph[name].children:
            count += 1 + count_transitive(child, visited)
        return count

    # Compute propagated score with decay
    def propagated_score(name: str, depth: int = 0, visited: set[str] | None = None) -> float:
        if visited is None:
            visited = set()
        if name in visited or name not in dep_graph:
            return 0.0
        visited.add(name)

        total = 0.0
        for child in dep_graph[name].children:
            child_caps = capabilities.get(child)
            child_direct = child_caps.direct_score if child_caps else 0.0
            decay = DECAY_FACTOR ** (depth + 1)
            total += child_direct * decay
            total += propagated_score(child, depth + 1, visited)
        return total

    results = []
    for name, node in dep_graph.items():
        caps = capabilities.get(name)
        direct = caps.direct_score if caps else 0.0
        propagated = propagated_score(name)
        rev_count = len(reverse_deps.get(name, set()))
        rev_bonus = math.log1p(rev_count) * 5

        cap_summary = {}
        if caps:
            for cat, hits in caps.capabilities.items():
                cap_summary[cat] = len(hits)

        blast = direct + propagated + rev_bonus

        results.append(ScoredPackage(
            name=name,
            version=node.version,
            direct_score=round(direct, 2),
            propagated_score=round(propagated, 2),
            blast_radius=round(blast, 2),
            capabilities=cap_summary,
            dep_count=count_transitive(name),
            reverse_dep_count=rev_count,
        ))

    results.sort(key=lambda x: x.blast_radius, reverse=True)
    return results

"""Dependency graph metrics: edge count, cyclic dependencies."""

from collections import defaultdict


def build_dependency_graph(
    edges: list[tuple[str, str]],
) -> dict[str, set[str]]:
    """Build adjacency list from import edges."""
    graph: dict[str, set[str]] = defaultdict(set)
    for from_mod, to_mod in edges:
        graph[from_mod].add(to_mod)
    return dict(graph)


def count_edges(graph: dict[str, set[str]]) -> int:
    """Count total edges in dependency graph."""
    return sum(len(deps) for deps in graph.values())


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find all cycles in the dependency graph using DFS."""
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node: str, path: list[str]):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    all_nodes = set(graph.keys())
    for deps in graph.values():
        all_nodes.update(deps)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def count_cyclic_dependencies(graph: dict[str, set[str]]) -> int:
    """Count unique cyclic dependency pairs."""
    cycles = find_cycles(graph)
    cyclic_pairs = set()
    for cycle in cycles:
        for i in range(len(cycle) - 1):
            pair = tuple(sorted([cycle[i], cycle[i + 1]]))
            cyclic_pairs.add(pair)
    return len(cyclic_pairs)

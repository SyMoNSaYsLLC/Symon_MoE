"""Dependency graph management for the planning layer."""
from __future__ import annotations

from typing import Any


class DependencyGraph:
    """Track and query task/component dependency relationships."""

    def __init__(self) -> None:
        self._edges: dict[str, set[str]] = {}

    def add_node(self, node_id: str) -> None:
        self._edges.setdefault(node_id, set())

    def add_dependency(self, node_id: str, depends_on: str) -> dict[str, Any]:
        """Record that *node_id* depends on *depends_on*."""
        self.add_node(node_id)
        self.add_node(depends_on)
        if self._would_cycle(node_id, depends_on):
            raise ValueError(
                f"Adding dependency {node_id!r} → {depends_on!r} would create a cycle"
            )
        self._edges[node_id].add(depends_on)
        return {"node": node_id, "depends_on": depends_on}

    def remove_dependency(self, node_id: str, depends_on: str) -> dict[str, Any]:
        self._edges.get(node_id, set()).discard(depends_on)
        return {"node": node_id, "removed": depends_on}

    def dependencies(self, node_id: str) -> list[str]:
        return sorted(self._edges.get(node_id, set()))

    def dependents(self, node_id: str) -> list[str]:
        return sorted(nid for nid, deps in self._edges.items() if node_id in deps)

    def topology(self) -> list[str]:
        """Return nodes in topological order (dependencies first)."""
        visited: set[str] = set()
        order: list[str] = []

        def _visit(nid: str) -> None:
            if nid in visited:
                return
            visited.add(nid)
            for dep in self._edges.get(nid, set()):
                _visit(dep)
            order.append(nid)

        for node in self._edges:
            _visit(node)
        return order

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": sorted(self._edges.keys()),
            "edges": {k: sorted(v) for k, v in self._edges.items()},
            "topology": self.topology(),
        }

    def _would_cycle(self, from_node: str, to_node: str) -> bool:
        """Return True if adding from_node → to_node would create a cycle."""
        visited: set[str] = set()
        stack = [to_node]
        while stack:
            current = stack.pop()
            if current == from_node:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._edges.get(current, set()))
        return False

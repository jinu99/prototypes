"""File-to-service mapper.

Maps file paths to services/layers based on directory pattern
configuration and parsed diagram data.
"""

import json
import fnmatch
from dataclasses import dataclass, asdict
from pathlib import Path

from .mermaid_parser import ParsedDiagram, Node


@dataclass
class MappingRule:
    """A rule that maps a directory pattern to a service/layer."""
    pattern: str         # glob pattern, e.g., "src/api/**"
    service: str         # service name from diagram
    layer: str = ""      # architectural layer
    description: str = ""


@dataclass
class MappingConfig:
    """Configuration for file-to-service mapping."""
    project_root: str
    rules: list[MappingRule]

    def to_dict(self) -> dict:
        return {
            "project_root": self.project_root,
            "rules": [asdict(r) for r in self.rules],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "MappingConfig":
        return cls(
            project_root=data["project_root"],
            rules=[MappingRule(**r) for r in data["rules"]],
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "MappingConfig":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


@dataclass
class FileContext:
    """Architecture context for a specific file."""
    file_path: str
    service: str
    layer: str
    related_services: list[str]
    description: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class ContextMapper:
    """Maps file paths to architectural context using rules and diagram data."""

    def __init__(self, config: MappingConfig, diagram: ParsedDiagram | None = None):
        self.config = config
        self.diagram = diagram
        self._node_map: dict[str, Node] = {}
        self._relation_map: dict[str, list[str]] = {}

        if diagram:
            for node in diagram.nodes:
                self._node_map[node.id] = node
                self._node_map[node.label.lower()] = node
            for rel in diagram.relationships:
                self._relation_map.setdefault(rel.source, []).append(rel.target)
                self._relation_map.setdefault(rel.target, []).append(rel.source)

    def get_context(self, file_path: str) -> FileContext | None:
        """Get architectural context for a file path."""
        # Normalize path relative to project root
        try:
            rel_path = str(Path(file_path).relative_to(self.config.project_root))
        except ValueError:
            rel_path = file_path

        # Find matching rule
        matched_rule = None
        for rule in self.config.rules:
            if fnmatch.fnmatch(rel_path, rule.pattern):
                matched_rule = rule
                break

        if not matched_rule:
            return None

        # Find related services from diagram
        related = []
        service_id = matched_rule.service
        if service_id in self._relation_map:
            related = list(set(self._relation_map[service_id]))

        # Get description from diagram node
        desc = matched_rule.description
        if not desc and service_id in self._node_map:
            desc = self._node_map[service_id].description

        return FileContext(
            file_path=rel_path,
            service=matched_rule.service,
            layer=matched_rule.layer,
            related_services=related,
            description=desc,
        )

    def get_all_contexts(self) -> list[FileContext]:
        """Get context for all known patterns (useful for generating docs)."""
        contexts = []
        seen = set()
        for rule in self.config.rules:
            key = (rule.service, rule.layer)
            if key in seen:
                continue
            seen.add(key)

            related = list(set(self._relation_map.get(rule.service, [])))
            desc = rule.description
            if not desc and rule.service in self._node_map:
                desc = self._node_map[rule.service].description

            contexts.append(FileContext(
                file_path=rule.pattern,
                service=rule.service,
                layer=rule.layer,
                related_services=related,
                description=desc,
            ))
        return contexts

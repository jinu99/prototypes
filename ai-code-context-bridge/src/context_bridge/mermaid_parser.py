"""Mermaid C4/flowchart diagram parser.

Parses Mermaid diagram text and extracts services, layers,
and communication relationships as structured JSON.
"""

import re
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class DiagramType(str, Enum):
    C4_CONTEXT = "c4_context"
    C4_CONTAINER = "c4_container"
    FLOWCHART = "flowchart"


@dataclass
class Node:
    id: str
    label: str
    type: str  # "system", "container", "person", "service", "component"
    technology: str = ""
    description: str = ""
    layer: str = ""  # e.g., "frontend", "backend", "database"


@dataclass
class Relationship:
    source: str
    target: str
    label: str = ""
    technology: str = ""


@dataclass
class ParsedDiagram:
    type: DiagramType
    nodes: list[Node] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "nodes": [asdict(n) for n in self.nodes],
            "relationships": [asdict(r) for r in self.relationships],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def detect_diagram_type(text: str) -> DiagramType:
    """Detect the type of Mermaid diagram from its text."""
    stripped = text.strip()
    if re.search(r"C4Context", stripped, re.IGNORECASE):
        return DiagramType.C4_CONTEXT
    if re.search(r"C4Container", stripped, re.IGNORECASE):
        return DiagramType.C4_CONTAINER
    if re.match(r"(flowchart|graph)\s+(TB|BT|LR|RL)", stripped):
        return DiagramType.FLOWCHART
    # Default to flowchart for graph definitions
    if re.match(r"(flowchart|graph)", stripped):
        return DiagramType.FLOWCHART
    return DiagramType.FLOWCHART


def _parse_c4_args(args_str: str) -> list[str]:
    """Parse comma-separated arguments, respecting quotes."""
    args = []
    current = []
    in_quotes = False
    quote_char = None
    for ch in args_str:
        if ch in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = ch
        elif ch == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
        elif ch == "," and not in_quotes:
            args.append("".join(current).strip().strip("\"'"))
            current = []
            continue
        else:
            current.append(ch)
    if current:
        args.append("".join(current).strip().strip("\"'"))
    return args


def _infer_layer(node_type: str, technology: str, label: str) -> str:
    """Infer architectural layer from node metadata."""
    tech_lower = technology.lower() if technology else ""
    label_lower = label.lower()

    if node_type == "person":
        return "external"
    if node_type == "system_ext":
        return "external"
    if any(kw in tech_lower for kw in ["react", "vue", "angular", "html", "css", "browser"]):
        return "frontend"
    if any(kw in tech_lower for kw in ["postgres", "mysql", "sqlite", "redis", "mongo", "db"]):
        return "database"
    if any(kw in tech_lower for kw in ["kafka", "rabbitmq", "sqs", "queue", "mq"]):
        return "messaging"
    if any(kw in tech_lower for kw in [
        "python", "fastapi", "flask", "django", "node", "express",
        "java", "spring", "go", "rust", "celery",
    ]):
        return "backend"
    if any(kw in label_lower for kw in ["api", "gateway", "backend", "server"]):
        return "backend"
    if any(kw in label_lower for kw in ["web", "frontend", "ui", "client"]):
        return "frontend"
    if any(kw in label_lower for kw in ["database", "db", "store", "cache"]):
        return "database"
    return "backend"


def parse_c4(text: str, diagram_type: DiagramType) -> ParsedDiagram:
    """Parse C4 Context or Container diagram."""
    result = ParsedDiagram(type=diagram_type)

    # Match C4 element definitions — specific patterns before general ones
    # (System_Ext before System, ContainerDb before Container, etc.)
    c4_patterns = [
        ("person", r"Person_Ext\s*\(([^)]+)\)"),
        ("person", r"Person\s*\(([^)]+)\)"),
        ("system_ext", r"System_Ext\s*\(([^)]+)\)"),
        ("system", r"System\s*\(([^)]+)\)"),
        ("container_db", r"ContainerDb\s*\(([^)]+)\)"),
        ("container_queue", r"ContainerQueue\s*\(([^)]+)\)"),
        ("container", r"Container\s*\(([^)]+)\)"),
        ("component", r"Component\s*\(([^)]+)\)"),
    ]

    seen_ids = set()
    for node_type, pattern in c4_patterns:
        for match in re.finditer(pattern, text):
            args = _parse_c4_args(match.group(1))
            if len(args) < 2:
                continue
            node_id = args[0]
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)

            label = args[1] if len(args) > 1 else node_id
            tech = args[2] if len(args) > 2 else ""
            desc = args[3] if len(args) > 3 else ""

            base_type = node_type.split("_")[0]  # container_db -> container
            layer = _infer_layer(node_type, tech, label)

            result.nodes.append(Node(
                id=node_id,
                label=label,
                type=base_type,
                technology=tech,
                description=desc,
                layer=layer,
            ))

    # Match relationships: Rel(source, target, label, technology)
    rel_pattern = r"(?:Rel|Rel_D|Rel_U|Rel_L|Rel_R|BiRel)\s*\(([^)]+)\)"
    for match in re.finditer(rel_pattern, text):
        args = _parse_c4_args(match.group(1))
        if len(args) < 2:
            continue
        result.relationships.append(Relationship(
            source=args[0],
            target=args[1],
            label=args[2] if len(args) > 2 else "",
            technology=args[3] if len(args) > 3 else "",
        ))

    return result


def _clean_label(label: str) -> str:
    """Clean up a node label — remove wrapping parens from [(db)] shapes etc."""
    label = label.strip()
    if label.startswith("(") and label.endswith(")"):
        label = label[1:-1]
    return label


def parse_flowchart(text: str) -> ParsedDiagram:
    """Parse flowchart/graph diagram."""
    result = ParsedDiagram(type=DiagramType.FLOWCHART)
    nodes: dict[str, Node] = {}

    # Parse subgraphs as layer groupings
    subgraph_stack: list[str] = []
    node_layers: dict[str, str] = {}

    for line in text.split("\n"):
        line = line.strip()

        # Track subgraph context
        sg_match = re.match(r"subgraph\s+(.+?)(?:\s*\[(.+?)\])?\s*$", line)
        if sg_match:
            layer_name = sg_match.group(2) or sg_match.group(1)
            subgraph_stack.append(layer_name.strip('"').strip("'"))
            continue
        if line == "end" and subgraph_stack:
            subgraph_stack.pop()
            continue

        # Parse node definitions and edges
        # Pattern: A[Label] --> B[Label]  or  A --> B
        edge_match = re.match(
            r"(\w+)(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\}|(?:\[\[([^\]]*)\]\]))?",
            line,
        )

        # Detect edges: -->, --->, -.->  etc.
        arrow_pattern = (
            r"(\w+)(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\})?\s*"
            r"(-->|---->|-.->|==>|--\s+[^-]+\s+-->|--\s+[^-]+\s+-.->)"
            r"\s*(?:\|([^|]*)\|)?\s*"
            r"(\w+)(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\})?"
        )

        for match in re.finditer(arrow_pattern, line):
            src_id = match.group(1)
            src_label = _clean_label(match.group(2) or match.group(3) or match.group(4) or src_id)
            edge_label = match.group(6) or ""
            tgt_id = match.group(7)
            tgt_label = _clean_label(match.group(8) or match.group(9) or match.group(10) or tgt_id)

            current_layer = subgraph_stack[-1] if subgraph_stack else ""

            if src_id not in nodes:
                shape = "round" if match.group(3) else "diamond" if match.group(4) else "rect"
                nodes[src_id] = Node(
                    id=src_id, label=src_label, type="service",
                    layer=node_layers.get(src_id, current_layer),
                )
            if tgt_id not in nodes:
                nodes[tgt_id] = Node(
                    id=tgt_id, label=tgt_label, type="service",
                    layer=node_layers.get(tgt_id, current_layer),
                )

            # Update layer if in subgraph
            if current_layer:
                node_layers[src_id] = current_layer
                if src_id in nodes:
                    nodes[src_id].layer = current_layer

            result.relationships.append(Relationship(
                source=src_id, target=tgt_id, label=edge_label.strip(),
            ))

        # Standalone node definition (no edge)
        if not re.search(r"-->|-.->|==>", line) and not line.startswith("subgraph"):
            standalone = re.match(
                r"(\w+)\[([^\]]+)\]|(\w+)\(([^)]+)\)|(\w+)\{([^}]+)\}", line
            )
            if standalone:
                groups = standalone.groups()
                nid = groups[0] or groups[2] or groups[4]
                nlabel = _clean_label(groups[1] or groups[3] or groups[5])
                if nid and nid not in nodes:
                    current_layer = subgraph_stack[-1] if subgraph_stack else ""
                    nodes[nid] = Node(
                        id=nid, label=nlabel, type="service",
                        layer=node_layers.get(nid, current_layer),
                    )
                    if current_layer:
                        node_layers[nid] = current_layer

    result.nodes = list(nodes.values())
    return result


def parse_mermaid(text: str) -> ParsedDiagram:
    """Parse a Mermaid diagram string and return structured data."""
    diagram_type = detect_diagram_type(text)
    if diagram_type in (DiagramType.C4_CONTEXT, DiagramType.C4_CONTAINER):
        return parse_c4(text, diagram_type)
    return parse_flowchart(text)


def parse_mermaid_file(path: str | Path) -> ParsedDiagram:
    """Parse a Mermaid diagram from a file."""
    content = Path(path).read_text(encoding="utf-8")

    # Extract mermaid block from markdown if present
    mermaid_block = re.search(r"```mermaid\s*\n(.*?)```", content, re.DOTALL)
    if mermaid_block:
        content = mermaid_block.group(1)

    return parse_mermaid(content)

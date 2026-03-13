"""MCP server exposing architecture context tools.

Allows AI agents (Claude Code, etc.) to query file-level
architecture context via tool calls.
"""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .mermaid_parser import parse_mermaid_file
from .mapper import ContextMapper, MappingConfig

mcp = FastMCP("architecture-context-bridge")

# Global state — loaded on startup
_mapper: ContextMapper | None = None
_diagram_json: dict | None = None


def load_project(diagram_path: str, config_path: str) -> None:
    """Load diagram and mapping config into memory."""
    global _mapper, _diagram_json

    diagram = parse_mermaid_file(diagram_path)
    config = MappingConfig.from_file(config_path)
    _mapper = ContextMapper(config, diagram)
    _diagram_json = diagram.to_dict()


@mcp.tool()
def get_file_context(file_path: str) -> str:
    """Get architectural context for a specific file.

    Returns which service/layer the file belongs to,
    related services, and communication relationships.

    Args:
        file_path: Path to the file (absolute or relative to project root)
    """
    if _mapper is None:
        return json.dumps({"error": "No project loaded. Start server with --diagram and --config."})

    ctx = _mapper.get_context(file_path)
    if ctx is None:
        return json.dumps({
            "error": f"No mapping found for '{file_path}'",
            "hint": "File path may not match any configured pattern.",
        })

    return ctx.to_json()


@mcp.tool()
def list_services() -> str:
    """List all services/components in the architecture diagram.

    Returns all nodes with their type, layer, and technology.
    """
    if _diagram_json is None:
        return json.dumps({"error": "No project loaded."})

    return json.dumps(_diagram_json["nodes"], indent=2, ensure_ascii=False)


@mcp.tool()
def list_relationships() -> str:
    """List all communication relationships between services.

    Returns source → target pairs with labels and technologies.
    """
    if _diagram_json is None:
        return json.dumps({"error": "No project loaded."})

    return json.dumps(_diagram_json["relationships"], indent=2, ensure_ascii=False)


@mcp.tool()
def get_service_context(service_id: str) -> str:
    """Get full context for a specific service/component.

    Args:
        service_id: The service ID as defined in the architecture diagram
    """
    if _diagram_json is None:
        return json.dumps({"error": "No project loaded."})

    # Find node
    node = None
    for n in _diagram_json["nodes"]:
        if n["id"] == service_id:
            node = n
            break

    if node is None:
        return json.dumps({"error": f"Service '{service_id}' not found."})

    # Find relationships
    incoming = []
    outgoing = []
    for rel in _diagram_json["relationships"]:
        if rel["source"] == service_id:
            outgoing.append(rel)
        if rel["target"] == service_id:
            incoming.append(rel)

    # Find file patterns
    patterns = []
    if _mapper:
        for rule in _mapper.config.rules:
            if rule.service == service_id:
                patterns.append(rule.pattern)

    return json.dumps({
        "service": node,
        "incoming_relationships": incoming,
        "outgoing_relationships": outgoing,
        "file_patterns": patterns,
    }, indent=2, ensure_ascii=False)


def run_server(diagram_path: str, config_path: str) -> None:
    """Start the MCP server with loaded project data."""
    load_project(diagram_path, config_path)
    mcp.run(transport="stdio")

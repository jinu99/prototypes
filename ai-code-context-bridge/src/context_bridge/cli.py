"""CLI entry point for ai-code-context-bridge."""

import json
import sys
from pathlib import Path

import click

from .mermaid_parser import parse_mermaid_file
from .mapper import ContextMapper, MappingConfig
from .claude_md_gen import generate_claude_md
from .intent_hook import install_hook, record_intent


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AI Code Context Bridge — architecture context for AI coding agents."""
    pass


@cli.command()
@click.argument("diagram", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output JSON file")
@click.option("--pretty/--no-pretty", default=True, help="Pretty print JSON")
def parse(diagram: str, output: str | None, pretty: bool):
    """Parse a Mermaid diagram and extract architecture as JSON."""
    result = parse_mermaid_file(diagram)
    json_str = result.to_json(indent=2 if pretty else None)

    if output:
        Path(output).write_text(json_str, encoding="utf-8")
        click.echo(f"Written to {output}")
        click.echo(f"  {len(result.nodes)} nodes, {len(result.relationships)} relationships")
    else:
        click.echo(json_str)


@cli.command()
@click.argument("file_path")
@click.option("-d", "--diagram", type=click.Path(exists=True), required=True,
              help="Mermaid diagram file")
@click.option("-c", "--config", type=click.Path(exists=True), required=True,
              help="Mapping config JSON file")
def lookup(file_path: str, diagram: str, config: str):
    """Look up architectural context for a file path."""
    parsed = parse_mermaid_file(diagram)
    mapping = MappingConfig.from_file(config)
    mapper = ContextMapper(mapping, parsed)

    ctx = mapper.get_context(file_path)
    if ctx is None:
        click.echo(json.dumps({
            "error": f"No mapping found for '{file_path}'",
            "hint": "Check your mapping config patterns.",
        }, indent=2))
        sys.exit(1)
    else:
        click.echo(ctx.to_json())


@cli.command("generate-claude-md")
@click.option("-d", "--diagram", type=click.Path(exists=True), required=True,
              help="Mermaid diagram file")
@click.option("-c", "--config", type=click.Path(exists=True), required=True,
              help="Mapping config JSON file")
@click.option("-o", "--output", type=click.Path(), default="CLAUDE.md",
              help="Output file path")
@click.option("--project-name", default="Project", help="Project name for header")
def generate_claude_md_cmd(diagram: str, config: str, output: str, project_name: str):
    """Generate a CLAUDE.md file from diagram and mapping config."""
    parsed = parse_mermaid_file(diagram)
    mapping = MappingConfig.from_file(config)
    md = generate_claude_md(parsed, mapping, project_name)

    Path(output).write_text(md, encoding="utf-8")
    click.echo(f"Generated {output}")


@cli.command("serve")
@click.option("-d", "--diagram", type=click.Path(exists=True), required=True,
              help="Mermaid diagram file")
@click.option("-c", "--config", type=click.Path(exists=True), required=True,
              help="Mapping config JSON file")
def serve(diagram: str, config: str):
    """Start MCP server for AI agent integration."""
    from .mcp_server import run_server
    click.echo("Starting MCP server (stdio transport)...", err=True)
    click.echo(f"  Diagram: {diagram}", err=True)
    click.echo(f"  Config:  {config}", err=True)
    run_server(diagram, config)


@cli.command("install-hook")
@click.argument("repo_path", type=click.Path(exists=True), default=".")
def install_hook_cmd(repo_path: str):
    """Install git hook for change intent recording."""
    result = install_hook(repo_path)
    click.echo(result)


@cli.command("record-intent")
@click.argument("repo_path", type=click.Path(exists=True), default=".")
@click.option("-f", "--file", "files", multiple=True, required=True,
              help="Changed file path")
@click.option("-m", "--message", default="", help="Intent description")
def record_intent_cmd(repo_path: str, files: tuple[str, ...], message: str):
    """Manually record a change intent."""
    path = record_intent(repo_path, list(files), message)
    click.echo(f"Intent recorded: {path}")


@cli.command()
@click.option("-d", "--diagram", type=click.Path(exists=True), required=True,
              help="Mermaid diagram file")
@click.option("-c", "--config", type=click.Path(exists=True), required=True,
              help="Mapping config JSON file")
@click.option("--project-name", default="Project", help="Project name")
def demo(diagram: str, config: str, project_name: str):
    """Run the before/after context injection demo."""
    from .demo import run_demo
    run_demo(diagram, config, project_name)


def main():
    cli()

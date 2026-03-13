"""CLI interface for the consistency checker."""

import json
import sys
from pathlib import Path

import click

from .checker import check_consistency, embed_facts
from .context import generate_context_snippet
from .db import (
    clear_facts_for_file,
    fact_count,
    get_all_facts,
    init_db,
    insert_fact,
)
from .extractor import extract_from_file


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Long Context Consistency — fact extraction and contradiction detection."""
    pass


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
def init(directory: str):
    """Initialize a text directory with a fact database."""
    project_dir = Path(directory).resolve()
    conn = init_db(project_dir)
    count = fact_count(conn)
    conn.close()
    click.echo(f"✓ Initialized consistency DB at {project_dir}")
    click.echo(f"  Database: {project_dir / '.consistency.db'}")
    click.echo(f"  Existing facts: {count}")


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--project-dir", "-d", type=click.Path(exists=True), default=None,
              help="Project directory (default: file's parent)")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def extract(file: str, project_dir: str | None, json_output: bool):
    """Extract facts from a text file and store in the database."""
    filepath = Path(file).resolve()
    proj = Path(project_dir).resolve() if project_dir else filepath.parent

    conn = init_db(proj)

    # Clear old facts from this file
    clear_facts_for_file(conn, filepath.name)

    # Extract
    click.echo(f"Extracting facts from {filepath.name}...")
    facts = extract_from_file(filepath)

    if not facts:
        click.echo("No facts extracted. The text may not match extraction patterns.")
        conn.close()
        return

    # Embed
    click.echo(f"Embedding {len(facts)} facts...")
    embeddings = embed_facts(facts)
    for i, fact in enumerate(facts):
        fact.embedding = embeddings[i]

    # Store
    for fact in facts:
        insert_fact(conn, fact)

    total = fact_count(conn)
    conn.close()

    if json_output:
        click.echo(json.dumps([f.to_dict() for f in facts], indent=2))
    else:
        click.echo(f"\n✓ Extracted {len(facts)} facts from {filepath.name}")
        click.echo(f"  Total facts in DB: {total}\n")
        for f in facts:
            click.echo(f"  [{f.chapter}] {f.summary()}")


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--project-dir", "-d", type=click.Path(exists=True), default=None)
@click.option("--threshold", "-t", type=float, default=0.6,
              help="Similarity threshold for cross-attribute detection (default: 0.6)")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def check(file: str, project_dir: str | None, threshold: float, json_output: bool):
    """Check a text file for inconsistencies against the fact database."""
    filepath = Path(file).resolve()
    proj = Path(project_dir).resolve() if project_dir else filepath.parent

    conn = init_db(proj)
    existing_facts = get_all_facts(conn)

    if not existing_facts:
        click.echo("No existing facts in DB. Run 'extract' first.")
        conn.close()
        return

    # Extract new facts (don't store yet)
    click.echo(f"Extracting facts from {filepath.name}...")
    new_facts = extract_from_file(filepath)

    if not new_facts:
        click.echo("No facts found in the new file.")
        conn.close()
        return

    # Embed new facts
    click.echo(f"Embedding {len(new_facts)} new facts...")
    new_embeddings = embed_facts(new_facts)
    for i, f in enumerate(new_facts):
        f.embedding = new_embeddings[i]

    # Load existing embeddings
    for f in existing_facts:
        if f.embedding is None:
            from .checker import embed_fact
            f.embedding = embed_fact(f)

    # Check
    click.echo("Checking for inconsistencies...")
    issues = check_consistency(new_facts, existing_facts, threshold)

    conn.close()

    if json_output:
        click.echo(json.dumps([i.to_dict() for i in issues], indent=2))
    elif not issues:
        click.echo(f"\n✓ No inconsistencies found ({len(new_facts)} new facts checked against {len(existing_facts)} existing)")
    else:
        click.echo(f"\n⚠ Found {len(issues)} potential inconsistencies:\n")
        for issue in issues:
            click.echo(issue.report())
            click.echo()


@cli.command()
@click.argument("scene", type=click.Path(exists=True, dir_okay=False))
@click.option("--project-dir", "-d", type=click.Path(exists=True), default=None)
@click.option("--budget", "-b", type=int, default=2000, help="Token budget (default: 2000)")
def context(scene: str, project_dir: str | None, budget: int):
    """Generate a context snippet for a scene from the fact database."""
    filepath = Path(scene).resolve()
    proj = Path(project_dir).resolve() if project_dir else filepath.parent

    conn = init_db(proj)
    facts = get_all_facts(conn)
    conn.close()

    if not facts:
        click.echo("No facts in DB. Run 'extract' first.")
        return

    scene_text = filepath.read_text(encoding="utf-8")
    snippet = generate_context_snippet(scene_text, facts, budget)
    click.echo(snippet)


def main():
    cli()


if __name__ == "__main__":
    main()

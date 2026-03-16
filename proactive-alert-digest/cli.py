"""CLI interface for proactive-alert-digest."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click

from engine import load_config, poll_all
from renderer import render_digest
from slack import send_to_slack

DEFAULT_CONFIG = "digest.yaml"
SAMPLE_CONFIG = Path(__file__).parent / "sample_config.yaml"


@click.group()
def cli():
    """Proactive Alert Digest — morning monitoring digest generator."""
    pass


@cli.command()
@click.option("--output", "-o", default=DEFAULT_CONFIG, help="Output config file path")
def init(output: str):
    """Generate a sample YAML configuration file."""
    dest = Path(output)
    if dest.exists():
        click.confirm(f"{dest} already exists. Overwrite?", abort=True)
    shutil.copy(SAMPLE_CONFIG, dest)
    click.echo(f"✅ Sample config written to {dest}")
    click.echo(f"   Edit {dest} to configure your monitoring sources.")


@cli.command()
@click.option("--config", "-c", default=DEFAULT_CONFIG, help="Config file path")
@click.option("--slack/--no-slack", default=False, help="Send to Slack webhook")
@click.option("--output", "-o", default=None, help="Override output file path")
def run(config: str, slack: bool, output: str | None):
    """Poll all sources and generate the alert digest."""
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"❌ Config file not found: {config_path}", err=True)
        click.echo(f"   Run `digest init` to create a sample config.", err=True)
        sys.exit(1)

    click.echo(f"📋 Loading config from {config_path}...")
    cfg = load_config(config_path)

    click.echo(f"🔍 Polling {len(cfg['sources'])} source(s)...")
    alerts = poll_all(cfg)

    click.echo(f"📝 Generating digest ({len(alerts)} alert(s))...")
    digest = render_digest(alerts)

    # File output
    output_path = Path(output or cfg.get("output", {}).get("file", "./digest_output.md"))
    output_path.write_text(digest)
    click.echo(f"💾 Digest saved to {output_path}")

    # Slack output
    webhook = cfg.get("output", {}).get("slack_webhook", "")
    if slack and webhook:
        click.echo("📤 Sending to Slack...")
        ok = send_to_slack(webhook, digest)
        if ok:
            click.echo("✅ Slack delivery successful!")
        else:
            click.echo("❌ Slack delivery failed.", err=True)
    elif slack and not webhook:
        click.echo("⚠️  --slack flag set but no webhook configured in config.", err=True)

    click.echo("\nDone! ✨")


if __name__ == "__main__":
    cli()

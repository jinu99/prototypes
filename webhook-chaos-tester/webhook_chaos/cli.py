"""CLI entry point for webhook-chaos-tester."""

import click
from pathlib import Path
from webhook_chaos.engine import run_duplicate, run_delay, run_reorder, ScenarioResult
from webhook_chaos.loader import load_scenarios, get_default_scenarios, Scenario
from webhook_chaos.report import to_markdown, to_json
from webhook_chaos.echo_server import run_server


def _run_scenario(target: str, scenario: Scenario) -> ScenarioResult:
    if scenario.type == "duplicate":
        result = run_duplicate(
            target,
            payload=scenario.payload,
            count=scenario.count,
            headers=scenario.headers or None,
        )
    elif scenario.type == "delay":
        result = run_delay(
            target,
            payload=scenario.payload,
            delay_seconds=scenario.delay_seconds,
            headers=scenario.headers or None,
        )
    elif scenario.type == "reorder":
        result = run_reorder(
            target,
            payloads=scenario.payloads,
            headers=scenario.headers or None,
        )
    else:
        click.echo(click.style(f"  Unknown scenario type: {scenario.type}", fg="red"), err=True)
        return ScenarioResult(
            name=scenario.name,
            description=scenario.description,
            verdict="FAIL",
            reason=f"Unknown type: {scenario.type}",
        )
    result.name = scenario.name
    result.type = scenario.type
    if scenario.description:
        result.description = scenario.description
    return result


def _execute_scenarios(target, scenarios, fmt, output_file):
    """Shared logic for run and demo commands."""
    click.echo(f"Target: {click.style(target, fg='cyan')}")
    click.echo(f"Scenarios: {len(scenarios)}")
    click.echo()

    results: list[ScenarioResult] = []
    for i, s in enumerate(scenarios, 1):
        click.echo(f"[{i}/{len(scenarios)}] {click.style(s.name, bold=True)} ({s.type})...")
        result = _run_scenario(target, s)
        if result.verdict == "PASS":
            click.echo(f"  {click.style('PASS', fg='green')}: {result.reason}")
        else:
            click.echo(f"  {click.style('FAIL', fg='red')}: {result.reason}")
        results.append(result)

    click.echo()
    passed = sum(1 for r in results if r.verdict == "PASS")
    total = len(results)
    color = "green" if passed == total else ("yellow" if passed > 0 else "red")
    click.echo(click.style(f"Results: {passed}/{total} passed", fg=color, bold=True))

    if fmt == "markdown":
        report = to_markdown(results, target)
    else:
        report = to_json(results, target)

    if output_file:
        Path(output_file).write_text(report)
        click.echo(f"Report written to {output_file}")
    else:
        click.echo()
        click.echo(report)

    return results


@click.group()
def cli():
    """Webhook Chaos Tester — find idempotency and error-handling bugs."""
    pass


@cli.command()
@click.option("--target", "-t", required=True, help="Target webhook URL")
@click.option("--scenario", "-s", "scenario_file", default=None, help="YAML scenario file")
@click.option("--format", "-f", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
@click.option("--output", "-o", "output_file", default=None, help="Output file (default: stdout)")
def run(target, scenario_file, fmt, output_file):
    """Run chaos scenarios against a target webhook URL."""
    if scenario_file:
        click.echo(f"Loading scenarios from {scenario_file}...")
        scenarios = load_scenarios(scenario_file)
    else:
        click.echo("Using default scenarios (duplicate, delay, reorder)...")
        scenarios = get_default_scenarios()

    _execute_scenarios(target, scenarios, fmt, output_file)


@cli.command()
@click.option("--port", "-p", default=9876, help="Port for echo server")
@click.option("--reject-duplicates", is_flag=True, help="Return 409 on duplicate idempotency keys")
def echo(port, reject_duplicates):
    """Start a local echo server for testing."""
    click.echo(f"Starting echo server on {click.style(f'http://127.0.0.1:{port}', fg='cyan')}")
    if reject_duplicates:
        click.echo(click.style("  Mode: rejecting duplicate idempotency keys (409)", fg="yellow"))
    click.echo("  GET  /_requests  — view received webhooks")
    click.echo("  GET  /_reset     — clear received webhooks")
    click.echo("  POST /webhook    — receive webhooks")
    click.echo("Press Ctrl+C to stop.")
    click.echo()

    server = run_server(port=port, reject_duplicates=reject_duplicates)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nStopped.")
        server.shutdown()


@cli.command()
@click.option("--port", "-p", default=9876, help="Port for echo server")
@click.option("--scenario", "-s", "scenario_file", default=None, help="YAML scenario file")
@click.option("--format", "-f", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
@click.option("--output", "-o", "output_file", default=None, help="Output file")
def demo(port, scenario_file, fmt, output_file):
    """Run a self-contained demo: start echo server + run scenarios."""
    click.echo(f"Starting echo server on port {port}...")
    server = run_server(port=port)
    target = f"http://127.0.0.1:{port}/webhook"

    try:
        if scenario_file:
            scenarios = load_scenarios(scenario_file)
        else:
            scenarios = get_default_scenarios()
        _execute_scenarios(target, scenarios, fmt, output_file)
    finally:
        server.shutdown()


def main():
    cli()


if __name__ == "__main__":
    main()

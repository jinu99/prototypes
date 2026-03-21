"""CLI entry point for wasm-boundary-diagnostic."""

import sys
from pathlib import Path

import click
from rich.console import Console

from .cost_model import analyze_all
from .parser import parse_glue_code
from .recommender import get_recommendations
from .report import render_report


@click.command()
@click.argument("glue_file", type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON instead of rich terminal")
@click.option("--min-cost", type=click.Choice(["zero", "low", "medium", "high"]),
              default="zero", help="Only show functions at or above this cost level")
def main(glue_file: Path, as_json: bool, min_cost: str) -> None:
    """Analyze wasm-bindgen glue code for boundary serialization costs.

    GLUE_FILE: Path to a wasm-bindgen generated _bg.js file.
    """
    console = Console(stderr=True)

    source = glue_file.read_text()
    functions = parse_glue_code(source)

    if not functions:
        console.print("[yellow]No boundary functions found in the file.[/yellow]")
        sys.exit(1)

    results = analyze_all(functions)

    # Filter by min cost
    cost_order = ["zero", "low", "medium", "high"]
    min_idx = cost_order.index(min_cost)
    results = [r for r in results if cost_order.index(r.overall.value) >= min_idx]

    # Build recommendations
    recommendations: dict[str, list] = {}
    for r in results:
        recs = get_recommendations(r)
        if recs:
            recommendations[r.function.name] = recs

    if as_json:
        _output_json(glue_file, results, recommendations)
    else:
        out_console = Console()
        render_report(str(glue_file), results, recommendations, out_console)


def _output_json(
    glue_file: Path,
    results: list,
    recommendations: dict,
) -> None:
    """Output results as JSON."""
    import json

    data = {
        "file": str(glue_file),
        "functions": [
            {
                "name": r.function.name,
                "kind": r.function.kind,
                "line": r.function.line_number,
                "overall_cost": r.overall.value,
                "score": r.total_score,
                "params": [
                    {
                        "name": pc.param.name,
                        "type": pc.param.inferred_type,
                        "cost": pc.level.value,
                        "reason": pc.reason,
                    }
                    for pc in r.param_costs
                ],
                "return_type": r.function.return_type,
                "return_cost": r.return_cost.value,
                "recommendations": [
                    {
                        "pattern": rec.pattern,
                        "title": rec.title,
                        "description": rec.description,
                    }
                    for rec in recommendations.get(r.function.name, [])
                ],
            }
            for r in results
        ],
    }

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

"""Rich terminal display for mesh results.

Renders the routing, confidence, escalation, and final response
in a clear, transparent format so users can see the full decision chain.
"""

from __future__ import annotations

import sys

from agent_mesh.mesh import MeshResult, MeshStep
from agent_mesh.router import Complexity


# ANSI colors
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_MAGENTA = "\033[35m"
_BLUE = "\033[34m"


def _color(text: str, color: str) -> str:
    return f"{color}{text}{_RESET}"


def render_result(result: MeshResult, verbose: bool = False) -> None:
    """Print the full mesh result to stdout."""
    out = sys.stdout

    # Header
    out.write("\n")
    out.write(_color("═" * 60, _DIM) + "\n")
    out.write(_color("  LOCAL AGENT MESH", _BOLD + _CYAN) + "\n")
    out.write(_color("═" * 60, _DIM) + "\n\n")

    # Prompt
    out.write(_color("📝 Prompt: ", _BOLD))
    prompt_display = result.prompt
    if len(prompt_display) > 120:
        prompt_display = prompt_display[:117] + "..."
    out.write(f"{prompt_display}\n\n")

    # Pipeline steps
    out.write(_color("─── Pipeline ───", _DIM) + "\n")
    for i, step in enumerate(result.steps, 1):
        icon = _step_icon(step.action)
        color = _step_color(step.action)
        model_str = f" [{step.model}]" if step.model else ""
        out.write(
            f"  {_color(icon, color)} "
            f"{_color(step.action.upper(), _BOLD)}"
            f"{_color(model_str, _DIM)}"
            f" — {step.detail}"
            f" {_color(f'({step.duration_ms:.0f}ms)', _DIM)}\n"
        )

    out.write(_color("─" * 40, _DIM) + "\n\n")

    # Routing detail
    if result.routing:
        r = result.routing
        complexity_color = _GREEN if r.complexity == Complexity.SIMPLE else _YELLOW
        out.write(
            f"  {_color('Complexity:', _BOLD)} "
            f"{_color(r.complexity.value.upper(), complexity_color)} "
            f"(score: {r.score:.2f})\n"
        )
        out.write(f"  {_color('Routed to:', _BOLD)} {r.model}\n")

    # Confidence detail
    if result.confidence:
        c = result.confidence
        conf_color = _GREEN if c.score >= 0.6 else (_YELLOW if c.score >= 0.4 else _RED)
        out.write(
            f"  {_color('Confidence:', _BOLD)} "
            f"{_color(f'{c.score:.2f}', conf_color)} "
            f"({c.method})\n"
        )

    # Escalation
    if result.was_escalated:
        out.write(
            f"\n  {_color('⚡ ESCALATED', _RED + _BOLD)} "
            f"→ Re-generated with {_color(result.final_model, _BOLD)}\n"
        )
    else:
        out.write(
            f"\n  {_color('✓ ACCEPTED', _GREEN + _BOLD)} "
            f"— Final model: {result.final_model}\n"
        )

    out.write(f"\n  {_color('Total time:', _DIM)} {result.total_duration_ms:.0f}ms\n")

    # Response
    out.write("\n" + _color("─── Response ───", _DIM) + "\n\n")
    out.write(result.final_response + "\n")
    out.write("\n" + _color("═" * 60, _DIM) + "\n")

    # Verbose: show all routing reasons and confidence reasons
    if verbose:
        out.write("\n" + _color("─── Details ───", _DIM) + "\n")
        if result.routing:
            out.write(_color("\n  Routing reasons:", _BOLD) + "\n")
            for reason in result.routing.reasons:
                out.write(f"    • {reason}\n")
        if result.confidence:
            out.write(_color("\n  Confidence reasons:", _BOLD) + "\n")
            for reason in result.confidence.reasons:
                out.write(f"    • {reason}\n")
        out.write("\n")


def _step_icon(action: str) -> str:
    return {
        "route": "🔀",
        "generate": "🤖",
        "self_eval": "🔍",
        "escalate": "⚡",
    }.get(action, "•")


def _step_color(action: str) -> str:
    return {
        "route": _BLUE,
        "generate": _CYAN,
        "self_eval": _MAGENTA,
        "escalate": _RED,
    }.get(action, _RESET)

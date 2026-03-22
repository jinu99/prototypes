"""Generate HTML report from parsed session data."""

from pathlib import Path

from jinja2 import Template

from parser import PromptSegment
from detector import detect_mismatches, Mismatch


def _prompt_preview(text: str, max_len: int = 80) -> str:
    """Create a short preview of the prompt text."""
    first_line = text.strip().split("\n")[0]
    if len(first_line) > max_len:
        return first_line[:max_len] + "…"
    return first_line


def build_report_data(segments: list[PromptSegment]) -> dict:
    """Build template context from segments."""
    all_mismatches: list[list[Mismatch]] = []
    total_changes = 0
    segments_with_changes = 0

    enriched = []
    for seg in segments:
        mismatches = detect_mismatches(seg)
        all_mismatches.append(mismatches)
        total_changes += len(seg.file_changes)
        if seg.file_changes:
            segments_with_changes += 1

        enriched.append({
            "prompt_text": seg.prompt_text,
            "prompt_preview": _prompt_preview(seg.prompt_text),
            "prompt_timestamp": seg.prompt_timestamp,
            "tool_calls": seg.tool_calls,
            "file_changes": seg.file_changes,
            "mismatches": mismatches,
        })

    total_mismatches = sum(len(m) for m in all_mismatches)

    return {
        "segments": enriched,
        "total_segments": len(segments),
        "total_changes": total_changes,
        "total_mismatches": total_mismatches,
        "segments_with_changes": segments_with_changes,
    }


def generate_html(
    segments: list[PromptSegment],
    session_id: str,
    output_path: str | Path,
) -> Path:
    """Generate HTML report file."""
    output_path = Path(output_path)
    template_path = Path(__file__).parent / "template.html"

    with open(template_path) as f:
        tmpl = Template(f.read())

    data = build_report_data(segments)
    data["session_id"] = session_id

    html = tmpl.render(**data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    return output_path

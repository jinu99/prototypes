"""Before/after context injection demo.

Demonstrates how architecture context improves code generation
by showing what information an AI agent receives with and without
the context bridge.
"""

import json
from pathlib import Path

from .mermaid_parser import parse_mermaid_file
from .mapper import ContextMapper, MappingConfig
from .claude_md_gen import generate_claude_md


SAMPLE_PROMPTS = [
    {
        "task": "Add a new endpoint to the Order Service that cancels an order",
        "file": "services/order-service/src/api/routes.py",
    },
    {
        "task": "Fix the user authentication bug in the API Gateway",
        "file": "services/api-gateway/src/middleware/auth.ts",
    },
    {
        "task": "Add caching to the Product Service database queries",
        "file": "services/product-service/src/db/queries.py",
    },
]


def _format_without_context(prompt: dict) -> str:
    """Simulate what an AI agent sees WITHOUT context bridge."""
    return f"""## Without Context Bridge

**Task**: {prompt['task']}
**File**: {prompt['file']}

AI agent only knows:
- The file path
- The file contents (if it reads them)
- Generic programming knowledge

❌ Missing:
- Which service this file belongs to
- What layer it operates in
- Which other services it communicates with
- Architecture constraints and patterns
- Impact on downstream services
"""


def _format_with_context(prompt: dict, mapper: ContextMapper) -> str:
    """Simulate what an AI agent sees WITH context bridge."""
    ctx = mapper.get_context(prompt["file"])

    if ctx is None:
        return f"⚠️  No context found for {prompt['file']}"

    related = ", ".join(ctx.related_services) if ctx.related_services else "none"

    return f"""## With Context Bridge

**Task**: {prompt['task']}
**File**: {prompt['file']}

AI agent knows (via MCP tool call):
```json
{ctx.to_json()}
```

✅ Agent now understands:
- This file is part of **{ctx.service}** ({ctx.layer} layer)
- It communicates with: {related}
- {ctx.description or 'Service context loaded'}

→ The agent can now:
  1. Respect the service boundary
  2. Check if changes affect dependent services ({related})
  3. Follow the established patterns for this layer
  4. Generate code that fits the architecture
"""


def run_demo(diagram_path: str, config_path: str, project_name: str = "Project"):
    """Run the before/after comparison demo."""
    parsed = parse_mermaid_file(diagram_path)
    config = MappingConfig.from_file(config_path)
    mapper = ContextMapper(config, parsed)

    print("=" * 70)
    print(f"  Context Bridge Demo — {project_name}")
    print("=" * 70)
    print()
    print(f"  Diagram: {len(parsed.nodes)} services, "
          f"{len(parsed.relationships)} relationships")
    print(f"  Mapping: {len(config.rules)} file pattern rules")
    print()

    for i, prompt in enumerate(SAMPLE_PROMPTS, 1):
        print(f"{'─' * 70}")
        print(f"  Scenario {i}: {prompt['task']}")
        print(f"{'─' * 70}")
        print()
        print(_format_without_context(prompt))
        print(_format_with_context(prompt, mapper))
        print()

    # Also generate CLAUDE.md preview
    claude_md = generate_claude_md(parsed, config, project_name)
    print(f"{'─' * 70}")
    print("  Generated CLAUDE.md Preview (first 30 lines)")
    print(f"{'─' * 70}")
    print()
    for line in claude_md.split("\n")[:30]:
        print(f"  {line}")
    print("  ...")
    print()
    print("=" * 70)
    print("  Demo complete. Use 'generate-claude-md' to save full CLAUDE.md")
    print("=" * 70)

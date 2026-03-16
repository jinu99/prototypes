#!/usr/bin/env python3
"""Build prototype catalog: Marp slides + SPA index page.

Usage:
    python3 scripts/build-catalog.py

Output:
    docs/index.html              — Catalog SPA
    docs/slides/{slug}.html      — One slide deck per prototype
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_DIR / "docs"
SLIDES_DIR = DOCS_DIR / "slides"

# Category classification (mirrored from update-readme.sh)
CATEGORY_PATTERNS = [
    ("LLM Ops & Debugging", r"llm.*(context|qual|serve|monitor)|embedding.migr|long.context|토큰.*분석|vram.*(추정|모니터)|resource.monitor"),
    ("AI Code Quality & DevTools", r"vibe.code|tree.sitter|code.*(change|perf|audit)|secret.scrub|ai-code.*(change|perf)|sql.*guard|static.guard"),
    ("AI Agent & LLM Infra", r"agent|에이전트|agentic|llm.*(mesh|route|stabil)|runtime.debug|mcp.*런타임"),
    ("CI/CD & Infrastructure", r"ci-yaml|deploy|log.incident|webhook|chaos"),
    ("Web & SEO", r"seo|web.health|search.guard|크롤러|팬텀"),
    ("Document & Content", r"doc.*(structure|fresh)|slide|rag.doc|pdf|markdown|launch.kit"),
    ("Indie / Small Biz", r"indie|small.biz|queue|email.cleanup|community.*keyword|community.*monitor"),
    ("IoT & Data", r"iot|local.first|openapi|data.guard"),
]

CAT_ORDER = [
    "AI Agent & LLM Infra",
    "AI Code Quality & DevTools",
    "LLM Ops & Debugging",
    "CI/CD & Infrastructure",
    "Web & SEO",
    "Document & Content",
    "Indie / Small Biz",
    "IoT & Data",
    "Other",
]

CAT_COLORS = {
    "AI Agent & LLM Infra": "#7c3aed",
    "AI Code Quality & DevTools": "#2563eb",
    "LLM Ops & Debugging": "#0891b2",
    "CI/CD & Infrastructure": "#059669",
    "Web & SEO": "#d97706",
    "Document & Content": "#dc2626",
    "Indie / Small Biz": "#db2777",
    "IoT & Data": "#4f46e5",
    "Other": "#6b7280",
}


def classify_category(slug: str, desc: str) -> str:
    text = f"{desc} {slug}".lower()
    for cat, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, text):
            return cat
    return "Other"


def detect_stack(proto_dir: Path) -> str:
    parts = []
    if (proto_dir / "tsconfig.json").exists():
        parts.append("TypeScript")
    elif (proto_dir / "package.json").exists():
        parts.append("Node.js")
    if (proto_dir / "pyproject.toml").exists():
        parts.append("Python")
    return "/".join(parts) if parts else "Other"


def extract_section(text: str, heading: str) -> str:
    """Extract content between ## heading and the next ## heading."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_code_block(section: str) -> str:
    """Extract first code block content from a section."""
    m = re.search(r"```[^\n]*\n(.*?)```", section, re.DOTALL)
    return m.group(1).strip() if m else ""


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def parse_prototype(slug: str) -> dict | None:
    proto_dir = REPO_DIR / slug
    readme = proto_dir / "README.md"
    status_file = proto_dir / "STATUS.md"

    if not readme.exists():
        return None

    text = readme.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Title
    title = lines[0].lstrip("# ").strip() if lines else slug

    # Description
    desc = ""
    for line in lines[1:]:
        if line.startswith(">"):
            desc = line.lstrip("> ").strip()
            break

    if not desc:
        desc = "(설명 없음)"

    # Architecture section
    arch_section = extract_section(text, "Architecture")
    arch_diagram = extract_code_block(arch_section)

    # Demo section
    demo_section = extract_section(text, "Demo")

    # Status
    status = "UNKNOWN"
    status_summary = ""
    status_checklist = []
    created_date = ""
    if status_file.exists():
        st = status_file.read_text(encoding="utf-8")
        m = re.search(r"STATUS:\s*(SUCCESS|PARTIAL|FAILED)", st)
        if m:
            status = m.group(1)
        # Summary
        summary_section = extract_section(st, "요약")
        status_summary = summary_section.split("\n")[0] if summary_section else ""
        # Checklist
        for line in st.split("\n"):
            if re.match(r"^- \[[ x]\]", line):
                status_checklist.append(line)
        # Date
        m = re.search(r"생성일:\s*(\S+)", st)
        if m:
            created_date = m.group(1)

    category = classify_category(slug, desc)
    stack = detect_stack(proto_dir)

    return {
        "slug": slug,
        "title": title,
        "description": desc,
        "category": category,
        "stack": stack,
        "status": status,
        "status_summary": status_summary,
        "status_checklist": status_checklist,
        "created_date": created_date,
        "architecture": arch_diagram,
        "demo": demo_section,
    }


def generate_marp_markdown(proto: dict) -> str:
    """Generate Marp markdown for a single prototype."""
    slug = proto["slug"]
    title = proto["title"]
    desc = proto["description"]
    category = proto["category"]
    stack = proto["stack"]
    status = proto["status"]
    date = proto["created_date"] or "N/A"
    arch = proto["architecture"]
    demo = proto["demo"]
    checklist = proto["status_checklist"]

    status_emoji = {"SUCCESS": "✅", "PARTIAL": "⚠️", "FAILED": "❌"}.get(status, "❓")
    cat_color = CAT_COLORS.get(category, "#6b7280")

    slides = []

    # --- Slide 1: Title ---
    slides.append(f"""---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
style: |
  section {{
    font-family: 'Pretendard', 'Apple SD Gothic Neo', system-ui, sans-serif;
    padding: 40px 60px;
  }}
  section.title {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: white;
  }}
  section.title h1 {{
    font-size: 2.2em;
    margin-bottom: 0.3em;
    line-height: 1.2;
  }}
  section.title blockquote {{
    border-left: 4px solid {cat_color};
    padding-left: 16px;
    font-size: 1.1em;
    opacity: 0.9;
    margin: 0.5em 0;
  }}
  section.title .meta {{
    margin-top: 1.5em;
    font-size: 0.8em;
    opacity: 0.7;
  }}
  section.title .badge {{
    display: inline-block;
    background: {cat_color};
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75em;
    margin-right: 8px;
  }}
  h2 {{
    color: #1e293b;
    border-bottom: 3px solid {cat_color};
    padding-bottom: 8px;
  }}
  pre {{
    font-size: 0.5em;
    line-height: 1.4;
    background: #1e293b;
    color: #e2e8f0;
    border-radius: 8px;
    padding: 16px;
  }}
  code {{
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
  }}
  .status-pass {{ color: #059669; font-weight: bold; }}
  .status-warn {{ color: #d97706; font-weight: bold; }}
  .status-fail {{ color: #dc2626; font-weight: bold; }}
  ul {{ font-size: 0.9em; }}
---

<!-- _class: title -->

# {title}

> {desc}

<div class="meta">
<span class="badge">{category}</span>
<span class="badge" style="background: #475569">{stack}</span>
{status_emoji} {status} &nbsp;|&nbsp; {date}
</div>
""")

    # --- Slide 2: Architecture ---
    if arch:
        slides.append(f"""
---

## Architecture

```
{arch}
```
""")

    # --- Slide 3-4: Demo ---
    if demo:
        # Split demo into chunks if too long
        demo_lines = demo.split("\n")
        if len(demo_lines) > 45:
            mid = len(demo_lines) // 2
            for i in range(mid, min(mid + 10, len(demo_lines))):
                if not demo_lines[i].strip():
                    mid = i
                    break
            slides.append(f"""
---

## Demo (1/2)

{chr(10).join(demo_lines[:mid])}
""")
            slides.append(f"""
---

## Demo (2/2)

{chr(10).join(demo_lines[mid:])}
""")
        else:
            slides.append(f"""
---

## Demo

{demo}
""")

    # --- Slide 5: Status & Links ---
    checklist_md = "\n".join(checklist) if checklist else "- (체크리스트 없음)"
    slides.append(f"""
---

## Completion Status

{checklist_md}

<br/>

**Source:** [github.com/jinu99/prototypes/{slug}](https://github.com/jinu99/prototypes/tree/main/{slug})

[← Back to Catalog](../index.html)
""")

    return "\n".join(slides)


def build_card_element(p: dict) -> str:
    """Build a card HTML element using safe DOM construction approach."""
    slug = escape_html(p["slug"])
    title = escape_html(p["title"])
    desc = escape_html(p["description"])
    cat = escape_html(p["category"])
    stack = escape_html(p["stack"])
    status = p["status"]
    cat_color = CAT_COLORS.get(p["category"], "#6b7280")
    status_icon = {"SUCCESS": "✅", "PARTIAL": "⚠️", "FAILED": "❌"}.get(status, "❓")

    return f"""<a class="card" href="slides/{slug}.html" style="--cat-color:{cat_color}" data-cat="{cat}" data-slug="{slug}" data-title="{title}" data-desc="{desc}" data-stack="{stack}">
      <div class="card-title">{title}</div>
      <div class="card-desc">{desc}</div>
      <div class="card-meta">
        <span class="badge badge-cat" style="background:{cat_color}">{cat}</span>
        <span class="badge badge-stack">{stack}</span>
        <span class="badge-status">{status_icon}</span>
      </div>
    </a>"""


def generate_catalog_html(prototypes: list[dict]) -> str:
    """Generate the catalog SPA HTML."""
    total = len(prototypes)
    cat_colors_json = json.dumps(CAT_COLORS, ensure_ascii=False)

    # Pre-render all cards server-side (no innerHTML needed)
    cards_html = "\n    ".join(build_card_element(p) for p in prototypes)

    # Build category counts for filter buttons
    cat_counts: dict[str, int] = {}
    for p in prototypes:
        cat_counts[p["category"]] = cat_counts.get(p["category"], 0) + 1

    filter_buttons = [f'<button class="filter-btn active" data-cat="">All ({total})</button>']
    for cat in CAT_ORDER:
        if cat not in cat_counts:
            continue
        escaped_cat = escape_html(cat)
        filter_buttons.append(
            f'<button class="filter-btn" data-cat="{escaped_cat}">'
            f'{escaped_cat} ({cat_counts[cat]})</button>'
        )
    filters_html = "\n      ".join(filter_buttons)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prototype Catalog</title>
<style>
  :root {{
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-hover: #334155;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #3b82f6;
    --border: #334155;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Pretendard', 'Apple SD Gothic Neo', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }}

  .header {{
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 24px 32px;
    text-align: center;
  }}

  .header h1 {{
    font-size: 2.4em;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 8px;
  }}

  .header h1 span {{
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}

  .header .subtitle {{
    color: var(--text-dim);
    font-size: 1.05em;
    margin-bottom: 4px;
  }}

  .header .count {{
    color: var(--text-dim);
    font-size: 0.9em;
    opacity: 0.7;
  }}

  .pipeline {{
    display: flex;
    justify-content: center;
    gap: 4px;
    margin-top: 20px;
    flex-wrap: wrap;
  }}

  .pipeline .step {{
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 0.82em;
    color: var(--text-dim);
  }}

  .pipeline .arrow {{
    color: var(--text-dim);
    opacity: 0.4;
    align-self: center;
    font-size: 0.9em;
  }}

  .controls {{
    max-width: 1200px;
    margin: 24px auto 0;
    padding: 0 24px;
  }}

  .search-box {{
    width: 100%;
    padding: 12px 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--text);
    font-size: 1em;
    outline: none;
    transition: border-color 0.2s;
  }}

  .search-box:focus {{
    border-color: var(--accent);
  }}

  .search-box::placeholder {{
    color: var(--text-dim);
    opacity: 0.6;
  }}

  .filters {{
    display: flex;
    gap: 8px;
    margin-top: 16px;
    flex-wrap: wrap;
  }}

  .filter-btn {{
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    font-size: 0.82em;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }}

  .filter-btn:hover {{
    background: var(--surface);
    color: var(--text);
  }}

  .filter-btn.active {{
    background: var(--accent);
    border-color: var(--accent);
    color: white;
  }}

  .result-count {{
    color: var(--text-dim);
    font-size: 0.85em;
    margin-top: 16px;
    padding: 0 4px;
  }}

  .grid {{
    max-width: 1200px;
    margin: 20px auto 60px;
    padding: 0 24px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    cursor: pointer;
    transition: all 0.25s ease;
    text-decoration: none;
    color: inherit;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
  }}

  .card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--cat-color, var(--accent));
    opacity: 0;
    transition: opacity 0.25s;
  }}

  .card:hover {{
    background: var(--surface-hover);
    border-color: #475569;
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
  }}

  .card:hover::before {{
    opacity: 1;
  }}

  .card.hidden {{
    display: none;
  }}

  .card-title {{
    font-size: 1.05em;
    font-weight: 700;
    margin-bottom: 8px;
    line-height: 1.3;
    word-break: break-word;
  }}

  .card-desc {{
    color: var(--text-dim);
    font-size: 0.88em;
    line-height: 1.5;
    flex: 1;
    margin-bottom: 16px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .card-meta {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }}

  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.72em;
    font-weight: 600;
    letter-spacing: 0.01em;
  }}

  .badge-cat {{
    color: white;
  }}

  .badge-stack {{
    background: rgba(148, 163, 184, 0.15);
    color: var(--text-dim);
    border: 1px solid var(--border);
  }}

  .badge-status {{
    margin-left: auto;
    font-size: 0.75em;
  }}

  .footer {{
    text-align: center;
    padding: 30px;
    color: var(--text-dim);
    font-size: 0.82em;
    border-top: 1px solid var(--border);
  }}

  .footer a {{
    color: var(--accent);
    text-decoration: none;
  }}

  @media (max-width: 600px) {{
    .header h1 {{ font-size: 1.6em; }}
    .grid {{ grid-template-columns: 1fr; padding: 0 16px; }}
    .controls {{ padding: 0 16px; }}
  }}
</style>
</head>
<body>

<header class="header">
  <h1><span>Prototype Catalog</span></h1>
  <p class="subtitle">커뮤니티 pain point 기반 자동 프로토타이핑 파이프라인 산출물</p>
  <p class="count">{total} prototypes</p>
  <div class="pipeline">
    <span class="step">Crawl</span><span class="arrow">&rarr;</span>
    <span class="step">Analyze</span><span class="arrow">&rarr;</span>
    <span class="step">Ideate</span><span class="arrow">&rarr;</span>
    <span class="step">Select</span><span class="arrow">&rarr;</span>
    <span class="step">Spawn</span>
  </div>
</header>

<div class="controls">
  <input type="text" class="search-box" placeholder="Search prototypes..." id="search" autocomplete="off">
  <div class="filters" id="filters">
    {filters_html}
  </div>
  <div class="result-count" id="result-count"></div>
</div>

<div class="grid" id="grid">
    {cards_html}
</div>

<footer class="footer">
  <a href="https://github.com/jinu99/prototypes">github.com/jinu99/prototypes</a>
  &nbsp;&middot;&nbsp; Auto-generated by prototype-pipeline
</footer>

<script>
(function() {{
  var activeCat = '';
  var searchBox = document.getElementById('search');
  var cards = document.querySelectorAll('.card');
  var filterBtns = document.querySelectorAll('.filter-btn');
  var resultCount = document.getElementById('result-count');
  var total = cards.length;

  function updateFilter() {{
    var q = searchBox.value.toLowerCase();
    var shown = 0;

    for (var i = 0; i < cards.length; i++) {{
      var card = cards[i];
      var cat = card.getAttribute('data-cat');
      var slug = card.getAttribute('data-slug');
      var title = card.getAttribute('data-title');
      var desc = card.getAttribute('data-desc');
      var stack = card.getAttribute('data-stack');

      var catMatch = !activeCat || cat === activeCat;
      var textMatch = !q
        || title.toLowerCase().indexOf(q) !== -1
        || desc.toLowerCase().indexOf(q) !== -1
        || slug.toLowerCase().indexOf(q) !== -1
        || cat.toLowerCase().indexOf(q) !== -1
        || stack.toLowerCase().indexOf(q) !== -1;

      if (catMatch && textMatch) {{
        card.classList.remove('hidden');
        shown++;
      }} else {{
        card.classList.add('hidden');
      }}
    }}

    resultCount.textContent = shown === total ? '' : shown + ' / ' + total;

    for (var j = 0; j < filterBtns.length; j++) {{
      var btn = filterBtns[j];
      var btnCat = btn.getAttribute('data-cat');
      if (btnCat === activeCat) {{
        btn.classList.add('active');
      }} else {{
        btn.classList.remove('active');
      }}
    }}
  }}

  for (var k = 0; k < filterBtns.length; k++) {{
    filterBtns[k].addEventListener('click', function() {{
      var cat = this.getAttribute('data-cat');
      activeCat = activeCat === cat ? '' : cat;
      updateFilter();
    }});
  }}

  searchBox.addEventListener('input', updateFilter);
}})();
</script>
</body>
</html>"""


def main():
    print(f"Repository: {REPO_DIR}")

    # Collect prototypes
    prototypes = []
    for d in sorted(REPO_DIR.iterdir()):
        if not d.is_dir():
            continue
        slug = d.name
        if slug in ("scripts", ".git", "docs", "node_modules", ".venv"):
            continue
        if not (d / "README.md").exists():
            continue

        proto = parse_prototype(slug)
        if proto:
            prototypes.append(proto)

    print(f"Found {len(prototypes)} prototypes")

    # Create output dirs
    DOCS_DIR.mkdir(exist_ok=True)
    SLIDES_DIR.mkdir(exist_ok=True)

    # Generate Marp markdown files in a temp dir, then batch convert
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        for proto in prototypes:
            md_content = generate_marp_markdown(proto)
            md_file = tmppath / f"{proto['slug']}.md"
            md_file.write_text(md_content, encoding="utf-8")

        print("Converting slides with Marp CLI...")

        result = subprocess.run(
            [
                "npx", "@marp-team/marp-cli",
                "--input-dir", str(tmppath),
                "--output", str(SLIDES_DIR),
                "--html",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Marp CLI error:\n{result.stderr}", file=sys.stderr)
            # Try one-by-one for better error reporting
            for md_file in sorted(tmppath.glob("*.md")):
                out_file = SLIDES_DIR / f"{md_file.stem}.html"
                r = subprocess.run(
                    ["npx", "@marp-team/marp-cli", str(md_file), "-o", str(out_file), "--html"],
                    capture_output=True, text=True,
                )
                if r.returncode == 0:
                    print(f"  ✓ {md_file.stem}")
                else:
                    print(f"  ✗ {md_file.stem}: {r.stderr[:200]}")
        else:
            print(f"  ✓ {len(prototypes)} slide decks generated")

    # Generate catalog
    catalog_html = generate_catalog_html(prototypes)
    (DOCS_DIR / "index.html").write_text(catalog_html, encoding="utf-8")
    print(f"  ✓ Catalog index generated")

    # Verify
    slides_count = len(list(SLIDES_DIR.glob("*.html")))
    print(f"\nDone: docs/index.html + {slides_count} slide decks")


if __name__ == "__main__":
    main()

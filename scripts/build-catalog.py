#!/usr/bin/env python3
"""Build prototype catalog: scrollable article pages + SPA index.

Converts PRESENTATION.md (or README.md fallback) into styled HTML article pages.
No Marp/slide dependency — content flows naturally with scroll.

Usage:
    python3 scripts/build-catalog.py

Output:
    docs/index.html              — Catalog SPA
    docs/slides/{slug}.html      — Article page per prototype
"""

import json
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_DIR / "docs"
SLIDES_DIR = DOCS_DIR / "slides"

CATEGORY_PATTERNS = [
    ("LLM Ops & Debugging", r"llm.*(context|qual|serve|monitor)|embedding.migr|long.context|토큰.*분석|vram.*(추정|모니터)|resource.monitor"),
    ("AI Code Quality & DevTools", r"vibe.code|tree.sitter|code.*(change|perf|audit|smell)|secret.scrub|ai-code.*(change|perf)|sql.*guard|static.guard"),
    ("AI Agent & LLM Infra", r"agent|에이전트|agentic|llm.*(mesh|route|stabil)|runtime.debug|mcp.*런타임"),
    ("CI/CD & Infrastructure", r"ci-yaml|deploy|log.incident|webhook|chaos"),
    ("Web & SEO", r"seo|web.health|search.guard|크롤러|팬텀"),
    ("Document & Content", r"doc.*(structure|fresh)|slide|rag.doc|pdf|markdown|launch.kit"),
    ("Indie / Small Biz", r"indie|small.biz|queue|email.cleanup|community.*keyword|community.*monitor|feed.*relevance|alert.*digest"),
    ("IoT & Data", r"iot|local.first|openapi|data.guard|lora.*merge"),
]

CAT_ORDER = [
    "AI Agent & LLM Infra", "AI Code Quality & DevTools", "LLM Ops & Debugging",
    "CI/CD & Infrastructure", "Web & SEO", "Document & Content",
    "Indie / Small Biz", "IoT & Data", "Other",
]

CAT_COLORS = {
    "AI Agent & LLM Infra": "#7c3aed", "AI Code Quality & DevTools": "#2563eb",
    "LLM Ops & Debugging": "#0891b2", "CI/CD & Infrastructure": "#059669",
    "Web & SEO": "#d97706", "Document & Content": "#dc2626",
    "Indie / Small Biz": "#db2777", "IoT & Data": "#4f46e5", "Other": "#6b7280",
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


def escape_html(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def parse_prototype(slug: str) -> dict | None:
    proto_dir = REPO_DIR / slug
    readme = proto_dir / "README.md"
    status_file = proto_dir / "STATUS.md"

    if not readme.exists():
        return None

    text = readme.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = lines[0].lstrip("# ").strip() if lines else slug
    desc = ""
    for line in lines[1:]:
        if line.startswith(">"):
            desc = line.lstrip("> ").strip()
            break
    if not desc:
        desc = "(설명 없음)"

    status = "UNKNOWN"
    created_date = ""
    if status_file.exists():
        st = status_file.read_text(encoding="utf-8")
        m = re.search(r"STATUS:\s*(SUCCESS|PARTIAL|FAILED)", st)
        if m:
            status = m.group(1)
        m = re.search(r"생성일:\s*(\S+)", st)
        if m:
            created_date = m.group(1)

    return {
        "slug": slug,
        "title": title,
        "description": desc,
        "category": classify_category(slug, desc),
        "stack": detect_stack(proto_dir),
        "status": status,
        "created_date": created_date,
    }


# ─── Markdown → HTML converter (minimal, no dependencies) ───


def md_to_html(md_text: str) -> tuple[str, list[str]]:
    """Convert markdown to HTML, extracting speaker notes separately.

    Returns (html_body, list_of_speaker_notes).
    """
    # Remove Marp frontmatter
    md_text = re.sub(r"^---\n.*?\n---\n", "", md_text, count=1, flags=re.DOTALL)
    # Remove slide separators
    md_text = md_text.replace("\n---\n", "\n")
    # Remove <!-- _class: ... --> directives
    md_text = re.sub(r"<!--\s*_class:.*?-->\s*\n?", "", md_text)

    # Extract speaker notes
    notes = []
    def extract_note(m):
        note_text = m.group(1).strip()
        if note_text:
            notes.append(note_text)
            return f'<div class="speaker-note" data-note-idx="{len(notes) - 1}"></div>'
        return ""

    md_text = re.sub(r"<!--\s*\n?(.*?)\n?\s*-->", extract_note, md_text, flags=re.DOTALL)

    lines = md_text.split("\n")
    html_parts = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_content = escape_html("\n".join(code_lines))
            cls = f' class="language-{escape_html(lang)}"' if lang else ""
            html_parts.append(f'<pre><code{cls}>{code_content}</code></pre>')
            continue

        # Headings
        if line.startswith("# ") and not line.startswith("## "):
            html_parts.append(f'<h1>{_inline(line[2:])}</h1>')
            i += 1
            continue
        if line.startswith("## "):
            heading_text = line[3:].strip()
            heading_id = re.sub(r"[^\w가-힣-]", "", heading_text.lower().replace(" ", "-"))
            html_parts.append(f'<h2 id="{heading_id}">{_inline(heading_text)}</h2>')
            i += 1
            continue
        if line.startswith("### "):
            html_parts.append(f'<h3>{_inline(line[4:])}</h3>')
            i += 1
            continue

        # Tables
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|", lines[i + 1]):
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            html_parts.append(_table_to_html(table_lines))
            continue

        # Blockquote
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            html_parts.append(f'<blockquote><p>{_inline("<br>".join(quote_lines))}</p></blockquote>')
            continue

        # Unordered list
        if re.match(r"^[-*] ", line) or re.match(r"^- \[[ x]\]", line):
            list_items = []
            while i < len(lines) and (re.match(r"^[-*] ", lines[i]) or re.match(r"^- \[[ x]\]", lines[i])):
                item = re.sub(r"^[-*] ", "", lines[i])
                # Checkboxes
                item = item.replace("[ ]", '<input type="checkbox" disabled>')
                item = item.replace("[x]", '<input type="checkbox" checked disabled>')
                list_items.append(f"<li>{_inline(item)}</li>")
                i += 1
            html_parts.append(f'<ul>{"".join(list_items)}</ul>')
            continue

        # Ordered list
        if re.match(r"^\d+\.\s", line):
            list_items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                item = re.sub(r"^\d+\.\s", "", lines[i])
                list_items.append(f"<li>{_inline(item)}</li>")
                i += 1
            html_parts.append(f'<ol>{"".join(list_items)}</ol>')
            continue

        # Speaker note placeholder
        if '<div class="speaker-note"' in line:
            html_parts.append(line)
            i += 1
            continue

        # HTML passthrough (for <div>, <br>, etc.)
        if line.strip().startswith("<"):
            html_parts.append(line)
            i += 1
            continue

        # Paragraph
        if line.strip():
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "```", "|", ">", "- ", "* ", "<")):
                para_lines.append(lines[i])
                i += 1
            html_parts.append(f"<p>{_inline(' '.join(para_lines))}</p>")
            continue

        i += 1

    return "\n".join(html_parts), notes


def _inline(text: str) -> str:
    """Process inline markdown: bold, italic, code, links."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", lambda m: f'<code>{escape_html(m.group(1))}</code>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _table_to_html(lines: list[str]) -> str:
    """Convert markdown table lines to HTML table."""
    rows = []
    for idx, line in enumerate(lines):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if idx == 1 and all(re.match(r"^[\s\-:]+$", c) for c in cells):
            continue  # skip separator row
        tag = "th" if idx == 0 else "td"
        row = "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells)
        rows.append(f"<tr>{row}</tr>")
    return f"<table>{rows[0]}{''.join(rows[1:])}</table>"


# ─── Article page generator ───


def generate_article_html(proto: dict) -> str:
    """Generate a scrollable article page from PRESENTATION.md or README."""
    slug = proto["slug"]
    title = proto["title"]
    desc = proto["description"]
    category = proto["category"]
    stack = proto["stack"]
    status = proto["status"]
    date = proto["created_date"] or ""
    cat_color = CAT_COLORS.get(category, "#6b7280")
    status_icon = {"SUCCESS": "✅", "PARTIAL": "⚠️", "FAILED": "❌"}.get(status, "❓")

    # Read presentation or readme
    pres_file = REPO_DIR / slug / "PRESENTATION.md"
    readme_file = REPO_DIR / slug / "README.md"

    if pres_file.exists():
        md_text = pres_file.read_text(encoding="utf-8")
    else:
        md_text = readme_file.read_text(encoding="utf-8")

    body_html, notes = md_to_html(md_text)

    # Build speaker notes JSON
    notes_json = json.dumps(notes, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)}</title>
<style>
  :root {{
    --bg: #0f172a;
    --surface: #1e293b;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: {cat_color};
    --border: #334155;
    --code-bg: #0d1117;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Pretendard', 'Apple SD Gothic Neo', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    font-size: 17px;
  }}

  /* --- Hero --- */
  .hero {{
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-bottom: 3px solid var(--accent);
    padding: 60px 24px 48px;
    text-align: center;
  }}
  .hero h1 {{
    font-size: 2em;
    font-weight: 800;
    margin-bottom: 12px;
    line-height: 1.3;
  }}
  .hero .desc {{
    color: var(--text-dim);
    font-size: 1.1em;
    max-width: 700px;
    margin: 0 auto 20px;
  }}
  .hero .meta {{
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .badge {{
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.78em;
    font-weight: 600;
  }}
  .badge-cat {{ background: var(--accent); color: white; }}
  .badge-stack {{ background: rgba(148,163,184,0.15); color: var(--text-dim); border: 1px solid var(--border); }}
  .badge-status {{ background: rgba(148,163,184,0.1); color: var(--text-dim); }}

  /* --- Article --- */
  .article {{
    max-width: 800px;
    margin: 0 auto;
    padding: 40px 24px 80px;
  }}
  .article h1 {{ display: none; }}
  .article h2 {{
    font-size: 1.5em;
    font-weight: 700;
    margin: 48px 0 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--accent);
    color: white;
  }}
  .article h2:first-of-type {{ margin-top: 0; }}
  .article h3 {{
    font-size: 1.15em;
    font-weight: 600;
    margin: 28px 0 10px;
    color: var(--text);
  }}
  .article p {{
    margin: 12px 0;
    color: var(--text-dim);
  }}
  .article strong {{ color: var(--text); }}
  .article a {{ color: var(--accent); text-decoration: none; }}
  .article a:hover {{ text-decoration: underline; }}
  .article ul, .article ol {{
    margin: 12px 0;
    padding-left: 24px;
    color: var(--text-dim);
  }}
  .article li {{ margin: 6px 0; }}
  .article li input[type="checkbox"] {{ margin-right: 6px; }}
  .article blockquote {{
    border-left: 4px solid var(--accent);
    padding: 12px 20px;
    margin: 16px 0;
    background: rgba(148,163,184,0.05);
    border-radius: 0 8px 8px 0;
    color: var(--text-dim);
    font-style: italic;
  }}
  .article pre {{
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    overflow-x: auto;
    margin: 16px 0;
    font-size: 0.85em;
    line-height: 1.5;
  }}
  .article code {{
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  }}
  .article p code, .article li code, .article td code {{
    background: rgba(148,163,184,0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  .article table {{
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 0.9em;
  }}
  .article th, .article td {{
    padding: 10px 14px;
    border: 1px solid var(--border);
    text-align: left;
  }}
  .article th {{
    background: var(--surface);
    color: var(--text);
    font-weight: 600;
  }}
  .article td {{ color: var(--text-dim); }}

  /* --- Speaker notes toggle --- */
  .speaker-note {{
    margin: 8px 0 20px;
  }}
  .note-toggle {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(124, 58, 237, 0.1);
    border: 1px solid rgba(124, 58, 237, 0.25);
    color: #a78bfa;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.82em;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }}
  .note-toggle:hover {{
    background: rgba(124, 58, 237, 0.2);
  }}
  .note-toggle .arrow {{
    transition: transform 0.2s;
    font-size: 0.8em;
  }}
  .note-toggle.open .arrow {{
    transform: rotate(90deg);
  }}
  .note-content {{
    display: none;
    background: rgba(124, 58, 237, 0.06);
    border-left: 3px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    margin-top: 8px;
    color: #c4b5fd;
    font-size: 0.92em;
    line-height: 1.8;
    white-space: pre-wrap;
  }}
  .note-content.open {{
    display: block;
  }}

  /* --- Navigation --- */
  .nav {{
    position: sticky;
    top: 0;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    z-index: 100;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .nav a {{
    color: var(--text-dim);
    text-decoration: none;
    font-size: 0.88em;
    transition: color 0.2s;
  }}
  .nav a:hover {{ color: var(--text); }}
  .nav .title-sm {{
    color: var(--text);
    font-weight: 600;
    font-size: 0.92em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 400px;
  }}
  .nav .actions {{
    display: flex;
    gap: 16px;
    align-items: center;
  }}
  .toggle-all-btn {{
    background: rgba(124, 58, 237, 0.15);
    border: 1px solid rgba(124, 58, 237, 0.3);
    color: #a78bfa;
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 0.8em;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.2s;
  }}
  .toggle-all-btn:hover {{
    background: rgba(124, 58, 237, 0.25);
  }}

  .footer {{
    text-align: center;
    padding: 30px;
    color: var(--text-dim);
    font-size: 0.82em;
    border-top: 1px solid var(--border);
  }}
  .footer a {{ color: var(--accent); text-decoration: none; }}

  @media (max-width: 600px) {{
    .hero h1 {{ font-size: 1.5em; }}
    .article {{ padding: 24px 16px 60px; }}
    .nav .title-sm {{ max-width: 200px; }}
  }}
</style>
</head>
<body>

<nav class="nav">
  <a href="../index.html">&larr; Catalog</a>
  <span class="title-sm">{escape_html(title)}</span>
  <div class="actions">
    <button class="toggle-all-btn" id="toggleAll">발표 스크립트 전체 열기</button>
    <a href="https://github.com/jinu99/prototypes/tree/main/{escape_html(slug)}">GitHub</a>
  </div>
</nav>

<header class="hero">
  <h1>{escape_html(title)}</h1>
  <p class="desc">{escape_html(desc)}</p>
  <div class="meta">
    <span class="badge badge-cat">{escape_html(category)}</span>
    <span class="badge badge-stack">{escape_html(stack)}</span>
    <span class="badge badge-status">{status_icon} {escape_html(status)}</span>
    {"<span class='badge badge-stack'>" + escape_html(date) + "</span>" if date else ""}
  </div>
</header>

<main class="article">
{body_html}
</main>

<footer class="footer">
  <a href="../index.html">&larr; Back to Catalog</a>
  &nbsp;&middot;&nbsp;
  <a href="https://github.com/jinu99/prototypes/tree/main/{escape_html(slug)}">Source Code</a>
</footer>

<script>
(function() {{
  var notes = {notes_json};
  var placeholders = document.querySelectorAll('.speaker-note');

  placeholders.forEach(function(el) {{
    var idx = parseInt(el.getAttribute('data-note-idx'));
    if (idx >= notes.length) return;
    var noteText = notes[idx];

    var toggle = document.createElement('button');
    toggle.className = 'note-toggle';
    toggle.setAttribute('type', 'button');
    toggle.textContent = '';
    var arrow = document.createElement('span');
    arrow.className = 'arrow';
    arrow.textContent = '▶';
    toggle.prepend(arrow);
    toggle.append(document.createTextNode(' 발표 스크립트'));

    var content = document.createElement('div');
    content.className = 'note-content';
    content.textContent = noteText;

    toggle.addEventListener('click', function() {{
      toggle.classList.toggle('open');
      content.classList.toggle('open');
    }});

    el.appendChild(toggle);
    el.appendChild(content);
  }});

  var toggleAllBtn = document.getElementById('toggleAll');
  var allOpen = false;
  toggleAllBtn.addEventListener('click', function() {{
    allOpen = !allOpen;
    document.querySelectorAll('.note-toggle').forEach(function(t) {{
      if (allOpen) {{
        t.classList.add('open');
        t.nextElementSibling.classList.add('open');
      }} else {{
        t.classList.remove('open');
        t.nextElementSibling.classList.remove('open');
      }}
    }});
    toggleAllBtn.textContent = allOpen ? '발표 스크립트 전체 닫기' : '발표 스크립트 전체 열기';
  }});
}})();
</script>
</body>
</html>"""


# ─── Catalog SPA (same as before, just cleaner) ───


def build_card_element(p: dict) -> str:
    slug = escape_html(p["slug"])
    title = escape_html(p["title"])
    desc = escape_html(p["description"])
    cat = escape_html(p["category"])
    stack = escape_html(p["stack"])
    cat_color = CAT_COLORS.get(p["category"], "#6b7280")
    status_icon = {"SUCCESS": "✅", "PARTIAL": "⚠️", "FAILED": "❌"}.get(p["status"], "❓")

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
    total = len(prototypes)
    cards_html = "\n    ".join(build_card_element(p) for p in prototypes)

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
  :root {{ --bg: #0f172a; --surface: #1e293b; --surface-hover: #334155; --text: #e2e8f0; --text-dim: #94a3b8; --accent: #3b82f6; --border: #334155; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Pretendard', 'Apple SD Gothic Neo', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); border-bottom: 1px solid var(--border); padding: 40px 24px 32px; text-align: center; }}
  .header h1 {{ font-size: 2.4em; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 8px; }}
  .header h1 span {{ background: linear-gradient(135deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .header .subtitle {{ color: var(--text-dim); font-size: 1.05em; margin-bottom: 4px; }}
  .header .count {{ color: var(--text-dim); font-size: 0.9em; opacity: 0.7; }}
  .pipeline {{ display: flex; justify-content: center; gap: 4px; margin-top: 20px; flex-wrap: wrap; }}
  .pipeline .step {{ background: var(--surface); border: 1px solid var(--border); padding: 6px 16px; border-radius: 20px; font-size: 0.82em; color: var(--text-dim); }}
  .pipeline .arrow {{ color: var(--text-dim); opacity: 0.4; align-self: center; }}
  .controls {{ max-width: 1200px; margin: 24px auto 0; padding: 0 24px; }}
  .search-box {{ width: 100%; padding: 12px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; color: var(--text); font-size: 1em; outline: none; transition: border-color 0.2s; }}
  .search-box:focus {{ border-color: var(--accent); }}
  .search-box::placeholder {{ color: var(--text-dim); opacity: 0.6; }}
  .filters {{ display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }}
  .filter-btn {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: transparent; color: var(--text-dim); font-size: 0.82em; cursor: pointer; transition: all 0.2s; white-space: nowrap; }}
  .filter-btn:hover {{ background: var(--surface); color: var(--text); }}
  .filter-btn.active {{ background: var(--accent); border-color: var(--accent); color: white; }}
  .result-count {{ color: var(--text-dim); font-size: 0.85em; margin-top: 16px; padding: 0 4px; }}
  .grid {{ max-width: 1200px; margin: 20px auto 60px; padding: 0 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; cursor: pointer; transition: all 0.25s ease; text-decoration: none; color: inherit; display: flex; flex-direction: column; position: relative; overflow: hidden; }}
  .card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--cat-color, var(--accent)); opacity: 0; transition: opacity 0.25s; }}
  .card:hover {{ background: var(--surface-hover); border-color: #475569; transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.3); }}
  .card:hover::before {{ opacity: 1; }}
  .card.hidden {{ display: none; }}
  .card-title {{ font-size: 1.05em; font-weight: 700; margin-bottom: 8px; line-height: 1.3; word-break: break-word; }}
  .card-desc {{ color: var(--text-dim); font-size: 0.88em; line-height: 1.5; flex: 1; margin-bottom: 16px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
  .card-meta {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.72em; font-weight: 600; }}
  .badge-cat {{ color: white; }}
  .badge-stack {{ background: rgba(148,163,184,0.15); color: var(--text-dim); border: 1px solid var(--border); }}
  .badge-status {{ margin-left: auto; font-size: 0.75em; }}
  .footer {{ text-align: center; padding: 30px; color: var(--text-dim); font-size: 0.82em; border-top: 1px solid var(--border); }}
  .footer a {{ color: var(--accent); text-decoration: none; }}
  @media (max-width: 600px) {{ .header h1 {{ font-size: 1.6em; }} .grid {{ grid-template-columns: 1fr; padding: 0 16px; }} .controls {{ padding: 0 16px; }} }}
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
  <div class="filters" id="filters">{filters_html}</div>
  <div class="result-count" id="result-count"></div>
</div>
<div class="grid" id="grid">{cards_html}</div>
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
      var catMatch = !activeCat || card.getAttribute('data-cat') === activeCat;
      var textMatch = !q || [card.getAttribute('data-title'), card.getAttribute('data-desc'), card.getAttribute('data-slug'), card.getAttribute('data-cat'), card.getAttribute('data-stack')].some(function(v) {{ return v.toLowerCase().indexOf(q) !== -1; }});
      if (catMatch && textMatch) {{ card.classList.remove('hidden'); shown++; }} else {{ card.classList.add('hidden'); }}
    }}
    resultCount.textContent = shown === total ? '' : shown + ' / ' + total;
    filterBtns.forEach(function(btn) {{ btn.classList.toggle('active', btn.getAttribute('data-cat') === activeCat); }});
  }}
  filterBtns.forEach(function(btn) {{ btn.addEventListener('click', function() {{ activeCat = activeCat === this.getAttribute('data-cat') ? '' : this.getAttribute('data-cat'); updateFilter(); }}); }});
  searchBox.addEventListener('input', updateFilter);
}})();
</script>
</body>
</html>"""


# ─── Main ───


def main():
    print(f"Repository: {REPO_DIR}")

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

    DOCS_DIR.mkdir(exist_ok=True)
    SLIDES_DIR.mkdir(exist_ok=True)

    # Generate article pages (no Marp needed!)
    for proto in prototypes:
        html = generate_article_html(proto)
        out_file = SLIDES_DIR / f"{proto['slug']}.html"
        out_file.write_text(html, encoding="utf-8")

    print(f"  ✓ {len(prototypes)} article pages generated")

    # Generate catalog
    catalog_html = generate_catalog_html(prototypes)
    (DOCS_DIR / "index.html").write_text(catalog_html, encoding="utf-8")
    print(f"  ✓ Catalog index generated")

    slides_count = len(list(SLIDES_DIR.glob("*.html")))
    print(f"\nDone: docs/index.html + {slides_count} article pages")


if __name__ == "__main__":
    main()

"""HTML report generation."""

from __future__ import annotations

import html
from pathlib import Path

from .graph import ScoredPackage
from .analyzer import CAPABILITY_WEIGHTS

CAPABILITY_ICONS = {
    "network": "&#x1F310;",      # 🌐
    "filesystem": "&#x1F4C1;",   # 📁
    "env_access": "&#x1F511;",   # 🔑
    "process_exec": "&#x2699;",  # ⚙
    "database": "&#x1F4BE;",     # 💾
    "crypto": "&#x1F512;",       # 🔒
    "code_exec": "&#x26A0;",     # ⚠
}

CAPABILITY_COLORS = {
    "process_exec": "#e74c3c",
    "code_exec": "#c0392b",
    "network": "#e67e22",
    "database": "#2980b9",
    "env_access": "#8e44ad",
    "filesystem": "#27ae60",
    "crypto": "#7f8c8d",
}


def generate_report(
    packages: list[ScoredPackage],
    project_name: str,
    output_path: Path,
    top_n: int = 5,
):
    """Generate an HTML report highlighting high-privilege dependencies."""
    max_score = max((p.blast_radius for p in packages), default=1) or 1

    # Build table rows
    rows = []
    for i, pkg in enumerate(packages):
        is_top = i < top_n
        risk_pct = min(pkg.blast_radius / max_score * 100, 100)

        cap_badges = ""
        for cat, count in sorted(pkg.capabilities.items(),
                                  key=lambda x: CAPABILITY_WEIGHTS.get(x[0], 0),
                                  reverse=True):
            color = CAPABILITY_COLORS.get(cat, "#95a5a6")
            icon = CAPABILITY_ICONS.get(cat, "")
            cap_badges += (
                f'<span class="badge" style="background:{color}">'
                f'{icon} {html.escape(cat)} ({count})</span> '
            )

        highlight = ' class="highlight"' if is_top else ""
        rank_badge = f'<span class="rank-badge">#{i+1}</span>' if is_top else f"#{i+1}"

        rows.append(f"""
        <tr{highlight}>
            <td>{rank_badge}</td>
            <td><strong>{html.escape(pkg.name)}</strong><br>
                <small>{html.escape(pkg.version)}</small></td>
            <td>
                <div class="score-bar-bg">
                    <div class="score-bar" style="width:{risk_pct:.0f}%;
                        background:{'#e74c3c' if is_top else '#3498db'}"></div>
                </div>
                <strong>{pkg.blast_radius:.1f}</strong>
            </td>
            <td>{cap_badges or '<span class="no-cap">none detected</span>'}</td>
            <td>{pkg.direct_score:.1f}</td>
            <td>{pkg.propagated_score:.1f}</td>
            <td>{pkg.dep_count}</td>
            <td>{pkg.reverse_dep_count}</td>
        </tr>""")

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dependency Privilege Report — {html.escape(project_name)}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: #0f1117; color: #e2e8f0; padding: 2rem;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 0.3rem; color: #f8fafc; }}
    .subtitle {{ color: #94a3b8; margin-bottom: 2rem; font-size: 0.95rem; }}
    .stats {{
        display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem; margin-bottom: 2rem;
    }}
    .stat-card {{
        background: #1e2030; border-radius: 12px; padding: 1.2rem;
        border: 1px solid #2d3148;
    }}
    .stat-card .label {{ color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; }}
    .stat-card .value {{ font-size: 1.8rem; font-weight: 700; margin-top: 0.3rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #1e2030;
             border-radius: 12px; overflow: hidden; }}
    th {{ background: #252840; color: #94a3b8; font-size: 0.75rem;
          text-transform: uppercase; letter-spacing: 0.05em;
          padding: 0.8rem 1rem; text-align: left; }}
    td {{ padding: 0.8rem 1rem; border-top: 1px solid #2d3148;
          font-size: 0.9rem; vertical-align: middle; }}
    tr.highlight {{ background: #2a1f1f; }}
    tr.highlight td {{ border-top-color: #3d2828; }}
    .badge {{
        display: inline-block; padding: 2px 8px; border-radius: 12px;
        font-size: 0.75rem; color: white; margin: 2px;
    }}
    .no-cap {{ color: #64748b; font-style: italic; font-size: 0.8rem; }}
    .score-bar-bg {{
        background: #2d3148; border-radius: 4px; height: 8px;
        width: 100px; display: inline-block; vertical-align: middle;
        margin-right: 8px;
    }}
    .score-bar {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
    .rank-badge {{
        background: #e74c3c; color: white; padding: 2px 8px;
        border-radius: 8px; font-weight: 700; font-size: 0.8rem;
    }}
    .legend {{
        margin-top: 2rem; padding: 1.2rem; background: #1e2030;
        border-radius: 12px; border: 1px solid #2d3148;
    }}
    .legend h3 {{ margin-bottom: 0.8rem; font-size: 0.95rem; }}
    .legend-item {{ display: inline-block; margin-right: 1.5rem; margin-bottom: 0.5rem; }}
    .formula {{
        margin-top: 1rem; padding: 1rem; background: #252840;
        border-radius: 8px; font-family: monospace; font-size: 0.85rem;
        color: #a5b4fc;
    }}
</style>
</head>
<body>
<div class="container">
    <h1>&#x1F6E1; High-Privilege Dependency Report</h1>
    <p class="subtitle">Project: <strong>{html.escape(project_name)}</strong>
       &mdash; {len(packages)} packages scanned</p>

    <div class="stats">
        <div class="stat-card">
            <div class="label">Total Packages</div>
            <div class="value">{len(packages)}</div>
        </div>
        <div class="stat-card">
            <div class="label">High-Risk (Top {top_n})</div>
            <div class="value" style="color:#e74c3c">{min(top_n, len(packages))}</div>
        </div>
        <div class="stat-card">
            <div class="label">Max Blast Radius</div>
            <div class="value" style="color:#e67e22">{max_score:.1f}</div>
        </div>
        <div class="stat-card">
            <div class="label">Avg Score</div>
            <div class="value">{sum(p.blast_radius for p in packages)/max(len(packages),1):.1f}</div>
        </div>
    </div>

    <table>
    <thead>
        <tr>
            <th>Rank</th>
            <th>Package</th>
            <th>Blast Radius</th>
            <th>Capabilities</th>
            <th>Direct</th>
            <th>Propagated</th>
            <th>Deps</th>
            <th>Rev Deps</th>
        </tr>
    </thead>
    <tbody>
        {''.join(rows)}
    </tbody>
    </table>

    <div class="legend">
        <h3>Capability Legend</h3>
        {''.join(
            f'<span class="legend-item"><span class="badge" style="background:{CAPABILITY_COLORS[cat]}">'
            f'{CAPABILITY_ICONS[cat]} {cat}</span> weight: {w}</span>'
            for cat, w in sorted(CAPABILITY_WEIGHTS.items(), key=lambda x: -x[1])
        )}
        <div class="formula">
            blast_radius = direct_score + propagated_score(decay={0.5}) + ln(1 + reverse_deps) * 5
        </div>
    </div>
</div>
</body>
</html>"""

    output_path.write_text(report_html)
    return output_path

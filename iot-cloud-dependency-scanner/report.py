"""Report generation module.

Generates CLI output and single-file HTML reports for scan results.
"""

from analyzer import CloudDependencyScore

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IoT Cloud Dependency Report</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e1e4ed;
    --text-muted: #8b8fa3;
    --accent: #6c63ff;
    --accent-light: #8b83ff;
    --critical: #ff4757;
    --high: #ff6b35;
    --medium: #ffc048;
    --low: #2ed573;
    --unknown: #636e72;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
  }
  .container { max-width: 1100px; margin: 0 auto; }
  header {
    text-align: center;
    padding: 2rem 0 3rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
  }
  header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, var(--accent), #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  header p { color: var(--text-muted); font-size: 0.95rem; }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }
  .summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
  }
  .summary-card .number {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
  }
  .summary-card .label {
    color: var(--text-muted);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .device-list { display: flex; flex-direction: column; gap: 1rem; }
  .device-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    transition: border-color 0.2s;
  }
  .device-card:hover { border-color: var(--accent); }
  .device-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }
  .device-name {
    font-size: 1.1rem;
    font-weight: 600;
  }
  .device-meta {
    color: var(--text-muted);
    font-size: 0.85rem;
  }
  .score-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .score-critical { background: rgba(255,71,87,0.15); color: var(--critical); }
  .score-high { background: rgba(255,107,53,0.15); color: var(--high); }
  .score-medium { background: rgba(255,192,72,0.15); color: var(--medium); }
  .score-low { background: rgba(46,213,115,0.15); color: var(--low); }
  .score-unknown { background: rgba(99,110,114,0.15); color: var(--unknown); }
  .score-bar-container {
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    margin: 0.75rem 0;
    overflow: hidden;
  }
  .score-bar {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
  }
  .endpoints {
    margin-top: 0.75rem;
  }
  .endpoints h4 {
    font-size: 0.8rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }
  .endpoint-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .endpoint-tag {
    background: rgba(108,99,255,0.1);
    border: 1px solid rgba(108,99,255,0.2);
    color: var(--accent-light);
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .alternatives {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
  }
  .alternatives h4 {
    font-size: 0.8rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }
  .alt-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0;
  }
  .alt-name {
    font-weight: 500;
    font-size: 0.9rem;
  }
  .alt-type {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    background: rgba(46,213,115,0.1);
    color: var(--low);
  }
  .alt-desc {
    font-size: 0.8rem;
    color: var(--text-muted);
  }
  .stats-row {
    display: flex;
    gap: 1.5rem;
    font-size: 0.85rem;
    color: var(--text-muted);
  }
  .stats-row span { display: flex; align-items: center; gap: 0.3rem; }
  footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-muted);
    font-size: 0.8rem;
  }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>IoT Cloud Dependency Report</h1>
    <p>Network scan results &mdash; {{device_count}} devices analyzed</p>
  </header>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="number">{{device_count}}</div>
      <div class="label">Devices Found</div>
    </div>
    <div class="summary-card">
      <div class="number">{{critical_count}}</div>
      <div class="label">Critical Dependency</div>
    </div>
    <div class="summary-card">
      <div class="number">{{high_count}}</div>
      <div class="label">High Dependency</div>
    </div>
    <div class="summary-card">
      <div class="number">{{avg_score}}</div>
      <div class="label">Avg Score</div>
    </div>
  </div>

  <div class="device-list">
    {{device_cards}}
  </div>

  <footer>
    Generated by IoT Cloud Dependency Scanner
  </footer>
</div>
</body>
</html>"""


def _score_color(rating: str) -> str:
    colors = {
        "Critical": "#ff4757",
        "High": "#ff6b35",
        "Medium": "#ffc048",
        "Low": "#2ed573",
        "Unknown": "#636e72",
    }
    return colors.get(rating, "#636e72")


def _score_class(rating: str) -> str:
    return f"score-{rating.lower()}"


def _render_device_card(result: CloudDependencyScore) -> str:
    device = result.device
    name = device.hostname or f"{device.manufacturer} ({device.ip})"

    # Endpoints
    endpoint_tags = ""
    if result.dns_profile and result.dns_profile.endpoints:
        top_endpoints = sorted(
            result.dns_profile.endpoints.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:8]
        for domain, count in top_endpoints:
            provider = result.cloud_endpoints.get(domain, "")
            label = f"{domain} ({count})"
            if provider:
                label = f"{domain} → {provider} ({count})"
            endpoint_tags += f'<span class="endpoint-tag">{label}</span>\n'

    # Alternatives
    alt_html = ""
    if result.alternatives:
        alt_items = ""
        for alt in result.alternatives[:3]:
            alt_items += f"""
            <div class="alt-item">
              <div>
                <div class="alt-name">{alt.name}</div>
                <div class="alt-desc">{alt.description}</div>
              </div>
              <span class="alt-type">{alt.category}</span>
            </div>"""
        alt_html = f"""
        <div class="alternatives">
          <h4>Local Alternatives</h4>
          {alt_items}
        </div>"""

    color = _score_color(result.rating)

    return f"""
    <div class="device-card">
      <div class="device-header">
        <div>
          <div class="device-name">{name}</div>
          <div class="device-meta">{device.manufacturer} &bull; {device.ip} &bull; {device.mac}</div>
        </div>
        <span class="score-badge {_score_class(result.rating)}">
          {result.rating} &bull; {result.score}
        </span>
      </div>
      <div class="score-bar-container">
        <div class="score-bar" style="width:{min(result.score, 100)}%;background:{color}"></div>
      </div>
      <div class="stats-row">
        <span>Queries: {result.total_queries}</span>
        <span>Rate: {result.query_frequency}/min</span>
        <span>Cloud endpoints: {result.endpoint_diversity}</span>
      </div>
      <div class="endpoints">
        <h4>Top Endpoints</h4>
        <div class="endpoint-list">{endpoint_tags}</div>
      </div>
      {alt_html}
    </div>"""


def generate_html_report(
    results: list[CloudDependencyScore], output_path: str = "report.html"
) -> str:
    """Generate a single-file HTML report."""
    device_cards = "\n".join(_render_device_card(r) for r in results)

    scores = [r.score for r in results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    html = HTML_TEMPLATE
    html = html.replace("{{device_count}}", str(len(results)))
    html = html.replace("{{critical_count}}", str(sum(1 for r in results if r.rating == "Critical")))
    html = html.replace("{{high_count}}", str(sum(1 for r in results if r.rating == "High")))
    html = html.replace("{{avg_score}}", str(avg_score))
    html = html.replace("{{device_cards}}", device_cards)

    with open(output_path, "w") as f:
        f.write(html)

    return output_path


def print_cli_report(results: list[CloudDependencyScore]):
    """Print a formatted CLI report."""
    print("\n" + "=" * 70)
    print("  IoT CLOUD DEPENDENCY REPORT")
    print("=" * 70)

    scores = [r.score for r in results]
    avg = sum(scores) / len(scores) if scores else 0
    critical = sum(1 for r in results if r.rating == "Critical")
    high = sum(1 for r in results if r.rating == "High")

    print(f"\n  Devices: {len(results)}  |  Avg Score: {avg:.1f}")
    print(f"  Critical: {critical}  |  High: {high}")
    print("-" * 70)

    for r in results:
        device = r.device
        name = device.hostname or device.ip
        mfr = device.manufacturer

        # Rating indicator
        indicators = {
            "Critical": "!!!",
            "High": " !! ",
            "Medium": "  ! ",
            "Low": "  . ",
            "Unknown": "  ? ",
        }
        indicator = indicators.get(r.rating, "  ? ")

        print(f"\n  [{indicator}] {name}")
        print(f"       Manufacturer: {mfr}  |  IP: {device.ip}  |  MAC: {device.mac}")
        print(f"       Score: {r.score}/100 ({r.rating})")
        print(f"       Queries: {r.total_queries}  |  Rate: {r.query_frequency}/min  |  Cloud EPs: {r.endpoint_diversity}")

        if r.cloud_endpoints:
            eps = list(r.cloud_endpoints.items())[:5]
            print(f"       Cloud: {', '.join(f'{d} ({p})' for d, p in eps)}")

        if r.alternatives:
            alts = r.alternatives[:2]
            print(f"       Alternatives: {', '.join(a.name for a in alts)}")

    print("\n" + "=" * 70)

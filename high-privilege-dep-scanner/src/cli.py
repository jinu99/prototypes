"""CLI entry point for high-privilege dependency scanner."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .deps import (
    build_dep_graph,
    extract_deps_from_requirements,
    find_site_packages,
    find_venv_python,
)
from .analyzer import scan_package
from .graph import compute_blast_radius
from .report import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="Scan Python project dependencies for high-privilege capabilities",
    )
    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to a Python project with venv and requirements.txt",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output HTML report path (default: <project>/dep-privilege-report.html)",
    )
    parser.add_argument(
        "-n", "--top",
        type=int,
        default=5,
        help="Number of top high-risk packages to highlight (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of HTML",
    )
    args = parser.parse_args()

    project = args.project_path.resolve()
    if not project.exists():
        print(f"Error: project path does not exist: {project}", file=sys.stderr)
        sys.exit(1)

    output = args.output or project / "dep-privilege-report.html"
    start = time.time()

    # Step 1: Find venv and site-packages
    print(f"[1/5] Finding Python environment in {project}...")
    venv_python = find_venv_python(project)
    site_packages = find_site_packages(venv_python)

    if not site_packages:
        print("Error: could not find site-packages. Is there a venv?", file=sys.stderr)
        sys.exit(1)

    print(f"      Python: {venv_python}")
    print(f"      site-packages: {site_packages}")

    # Step 2: Build dependency graph
    print("[2/5] Building dependency graph...")
    dep_graph = build_dep_graph(venv_python)
    print(f"      Found {len(dep_graph)} packages")

    # Step 3: Determine which packages to scan
    req_file = project / "requirements.txt"
    if req_file.exists():
        direct_deps = set(extract_deps_from_requirements(req_file))
        print(f"      Direct dependencies from requirements.txt: {len(direct_deps)}")
    else:
        direct_deps = set(dep_graph.keys())
        print("      No requirements.txt found, scanning all installed packages")

    # Step 4: AST analysis
    print("[3/5] Scanning packages for capabilities (AST analysis)...")
    capabilities = {}
    all_packages = set(dep_graph.keys())
    scanned = 0
    for pkg_name in sorted(all_packages):
        caps = scan_package(pkg_name, site_packages)
        if caps.total_files_scanned > 0:
            capabilities[pkg_name] = caps
            scanned += 1

    print(f"      Scanned {scanned} packages ({sum(c.total_files_scanned for c in capabilities.values())} files)")

    # Step 5: Compute blast radius
    print("[4/5] Computing blast radius scores...")
    scored = compute_blast_radius(dep_graph, capabilities)

    # Step 6: Generate report
    print(f"[5/5] Generating report...")
    project_name = project.name

    if args.json:
        import json
        data = [
            {
                "rank": i + 1,
                "name": p.name,
                "version": p.version,
                "blast_radius": p.blast_radius,
                "direct_score": p.direct_score,
                "propagated_score": p.propagated_score,
                "capabilities": p.capabilities,
                "dep_count": p.dep_count,
                "reverse_dep_count": p.reverse_dep_count,
            }
            for i, p in enumerate(scored)
        ]
        output_json = output.with_suffix(".json")
        output_json.write_text(json.dumps(data, indent=2))
        print(f"\n✓ JSON report: {output_json}")
    else:
        generate_report(scored, project_name, output, top_n=args.top)
        print(f"\n✓ HTML report: {output}")

    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.1f}s")

    # Print top-N summary
    print(f"\n{'='*60}")
    print(f" Top {args.top} High-Privilege Dependencies")
    print(f"{'='*60}")
    for i, pkg in enumerate(scored[:args.top]):
        caps = ", ".join(sorted(pkg.capabilities.keys())) or "none"
        print(f"  #{i+1}  {pkg.name} ({pkg.version})")
        print(f"      Blast Radius: {pkg.blast_radius:.1f}  |  Caps: {caps}")
    print()


if __name__ == "__main__":
    main()

"""CLI entry point: decay-detect scan <repo-path>"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .git_analyzer import (
    get_commit_list, get_python_files_at_commit,
    get_file_content_at_commit, get_churn_stats, get_diff_files,
)
from .dependency_parser import parse_file_imports
from .metrics import build_dependency_graph, count_edges, count_cyclic_dependencies
from .pattern_detector import (
    FileAction, detect_add_delete_patterns, detect_rapid_edits,
)
from .storage import MetricsDB, CommitMetrics, RevertPattern
from .visualizer import (
    display_coupling_trend, display_cyclic_deps_trend,
    display_churn_trend, display_revert_patterns, display_warnings,
)

console = Console()


@click.group()
def main():
    """Vibe Code Decay Detector - Architecture erosion tracker."""
    pass


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option("--max-commits", "-n", default=100,
              help="Maximum number of commits to analyze")
@click.option("--db", default=None, help="SQLite database path")
def scan(repo_path: str, max_commits: int, db: str):
    """Scan a git repository for architecture decay signals."""
    repo = Path(repo_path).resolve()
    db_path = Path(db) if db else repo / ".decay-detect.db"

    console.print(f"\n[bold]Scanning:[/bold] {repo}")
    console.print(f"[bold]Database:[/bold] {db_path}\n")

    store = MetricsDB(db_path)

    # Step 1: Get commit list
    commits = get_commit_list(repo, max_commits)
    if not commits:
        console.print("[red]No commits found in repository.[/red]")
        return

    console.print(f"Found [bold]{len(commits)}[/bold] commits to analyze.\n")

    # Step 2: Analyze each commit
    all_file_actions: list[FileAction] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing commits...", total=len(commits))

        for commit in commits:
            progress.update(task, description=f"[dim]{commit.hash[:7]}[/dim]")

            if store.has_commit(commit.hash):
                # Collect file actions even for cached commits
                diff_files = get_diff_files(repo, commit.hash)
                for df in diff_files:
                    all_file_actions.append(FileAction(
                        commit_hash=commit.hash,
                        timestamp=commit.timestamp,
                        status=df["status"],
                        path=df["path"],
                    ))
                progress.advance(task)
                continue

            # Get source files at this commit
            source_files = get_python_files_at_commit(repo, commit.hash)

            # Parse imports and build dependency graph
            all_edges = []
            for fpath in source_files:
                content = get_file_content_at_commit(repo, commit.hash, fpath)
                if content:
                    try:
                        edges = parse_file_imports(fpath, content)
                        all_edges.extend(edges)
                    except Exception:
                        pass  # Skip unparseable files

            graph = build_dependency_graph(all_edges)
            edge_count = count_edges(graph)
            cyclic_count = count_cyclic_dependencies(graph)

            # Churn stats
            churn = get_churn_stats(repo, commit.hash)

            # File actions for pattern detection
            diff_files = get_diff_files(repo, commit.hash)
            for df in diff_files:
                all_file_actions.append(FileAction(
                    commit_hash=commit.hash,
                    timestamp=commit.timestamp,
                    status=df["status"],
                    path=df["path"],
                ))

            # Store metrics
            store.upsert_metrics(CommitMetrics(
                commit_hash=commit.hash,
                timestamp=commit.timestamp,
                author=commit.author,
                message=commit.message,
                edge_count=edge_count,
                cyclic_dep_count=cyclic_count,
                file_count=len(source_files),
                churn_additions=churn.additions,
                churn_deletions=churn.deletions,
                churn_files_changed=churn.files_changed,
            ))

            progress.advance(task)

    # Step 3: Detect commit-revert patterns
    add_del_patterns = detect_add_delete_patterns(all_file_actions)
    rapid_patterns = detect_rapid_edits(all_file_actions)

    for p in add_del_patterns:
        store.insert_revert_pattern(RevertPattern(
            commit_hash=p["commit1"],
            file_path=p["file"],
            pattern_type=p["type"],
            detail=p["detail"],
        ))
    for p in rapid_patterns:
        store.insert_revert_pattern(RevertPattern(
            commit_hash=p["commit1"],
            file_path=p["file"],
            pattern_type=p["type"],
            detail=p["detail"],
        ))

    # Step 4: Display results
    all_metrics = store.get_all_metrics()
    all_revert = store.get_all_revert_patterns()

    # Summary
    from datetime import datetime
    first_ts = all_metrics[0].timestamp if all_metrics else 0
    last_ts = all_metrics[-1].timestamp if all_metrics else 0
    first_date = datetime.fromtimestamp(first_ts).strftime("%Y-%m-%d") if first_ts else "?"
    last_date = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d") if last_ts else "?"

    console.print(f"\n[bold]Analysis complete[/bold]")
    console.print(f"  Commits: [cyan]{len(all_metrics)}[/cyan]  "
                  f"Period: [cyan]{first_date}[/cyan] → [cyan]{last_date}[/cyan]  "
                  f"Patterns: [cyan]{len(all_revert)}[/cyan]\n")

    display_coupling_trend(all_metrics)
    display_cyclic_deps_trend(all_metrics)
    display_churn_trend(all_metrics)
    display_revert_patterns(all_revert)
    display_warnings(all_metrics)

    console.print(f"\n[dim]Results saved to {db_path}[/dim]\n")
    store.close()


if __name__ == "__main__":
    main()

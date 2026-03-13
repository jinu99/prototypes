"""impact-track CLI — 코드 변경 영향 추적 및 spec 괴리 탐지."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .ast_analyzer import analyze_project
from .diff_parser import get_changed_files, get_git_root
from .display import display_impact_tree, display_spec_report
from .impact_graph import build_impact_graph, find_changed_symbols
from .spec_checker import check_spec, extract_requirements

app = typer.Typer(
    name="impact-track",
    help="AI 코드 변경 영향 추적기 — tree-sitter AST + git diff 분석",
    no_args_is_help=True,
)
console = Console()


@app.command()
def diff(
    revision: str = typer.Argument(
        "HEAD~1",
        help="비교 대상 리비전 (예: HEAD~1, HEAD~3, abc123)",
    ),
    path: Path = typer.Option(
        ".",
        "--path", "-p",
        help="분석할 프로젝트 경로",
    ),
) -> None:
    """git diff에서 변경된 함수/클래스를 식별하고 1-hop downstream 영향을 추적한다."""
    project_root = path.resolve()

    # git 저장소 루트 감지 (--path가 하위 디렉토리일 수 있음)
    try:
        git_root = get_git_root(project_root)
    except RuntimeError as e:
        console.print(f"[red]오류:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"[bold]프로젝트:[/bold] {project_root}")
    console.print(f"[bold]리비전:[/bold] {revision}")
    console.print()

    # 1. git diff 파싱 (git 루트 기준으로 실행)
    console.print("[dim]git diff 분석 중...[/dim]")
    try:
        changed_files = get_changed_files(git_root, revision)
    except RuntimeError as e:
        console.print(f"[red]오류:[/red] {e}")
        raise typer.Exit(1)

    # --path가 하위 디렉토리면, 해당 디렉토리에 속하는 파일만 필터링
    if project_root != git_root:
        rel_prefix = str(project_root.relative_to(git_root))
        changed_files = [cf for cf in changed_files if cf.path.startswith(rel_prefix)]

    if not changed_files:
        console.print("[yellow]변경된 파일이 없습니다.[/yellow]")
        raise typer.Exit(0)

    console.print(f"  변경된 파일: {len(changed_files)}개")
    for cf in changed_files:
        console.print(f"    [cyan]{cf.path}[/cyan] (+{len(cf.added_lines)}/-{len(cf.removed_lines)} lines)")

    # 2. 프로젝트 전체 AST 분석
    console.print("[dim]AST 분석 중...[/dim]")
    analyses = analyze_project(project_root)
    total_symbols = sum(len(a.symbols) for a in analyses)
    console.print(f"  분석된 파일: {len(analyses)}개, 심볼: {total_symbols}개")

    # 3. 변경된 심볼 식별 (git 루트 기준 경로로 매칭)
    changed_symbols = find_changed_symbols(changed_files, analyses, git_root)
    console.print(f"  변경된 심볼: {len(changed_symbols)}개")

    # 4. 1-hop downstream 영향 추적
    console.print("[dim]영향 범위 추적 중...[/dim]")
    impacts = build_impact_graph(changed_symbols, analyses, git_root)

    # 5. 결과 출력
    display_impact_tree(impacts, project_root)


@app.command(name="spec-check")
def spec_check(
    spec_file: Path = typer.Argument(
        ...,
        help="Spec/PRD markdown 파일 경로",
        exists=True,
    ),
    path: Path = typer.Option(
        ".",
        "--path", "-p",
        help="분석할 프로젝트 경로",
    ),
) -> None:
    """Spec 문서의 요구사항을 코드와 매칭하여 구현 상태를 리포트한다."""
    project_root = path.resolve()
    spec_path = spec_file.resolve()

    console.print(f"[bold]프로젝트:[/bold] {project_root}")
    console.print(f"[bold]Spec:[/bold] {spec_path}")
    console.print()

    # 1. Spec 파싱
    console.print("[dim]Spec 파싱 중...[/dim]")
    requirements = extract_requirements(spec_path)
    console.print(f"  요구사항: {len(requirements)}개")

    if not requirements:
        console.print("[yellow]요구사항을 찾지 못했습니다.[/yellow]")
        raise typer.Exit(0)

    # 2. 프로젝트 AST 분석
    console.print("[dim]AST 분석 중...[/dim]")
    analyses = analyze_project(project_root)
    total_symbols = sum(len(a.symbols) for a in analyses)
    console.print(f"  분석된 파일: {len(analyses)}개, 심볼: {total_symbols}개")

    # 3. 매칭 및 리포트
    console.print("[dim]매칭 중...[/dim]")
    results, code_only = check_spec(requirements, analyses)

    display_spec_report(results, code_only, project_root)


if __name__ == "__main__":
    app()

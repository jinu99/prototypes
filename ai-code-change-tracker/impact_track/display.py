"""rich를 사용한 터미널 트리 출력."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .impact_graph import ChangedSymbolImpact
from .spec_checker import CodeOnlySymbol, MatchResult

console = Console()


def _short_path(file_path: str, project_root: Path) -> str:
    """프로젝트 루트 기준 상대 경로를 반환한다."""
    try:
        return str(Path(file_path).relative_to(project_root))
    except ValueError:
        return file_path


def display_impact_tree(
    impacts: list[ChangedSymbolImpact],
    project_root: Path,
) -> None:
    """변경 영향 트리를 터미널에 출력한다."""
    if not impacts:
        console.print("[yellow]변경된 심볼이 없습니다.[/yellow]")
        return

    tree = Tree(
        "[bold blue]📊 Code Change Impact Tree[/bold blue]",
        guide_style="blue",
    )

    for impact in impacts:
        sym = impact.changed
        rel_path = _short_path(sym.file, project_root)
        kind_icon = {"function": "🔧", "class": "📦", "method": "⚙️"}.get(sym.kind, "•")
        qualified = f"{sym.parent_class}.{sym.name}" if sym.parent_class else sym.name

        node_label = (
            f"{kind_icon} [bold yellow]{qualified}[/bold yellow] "
            f"[dim]({sym.kind})[/dim]  "
            f"[cyan]{rel_path}:{sym.start_line}-{sym.end_line}[/cyan]"
        )
        sym_branch = tree.add(node_label)

        if impact.downstream:
            for ds in impact.downstream:
                ds_sym = ds.symbol
                ds_rel = _short_path(ds_sym.file, project_root)
                ds_qualified = (
                    f"{ds_sym.parent_class}.{ds_sym.name}"
                    if ds_sym.parent_class
                    else ds_sym.name
                )
                ds_branch = sym_branch.add(
                    f"[red]↳[/red] [white]{ds_qualified}[/white] "
                    f"[dim]({ds_sym.kind})[/dim]  "
                    f"[cyan]{ds_rel}:{ds_sym.start_line}[/cyan]  "
                    f"[dim italic]← {ds.reason}[/dim italic]"
                )
        else:
            sym_branch.add("[dim]영향 범위 없음 (1-hop downstream 없음)[/dim]")

    console.print()
    console.print(tree)
    console.print()

    # 요약 통계
    total_changed = len(impacts)
    total_downstream = sum(len(i.downstream) for i in impacts)
    console.print(
        f"[bold]요약:[/bold] 변경된 심볼 [yellow]{total_changed}[/yellow]개, "
        f"영향받는 심볼 [red]{total_downstream}[/red]개"
    )


def display_spec_report(
    results: list[MatchResult],
    code_only: list[CodeOnlySymbol],
    project_root: Path,
) -> None:
    """spec-코드 매칭 리포트를 출력한다."""
    # 요구사항 매칭 테이블
    table = Table(
        title="📋 Spec-Code Alignment Report",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("요구사항", max_width=50)
    table.add_column("상태", width=10)
    table.add_column("매칭된 코드", max_width=40)

    status_icons = {
        "구현됨": "[green]✅ 구현됨[/green]",
        "미구현": "[red]❌ 미구현[/red]",
        "부분 구현": "[yellow]⚠️ 부분[/yellow]",
    }

    implemented = 0
    not_implemented = 0

    for i, result in enumerate(results, 1):
        status_display = status_icons.get(result.status, result.status)
        if result.status == "구현됨":
            implemented += 1
        else:
            not_implemented += 1

        matched_str = ""
        if result.matched_symbols:
            names = []
            for sym in result.matched_symbols[:3]:
                rel = _short_path(sym.file, project_root)
                qualified = f"{sym.parent_class}.{sym.name}" if sym.parent_class else sym.name
                names.append(f"{qualified} ({rel}:{sym.start_line})")
            matched_str = "\n".join(names)
            if len(result.matched_symbols) > 3:
                matched_str += f"\n... +{len(result.matched_symbols) - 3}개"

        # 요구사항 텍스트 축약
        req_text = result.requirement.text
        if len(req_text) > 50:
            req_text = req_text[:47] + "..."

        table.add_row(str(i), req_text, status_display, matched_str)

    console.print()
    console.print(table)

    # 코드에만 존재하는 심볼
    if code_only:
        console.print()
        code_tree = Tree(
            "[bold yellow]⚠️ 코드에만 존재 (spec에 미언급)[/bold yellow]",
            guide_style="yellow",
        )
        shown = 0
        for item in code_only:
            if shown >= 15:
                code_tree.add(f"[dim]... +{len(code_only) - 15}개[/dim]")
                break
            sym = item.symbol
            rel = _short_path(sym.file, project_root)
            qualified = f"{sym.parent_class}.{sym.name}" if sym.parent_class else sym.name
            code_tree.add(
                f"[white]{qualified}[/white] [dim]({sym.kind})[/dim]  "
                f"[cyan]{rel}:{sym.start_line}[/cyan]"
            )
            shown += 1
        console.print(code_tree)

    # 요약
    console.print()
    total = implemented + not_implemented
    console.print(
        f"[bold]요약:[/bold] 전체 {total}개 요구사항 중 "
        f"[green]{implemented}[/green]개 구현됨, "
        f"[red]{not_implemented}[/red]개 미구현, "
        f"[yellow]{len(code_only)}[/yellow]개 코드에만 존재"
    )

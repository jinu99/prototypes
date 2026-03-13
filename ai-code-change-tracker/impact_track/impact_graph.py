"""변경된 심볼에서 1-hop downstream 영향 범위를 추적한다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ast_analyzer import FileAnalysis, Symbol, analyze_project
from .diff_parser import ChangedFile


@dataclass
class ImpactedSymbol:
    """영향을 받는 심볼."""
    symbol: Symbol
    reason: str  # e.g. "calls foo", "imports from module"


@dataclass
class ChangedSymbolImpact:
    """변경된 심볼과 그 downstream 영향."""
    changed: Symbol
    downstream: list[ImpactedSymbol] = field(default_factory=list)


def find_changed_symbols(
    changed_files: list[ChangedFile],
    analyses: list[FileAnalysis],
    project_root: Path,
) -> list[Symbol]:
    """변경된 라인 범위에 해당하는 심볼을 찾는다."""
    changed_symbols = []
    # path -> ChangedFile 매핑
    changed_map: dict[str, ChangedFile] = {}
    for cf in changed_files:
        changed_map[cf.path] = cf

    for analysis in analyses:
        # 분석된 파일의 상대 경로
        try:
            rel_path = str(Path(analysis.path).relative_to(project_root))
        except ValueError:
            continue

        cf = changed_map.get(rel_path)
        if not cf:
            continue

        changed_lines = set(cf.added_lines + cf.removed_lines)

        for symbol in analysis.symbols:
            symbol_lines = set(range(symbol.start_line, symbol.end_line + 1))
            if symbol_lines & changed_lines:
                changed_symbols.append(symbol)

    return changed_symbols


def _resolve_module_to_file(
    module: str,
    importer_file: str,
    project_root: Path,
) -> str | None:
    """모듈 경로를 프로젝트 내 파일 경로로 해석한다."""
    # 상대 import: 같은 디렉토리의 모듈
    # 절대 import: 프로젝트 루트 기준
    parts = module.split(".")
    candidates = [
        project_root / Path(*parts) / "__init__.py",
        project_root / Path(*parts).with_suffix(".py"),
    ]
    # importer 기준 상대 경로
    importer_dir = Path(importer_file).parent
    candidates.extend([
        importer_dir / Path(*parts) / "__init__.py",
        importer_dir / Path(*parts).with_suffix(".py"),
    ])

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def build_impact_graph(
    changed_symbols: list[Symbol],
    analyses: list[FileAnalysis],
    project_root: Path,
) -> list[ChangedSymbolImpact]:
    """변경된 심볼들의 1-hop downstream 영향을 추적한다."""
    # 전체 심볼명 → 정의 위치 매핑
    changed_names: set[str] = set()
    for sym in changed_symbols:
        changed_names.add(sym.name)
        if sym.parent_class:
            changed_names.add(f"{sym.parent_class}.{sym.name}")

    # 변경된 심볼을 포함하는 모듈 파일 경로
    changed_files: set[str] = {sym.file for sym in changed_symbols}

    # 변경된 모듈을 import하거나, 변경된 함수를 호출하는 심볼을 찾는다
    results = []
    for sym in changed_symbols:
        impact = ChangedSymbolImpact(changed=sym)

        for analysis in analyses:
            if analysis.path == sym.file:
                # 같은 파일 내에서 변경된 함수를 호출하는 다른 함수
                for other_sym in analysis.symbols:
                    if other_sym.name == sym.name:
                        continue
                    if sym.name in other_sym.calls:
                        impact.downstream.append(ImpactedSymbol(
                            symbol=other_sym,
                            reason=f"calls {sym.name}",
                        ))
                    # ClassName.method 형태 호출 체크
                    if sym.parent_class:
                        qualified = f"{sym.parent_class}.{sym.name}"
                        if qualified in other_sym.calls:
                            impact.downstream.append(ImpactedSymbol(
                                symbol=other_sym,
                                reason=f"calls {qualified}",
                            ))
            else:
                # 다른 파일에서 import 후 호출
                imports_changed_module = False
                imported_names: set[str] = set()

                for imp in analysis.imports:
                    resolved = _resolve_module_to_file(
                        imp.module, analysis.path, project_root
                    )
                    if resolved and resolved in changed_files:
                        imports_changed_module = True
                        imported_names.update(imp.names)

                    # from X import name 형태에서 직접 이름 매칭
                    if sym.name in imp.names:
                        imports_changed_module = True
                        imported_names.add(sym.name)

                if not imports_changed_module:
                    continue

                # 이 파일의 심볼 중 변경된 함수를 호출하는 것
                for other_sym in analysis.symbols:
                    if sym.name in other_sym.calls:
                        impact.downstream.append(ImpactedSymbol(
                            symbol=other_sym,
                            reason=f"imports and calls {sym.name}",
                        ))
                    if sym.parent_class:
                        qualified = f"{sym.parent_class}.{sym.name}"
                        if qualified in other_sym.calls:
                            impact.downstream.append(ImpactedSymbol(
                                symbol=other_sym,
                                reason=f"imports and calls {qualified}",
                            ))

                # import만 하고 있어도 영향 표시 ("*" = 모듈 전체 import)
                if "*" in imported_names or sym.name in imported_names:
                    # 파일 수준의 영향도 기록 (호출 없이 import만 한 경우)
                    already_added = {ds.symbol.file for ds in impact.downstream}
                    if analysis.path not in already_added:
                        # import 관계만으로도 영향 표시
                        for other_sym in analysis.symbols:
                            if other_sym.kind in ("function", "method") and other_sym not in [
                                ds.symbol for ds in impact.downstream
                            ]:
                                # 해당 파일의 함수들이 영향 가능성 있음
                                pass  # 호출 없으면 skip

        results.append(impact)

    return results

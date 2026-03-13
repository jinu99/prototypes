"""Spec/PRD markdown 문서의 요구사항을 코드 심볼과 매칭하여 괴리 리포트를 생성한다."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .ast_analyzer import FileAnalysis, Symbol


@dataclass
class Requirement:
    text: str
    keywords: list[str]
    line_number: int


@dataclass
class MatchResult:
    requirement: Requirement
    status: str  # "구현됨" | "미구현" | "부분 구현"
    matched_symbols: list[Symbol] = field(default_factory=list)


@dataclass
class CodeOnlySymbol:
    """spec에 언급되지 않은 코드 심볼."""
    symbol: Symbol
    status: str = "코드에만 존재"


def extract_requirements(spec_path: str | Path) -> list[Requirement]:
    """markdown spec 파일에서 요구사항 항목을 추출한다.

    체크리스트 형태 (- [ ] ...), 번호 매기기 (1. ...), 또는 불릿 (- ...) 항목을 인식한다.
    **제외**, **기술 제약** 등 비-요구사항 섹션은 건너뛴다.
    """
    spec_path = Path(spec_path)
    text = spec_path.read_text(encoding="utf-8")
    requirements = []

    # 제외할 섹션 헤딩 패턴
    skip_section_patterns = {"제외", "기술 제약", "심의", "excluded", "constraints"}
    in_skip_section = False
    current_heading_level = 0

    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 헤딩 감지: ## 제외, ## 기술 제약 등
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip().lower()
            # **볼드** 마커 제거
            heading_text = re.sub(r"\*\*", "", heading_text)
            if any(skip in heading_text for skip in skip_section_patterns):
                in_skip_section = True
                current_heading_level = level
            elif level <= current_heading_level:
                in_skip_section = False
            continue

        # **포함**: / **제외**: 같은 인라인 섹션 마커
        if stripped.startswith("- **제외") or stripped.startswith("- **기술"):
            in_skip_section = True
            continue
        if stripped.startswith("- **포함") or stripped.startswith("- **범위"):
            in_skip_section = False
            continue

        if in_skip_section:
            continue

        # 체크리스트: - [ ] 또는 - [x] — 항상 요구사항으로 추출
        if re.match(r"^-\s*\[[ x]\]\s+", stripped):
            content = re.sub(r"^-\s*\[[ x]\]\s+", "", stripped)
            keywords = _extract_keywords(content)
            requirements.append(Requirement(
                text=content, keywords=keywords, line_number=i
            ))
        # 번호 리스트: 1. ...
        elif re.match(r"^\d+\.\s+", stripped):
            content = re.sub(r"^\d+\.\s+", "", stripped)
            keywords = _extract_keywords(content)
            if keywords:
                requirements.append(Requirement(
                    text=content, keywords=keywords, line_number=i
                ))
        # 불릿: - ...
        elif re.match(r"^[-*]\s+", stripped) and not stripped.startswith("---"):
            content = re.sub(r"^[-*]\s+", "", stripped)
            # 섹션 마커 제거 (**포함**: 등)
            if content.startswith("**") and "**:" in content:
                continue
            keywords = _extract_keywords(content)
            if keywords:
                requirements.append(Requirement(
                    text=content, keywords=keywords, line_number=i
                ))

    return requirements


def _extract_keywords(text: str) -> list[str]:
    """요구사항 텍스트에서 코드 매칭용 키워드를 추출한다.

    백틱으로 감싼 코드, snake_case 단어, camelCase 단어를 우선 추출하고,
    의미 있는 일반 단어도 포함한다.
    """
    keywords = []

    # 백틱 코드: `foo_bar`, `ClassName`
    backtick_matches = re.findall(r"`([^`]+)`", text)
    for m in backtick_matches:
        # 공백이 있으면 명령어일 수 있으므로 각 단어를 키워드로
        for word in m.split():
            cleaned = word.strip("(){}[]<>,;:")
            if cleaned and len(cleaned) > 1:
                keywords.append(cleaned.lower())

    # snake_case / camelCase 단어
    words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text)
    for w in words:
        lower = w.lower()
        if "_" in w or (any(c.isupper() for c in w[1:]) and any(c.islower() for c in w)):
            if lower not in keywords and len(lower) > 2:
                keywords.append(lower)

    # 일반 의미어 (동사/명사 형태, 짧은 단어 제외)
    stop_words = {
        "the", "and", "for", "with", "from", "this", "that", "are", "was",
        "will", "can", "not", "all", "has", "have", "had", "been", "each",
        "when", "where", "which", "who", "how", "into", "out", "use", "using",
        "used", "does", "should", "would", "could", "may", "might", "must",
        "also", "only", "just", "than", "then", "very", "about", "over",
        "through", "between", "both", "some", "any", "such", "other", "its",
    }
    for w in words:
        lower = w.lower()
        if lower not in keywords and lower not in stop_words and len(lower) > 3:
            keywords.append(lower)

    return keywords


def check_spec(
    requirements: list[Requirement],
    analyses: list[FileAnalysis],
) -> tuple[list[MatchResult], list[CodeOnlySymbol]]:
    """요구사항과 코드 심볼을 매칭하여 결과를 반환한다."""
    # 모든 심볼 수집
    all_symbols: list[Symbol] = []
    for analysis in analyses:
        all_symbols.extend(analysis.symbols)

    # 심볼명 → Symbol 매핑 (lowercase)
    symbol_map: dict[str, list[Symbol]] = {}
    for sym in all_symbols:
        key = sym.name.lower()
        symbol_map.setdefault(key, []).append(sym)
        if sym.parent_class:
            qualified = f"{sym.parent_class}.{sym.name}".lower()
            symbol_map.setdefault(qualified, []).append(sym)

    # 요구사항별 매칭
    matched_symbol_names: set[str] = set()
    results = []

    for req in requirements:
        matched: list[Symbol] = []
        for kw in req.keywords:
            kw_lower = kw.lower()
            # 정확한 이름 매칭
            if kw_lower in symbol_map:
                for sym in symbol_map[kw_lower]:
                    if sym not in matched:
                        matched.append(sym)
                        matched_symbol_names.add(sym.name.lower())
            # 부분 매칭: 키워드가 심볼명에 포함
            for sym_name, syms in symbol_map.items():
                if kw_lower in sym_name and len(kw_lower) > 3:
                    for sym in syms:
                        if sym not in matched:
                            matched.append(sym)
                            matched_symbol_names.add(sym.name.lower())

        if matched:
            status = "구현됨"
        else:
            status = "미구현"

        results.append(MatchResult(
            requirement=req,
            status=status,
            matched_symbols=matched,
        ))

    # 코드에만 존재하는 심볼 (spec에 매칭되지 않은 것)
    code_only = []
    for sym in all_symbols:
        if sym.name.lower() not in matched_symbol_names:
            # 던더 메서드, 프라이빗 메서드 제외
            if sym.name.startswith("_"):
                continue
            code_only.append(CodeOnlySymbol(symbol=sym))

    return results, code_only

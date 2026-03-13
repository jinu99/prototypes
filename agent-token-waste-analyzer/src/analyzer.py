"""Waste pattern detection engine — identifies token waste in agent sessions."""

from dataclasses import dataclass, field
from .parser import SessionData, ToolCall


@dataclass
class WastePattern:
    pattern_type: str  # repeated_read, unused_search, duplicate_context
    description: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    wasted_tokens: int = 0
    occurrences: int = 0
    target: str = ""


@dataclass
class OptimizationSuggestion:
    title: str
    description: str
    estimated_savings: int = 0


@dataclass
class AnalysisResult:
    session_id: str
    waste_patterns: list[WastePattern] = field(default_factory=list)
    suggestions: list[OptimizationSuggestion] = field(default_factory=list)
    total_tokens: int = 0
    effective_tokens: int = 0
    wasted_tokens: int = 0

    @property
    def effective_ratio(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return self.effective_tokens / self.total_tokens

    @property
    def waste_ratio(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return self.wasted_tokens / self.total_tokens


def detect_repeated_reads(session: SessionData) -> list[WastePattern]:
    """Detect files that are read multiple times in the same session."""
    read_calls: dict[str, list[ToolCall]] = {}
    for tc in session.tool_calls:
        if tc.name == "Read" and tc.target:
            read_calls.setdefault(tc.target, []).append(tc)

    patterns = []
    for filepath, calls in read_calls.items():
        if len(calls) >= 2:
            # Estimate wasted tokens: each redundant read costs ~input tokens
            avg_tokens = sum(
                c.token_usage.get("input_tokens", 0)
                + c.token_usage.get("cache_read_input_tokens", 0)
                for c in calls
            ) // len(calls)
            redundant_count = len(calls) - 1
            wasted = avg_tokens * redundant_count

            patterns.append(WastePattern(
                pattern_type="repeated_read",
                description=f"File read {len(calls)} times: {filepath}",
                tool_calls=calls,
                wasted_tokens=wasted,
                occurrences=len(calls),
                target=filepath,
            ))

    return sorted(patterns, key=lambda p: p.wasted_tokens, reverse=True)


def detect_unused_searches(session: SessionData) -> list[WastePattern]:
    """Detect Grep/Glob searches whose results were never used.

    Heuristic: if a search tool is called but the next assistant action
    doesn't reference any of the searched targets (no Read/Edit on found files),
    the search was likely unused.
    """
    patterns = []
    search_tools = {"Grep", "Glob"}

    for i, tc in enumerate(session.tool_calls):
        if tc.name not in search_tools:
            continue

        # Look at the next few tool calls after this search
        next_calls = session.tool_calls[i + 1: i + 4]
        search_target = tc.target

        # Check if any subsequent call references something related
        was_used = False
        for next_tc in next_calls:
            if next_tc.name in ("Read", "Edit", "Write"):
                # If the file being read/edited could be a search result
                if search_target and (
                    search_target in next_tc.target
                    or _paths_related(search_target, next_tc.target)
                ):
                    was_used = True
                    break

        if not was_used:
            token_cost = (
                tc.token_usage.get("input_tokens", 0)
                + tc.token_usage.get("cache_read_input_tokens", 0)
                + tc.token_usage.get("output_tokens", 0)
            )
            patterns.append(WastePattern(
                pattern_type="unused_search",
                description=f"Search result not followed up: {tc.name}('{search_target}')",
                tool_calls=[tc],
                wasted_tokens=token_cost,
                occurrences=1,
                target=search_target,
            ))

    return sorted(patterns, key=lambda p: p.wasted_tokens, reverse=True)


def detect_duplicate_context(session: SessionData) -> list[WastePattern]:
    """Detect duplicate context loading — same large content sent multiple turns.

    Heuristic: if cache_read_input_tokens stays constant or grows monotonically
    with big jumps, context is being re-loaded. We flag turns where cache_read
    is disproportionately large compared to new input.
    """
    patterns = []
    high_cache_turns = []

    for msg in session.messages:
        usage = msg.token_usage
        if not usage:
            continue
        cache_read = usage.get("cache_read_input_tokens", 0)
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Flag if cache read is >95% of total input and output is tiny
        total_in = cache_read + input_tokens
        if total_in > 1000 and cache_read > 0 and output_tokens > 0:
            cache_ratio = cache_read / total_in
            output_efficiency = output_tokens / total_in
            if cache_ratio > 0.95 and output_efficiency < 0.01:
                high_cache_turns.append((msg, cache_read, output_tokens))

    if len(high_cache_turns) >= 3:
        total_wasted = sum(t[1] for t in high_cache_turns)
        patterns.append(WastePattern(
            pattern_type="duplicate_context",
            description=(
                f"{len(high_cache_turns)} turns with >95% cache reads "
                f"and <1% output efficiency — context being re-loaded repeatedly"
            ),
            wasted_tokens=total_wasted // 2,  # Conservative: half is waste
            occurrences=len(high_cache_turns),
            target="session context",
        ))

    return patterns


def generate_suggestions(
    patterns: list[WastePattern], session: SessionData
) -> list[OptimizationSuggestion]:
    """Generate optimization suggestions based on detected patterns."""
    suggestions = []
    pattern_types = {p.pattern_type for p in patterns}

    if "repeated_read" in pattern_types:
        repeated = [p for p in patterns if p.pattern_type == "repeated_read"]
        total_waste = sum(p.wasted_tokens for p in repeated)
        suggestions.append(OptimizationSuggestion(
            title="Avoid re-reading files",
            description=(
                f"{len(repeated)} files were read multiple times. "
                "Cache file contents in context or use targeted line-range reads "
                "instead of re-reading entire files."
            ),
            estimated_savings=total_waste,
        ))

    if "unused_search" in pattern_types:
        unused = [p for p in patterns if p.pattern_type == "unused_search"]
        total_waste = sum(p.wasted_tokens for p in unused)
        suggestions.append(OptimizationSuggestion(
            title="Use targeted searches",
            description=(
                f"{len(unused)} search results were not followed up on. "
                "Formulate more specific queries or skip exploratory searches "
                "when the target is already known."
            ),
            estimated_savings=total_waste,
        ))

    if "duplicate_context" in pattern_types:
        dup = [p for p in patterns if p.pattern_type == "duplicate_context"]
        total_waste = sum(p.wasted_tokens for p in dup)
        suggestions.append(OptimizationSuggestion(
            title="Reduce context re-loading",
            description=(
                "Many turns re-loaded large context with minimal new output. "
                "Consider batching tool calls or reducing conversation turns."
            ),
            estimated_savings=total_waste,
        ))

    return suggestions


def analyze_session(session: SessionData) -> AnalysisResult:
    """Run all waste pattern detectors on a session and return analysis."""
    all_patterns = []
    all_patterns.extend(detect_repeated_reads(session))
    all_patterns.extend(detect_unused_searches(session))
    all_patterns.extend(detect_duplicate_context(session))

    total_tokens = (
        session.total_input_tokens
        + session.total_output_tokens
        + session.total_cache_read_tokens
        + session.total_cache_creation_tokens
    )
    wasted_tokens = sum(p.wasted_tokens for p in all_patterns)
    effective_tokens = max(0, total_tokens - wasted_tokens)

    suggestions = generate_suggestions(all_patterns, session)

    return AnalysisResult(
        session_id=session.session_id,
        waste_patterns=all_patterns,
        suggestions=suggestions,
        total_tokens=total_tokens,
        effective_tokens=effective_tokens,
        wasted_tokens=wasted_tokens,
    )


def _paths_related(pattern: str, filepath: str) -> bool:
    """Check if a search pattern is related to a file path."""
    if not pattern or not filepath:
        return False
    # Glob pattern match heuristic
    pattern_parts = pattern.replace("*", "").replace("?", "").split("/")
    for part in pattern_parts:
        if part and part in filepath:
            return True
    return False

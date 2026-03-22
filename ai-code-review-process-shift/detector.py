"""Rule-based intent mismatch detection between prompts and code changes."""

import re
from dataclasses import dataclass
from parser import PromptSegment


@dataclass
class Mismatch:
    rule_name: str
    severity: str  # "warning", "error"
    description: str
    prompt_snippet: str
    detail: str


# Korean and English keyword pairs for detection
DELETE_KEYWORDS = [
    "삭제", "제거", "지워", "없애", "remove", "delete", "drop", "rid of"
]
ADD_KEYWORDS = [
    "추가", "새로", "만들", "생성", "add", "create", "new", "implement"
]
RENAME_KEYWORDS = [
    "이름", "rename", "변경", "바꿔", "change name"
]
TEST_KEYWORDS = [
    "테스트", "test", "검증", "확인"
]


def _prompt_contains(text: str, keywords: list[str]) -> list[str]:
    """Check if prompt contains any of the keywords."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw in text_lower]


def _count_deletions(segment: PromptSegment) -> int:
    """Count lines deleted across all file changes."""
    count = 0
    for fc in segment.file_changes:
        if fc.change_type == "edit" and fc.old_string and fc.new_string:
            old_lines = len(fc.old_string.strip().splitlines())
            new_lines = len(fc.new_string.strip().splitlines())
            if old_lines > new_lines:
                count += old_lines - new_lines
        elif fc.change_type == "edit" and fc.old_string and not fc.new_string:
            count += len(fc.old_string.strip().splitlines())
    return count


def _count_additions(segment: PromptSegment) -> int:
    """Count lines added across all file changes."""
    count = 0
    for fc in segment.file_changes:
        if fc.change_type == "write":
            count += len((fc.new_string or "").strip().splitlines())
        elif fc.change_type == "edit" and fc.new_string:
            old_lines = len((fc.old_string or "").strip().splitlines())
            new_lines = len(fc.new_string.strip().splitlines())
            if new_lines > old_lines:
                count += new_lines - old_lines
    return count


def _get_changed_files(segment: PromptSegment) -> set[str]:
    return {fc.file_path for fc in segment.file_changes}


def detect_mismatches(segment: PromptSegment) -> list[Mismatch]:
    """Run all mismatch rules on a single prompt segment."""
    mismatches = []
    prompt = segment.prompt_text

    # Rule 1: Prompt says "delete" but no deletions
    del_kws = _prompt_contains(prompt, DELETE_KEYWORDS)
    if del_kws and _count_deletions(segment) == 0 and segment.file_changes:
        mismatches.append(Mismatch(
            rule_name="delete_without_deletion",
            severity="warning",
            description="프롬프트에 삭제 의도가 있으나 실제 삭제된 코드 없음",
            prompt_snippet=del_kws[0],
            detail=f"키워드 '{del_kws[0]}' 발견, 삭제된 라인 0개",
        ))

    # Rule 2: Prompt says "add/create" but no additions
    add_kws = _prompt_contains(prompt, ADD_KEYWORDS)
    if add_kws and _count_additions(segment) == 0 and segment.file_changes:
        mismatches.append(Mismatch(
            rule_name="add_without_addition",
            severity="warning",
            description="프롬프트에 추가 의도가 있으나 실제 추가된 코드 없음",
            prompt_snippet=add_kws[0],
            detail=f"키워드 '{add_kws[0]}' 발견, 추가된 라인 0개",
        ))

    # Rule 3: No file changes despite code-related prompt
    code_indicators = ["파일", "코드", "함수", "클래스", "file", "code",
                       "function", "class", "component", "module"]
    code_kws = _prompt_contains(prompt, code_indicators)
    if code_kws and not segment.file_changes and segment.tool_calls:
        mismatches.append(Mismatch(
            rule_name="code_prompt_no_changes",
            severity="warning",
            description="코드 관련 프롬프트지만 파일 변경 없음",
            prompt_snippet=code_kws[0],
            detail=f"Tool call {len(segment.tool_calls)}개 있으나 파일 변경 0개",
        ))

    # Rule 4: File mentioned in prompt but not in changes
    file_pattern = re.compile(r'[\w/.-]+\.\w{1,5}')
    mentioned_files = set(file_pattern.findall(prompt))
    # Filter to likely source file paths (exclude log files, config, etc.)
    exclude_ext = {".jsonl", ".json", ".log", ".env", ".lock", ".toml", ".yml",
                   ".yaml", ".cfg", ".ini", ".txt", ".png", ".jpg", ".svg"}
    likely_files = {f for f in mentioned_files
                    if ("/" in f or f.endswith((".py", ".js", ".ts", ".jsx",
                                               ".tsx", ".css", ".html")))
                    and not any(f.endswith(e) for e in exclude_ext)
                    and not f.startswith("/home/") and len(f) < 80}
    changed_files = _get_changed_files(segment)
    if likely_files and changed_files:
        for mf in likely_files:
            if not any(mf in cf for cf in changed_files):
                mismatches.append(Mismatch(
                    rule_name="mentioned_file_not_changed",
                    severity="warning",
                    description=f"프롬프트에 언급된 파일이 변경되지 않음",
                    prompt_snippet=mf,
                    detail=f"'{mf}'가 프롬프트에 있으나 변경된 파일에 없음",
                ))

    # Rule 5: Large scope change (many files) from short prompt
    if len(prompt.strip()) < 50 and len(changed_files) > 5:
        mismatches.append(Mismatch(
            rule_name="scope_mismatch",
            severity="error",
            description="짧은 프롬프트에 비해 변경 범위가 과도하게 넓음",
            prompt_snippet=prompt[:50],
            detail=f"프롬프트 {len(prompt)}자, 변경 파일 {len(changed_files)}개",
        ))

    return mismatches

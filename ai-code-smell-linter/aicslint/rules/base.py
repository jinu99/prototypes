"""Base class for code smell rules."""

from dataclasses import dataclass, field


@dataclass
class SmellResult:
    rule_id: str
    rule_name: str
    severity: str  # critical, warning, info
    message: str
    file: str
    line: int
    end_line: int | None = None
    snippet: str = ""


class BaseRule:
    rule_id: str = ""
    rule_name: str = ""
    severity: str = "warning"
    description: str = ""
    languages: list[str] = []

    def check(self, tree, source: str, lang: str, filepath: str) -> list[SmellResult]:
        raise NotImplementedError

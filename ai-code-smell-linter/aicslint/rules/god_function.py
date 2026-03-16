"""Rule: God function (excessive length + complexity).

AI models tend to generate monolithic functions that do too many things.
This rule flags functions exceeding a line threshold with high nesting depth.
Traditional linters check line count OR complexity, but not the combination
that characterizes AI-generated "dump everything in one function" patterns.
"""

from .base import BaseRule, SmellResult

MAX_LINES = 40
MAX_DEPTH = 5


class GodFunctionRule(BaseRule):
    rule_id = "ACS003"
    rule_name = "god-function"
    severity = "warning"
    description = "Function is excessively long with deep nesting (AI dump pattern)"
    languages = ["python", "javascript", "typescript"]

    def check(self, tree, source: str, lang: str, filepath: str) -> list[SmellResult]:
        results = []
        self._walk(tree.root_node, source, lang, filepath, results)
        return results

    def _walk(self, node, source, lang, filepath, results):
        func_types = {
            "python": ("function_definition",),
            "javascript": ("function_declaration", "arrow_function", "method_definition"),
            "typescript": ("function_declaration", "arrow_function", "method_definition"),
        }
        if node.type in func_types.get(lang, ()):
            start = node.start_point[0]
            end = node.end_point[0]
            line_count = end - start + 1
            max_depth = self._max_nesting_depth(node, 0)

            if line_count > MAX_LINES and max_depth >= MAX_DEPTH:
                name = self._get_func_name(node)
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=f"Function '{name}' is {line_count} lines with nesting depth {max_depth}",
                    file=filepath,
                    line=start + 1,
                    end_line=end + 1,
                    snippet=f"{name}(...)  # {line_count} lines, depth {max_depth}",
                ))
        for child in node.children:
            self._walk(child, source, lang, filepath, results)

    def _get_func_name(self, node) -> str:
        for child in node.children:
            if child.type in ("identifier", "property_identifier"):
                return child.text.decode()
        return "<anonymous>"

    def _max_nesting_depth(self, node, current_depth) -> int:
        nesting_types = (
            "if_statement", "for_statement", "while_statement",
            "try_statement", "with_statement",  # Python
            "if_statement", "for_statement", "for_in_statement",
            "while_statement", "try_statement", "switch_statement",  # JS
        )
        depth = current_depth
        if node.type in nesting_types:
            depth = current_depth + 1
        max_d = depth
        for child in node.children:
            child_depth = self._max_nesting_depth(child, depth)
            if child_depth > max_d:
                max_d = child_depth
        return max_d

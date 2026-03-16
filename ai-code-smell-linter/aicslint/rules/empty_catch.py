"""Rule: Empty catch/except blocks.

AI-generated code often wraps operations in try/catch with empty handlers,
silently swallowing errors. Traditional linters may flag bare `except:` but
miss `except Exception: pass` or JS `catch(e) {}` patterns.
"""

from .base import BaseRule, SmellResult


class EmptyCatchRule(BaseRule):
    rule_id = "ACS001"
    rule_name = "empty-catch"
    severity = "critical"
    description = "Empty catch/except block silently swallows errors"
    languages = ["python", "javascript", "typescript"]

    def check(self, tree, source: str, lang: str, filepath: str) -> list[SmellResult]:
        results = []
        if lang == "python":
            results = self._check_python(tree, source, filepath)
        elif lang in ("javascript", "typescript"):
            results = self._check_js(tree, source, filepath)
        return results

    def _check_python(self, tree, source: str, filepath: str) -> list[SmellResult]:
        results = []
        self._find_python_except(tree.root_node, source, filepath, results)
        return results

    def _find_python_except(self, node, source, filepath, results):
        if node.type == "except_clause":
            body = None
            for child in node.children:
                if child.type == "block":
                    body = child
                    break
            if body and self._is_empty_or_pass(body):
                line = node.start_point[0] + 1
                snippet = source.split("\n")[line - 1].strip() if line <= len(source.split("\n")) else ""
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=self.description,
                    file=filepath,
                    line=line,
                    snippet=snippet,
                ))
        for child in node.children:
            self._find_python_except(child, source, filepath, results)

    def _is_empty_or_pass(self, block_node) -> bool:
        """Check if block is empty or contains only `pass` or `...`."""
        stmts = [c for c in block_node.children if c.type not in ("comment", "newline", ":")]
        if len(stmts) == 0:
            return True
        if len(stmts) == 1:
            s = stmts[0]
            if s.type == "pass_statement":
                return True
            if s.type == "expression_statement":
                for c in s.children:
                    if c.type == "ellipsis":
                        return True
        return False

    def _check_js(self, tree, source: str, filepath: str) -> list[SmellResult]:
        results = []
        self._find_js_catch(tree.root_node, source, filepath, results)
        return results

    def _find_js_catch(self, node, source, filepath, results):
        if node.type == "catch_clause":
            body = None
            for child in node.children:
                if child.type == "statement_block":
                    body = child
                    break
            if body and self._is_empty_block_js(body):
                line = node.start_point[0] + 1
                snippet = source.split("\n")[line - 1].strip() if line <= len(source.split("\n")) else ""
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=self.description,
                    file=filepath,
                    line=line,
                    snippet=snippet,
                ))
        for child in node.children:
            self._find_js_catch(child, source, filepath, results)

    def _is_empty_block_js(self, block_node) -> bool:
        stmts = [c for c in block_node.children if c.type not in ("comment", "{", "}")]
        return len(stmts) == 0

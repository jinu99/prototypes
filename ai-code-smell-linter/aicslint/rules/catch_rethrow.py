"""Rule: Catch-and-rethrow without modification.

AI often generates try/except blocks that catch an exception only to re-raise
it unchanged — adding noise without value. ESLint/Pylint don't flag this.
"""

from .base import BaseRule, SmellResult


class CatchRethrowRule(BaseRule):
    rule_id = "ACS002"
    rule_name = "catch-and-rethrow"
    severity = "warning"
    description = "Catch block only re-raises/re-throws the same exception"
    languages = ["python", "javascript", "typescript"]

    def check(self, tree, source: str, lang: str, filepath: str) -> list[SmellResult]:
        results = []
        if lang == "python":
            self._walk_python(tree.root_node, source, filepath, results)
        elif lang in ("javascript", "typescript"):
            self._walk_js(tree.root_node, source, filepath, results)
        return results

    def _walk_python(self, node, source, filepath, results):
        if node.type == "except_clause":
            body = None
            exc_name = None
            for child in node.children:
                if child.type == "block":
                    body = child
                if child.type == "as_pattern":
                    for c in child.children:
                        if c.type == "as_pattern_target":
                            exc_name = c.text.decode()
                elif child.type == "identifier":
                    # Could be exception type, skip
                    pass
            if body and self._is_bare_reraise_python(body, exc_name):
                line = node.start_point[0] + 1
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=self.description,
                    file=filepath,
                    line=line,
                    snippet=source.split("\n")[line - 1].strip(),
                ))
        for child in node.children:
            self._walk_python(child, source, filepath, results)

    def _is_bare_reraise_python(self, block, exc_name) -> bool:
        stmts = [c for c in block.children if c.type not in ("comment", "newline", ":")]
        if len(stmts) != 1:
            return False
        stmt = stmts[0]
        if stmt.type == "raise_statement":
            # bare `raise` or `raise e` where e is the caught exception
            children = [c for c in stmt.children if c.type != "raise"]
            if len(children) == 0:
                return True  # bare raise
            if len(children) == 1 and children[0].type == "identifier":
                if exc_name and children[0].text.decode() == exc_name:
                    return True
        return False

    def _walk_js(self, node, source, filepath, results):
        if node.type == "catch_clause":
            param_name = None
            body = None
            for child in node.children:
                if child.type == "identifier":
                    param_name = child.text.decode()
                if child.type == "catch_parameter":
                    for c in child.children:
                        if c.type == "identifier":
                            param_name = c.text.decode()
                if child.type == "statement_block":
                    body = child
            if body and self._is_bare_rethrow_js(body, param_name):
                line = node.start_point[0] + 1
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=self.description,
                    file=filepath,
                    line=line,
                    snippet=source.split("\n")[line - 1].strip(),
                ))
        for child in node.children:
            self._walk_js(child, source, filepath, results)

    def _is_bare_rethrow_js(self, block, param_name) -> bool:
        stmts = [c for c in block.children if c.type not in ("comment", "{", "}")]
        if len(stmts) != 1:
            return False
        stmt = stmts[0]
        if stmt.type == "throw_statement":
            thrown = [c for c in stmt.children if c.type not in ("throw", ";")]
            if len(thrown) == 1 and thrown[0].type == "identifier":
                if param_name and thrown[0].text.decode() == param_name:
                    return True
        return False

"""Rule: Hardcoded secret patterns.

AI assistants frequently generate placeholder secrets, API keys, and tokens
directly in source code. While some linters check for specific patterns,
this rule uses AST-aware detection to find assignments to secret-like variable
names with literal string values — reducing false positives from comments/docs.
"""

import re
from .base import BaseRule, SmellResult

SECRET_PATTERNS = re.compile(
    r"(api_?key|secret_?key|password|passwd|token|auth_?token|"
    r"access_?key|private_?key|client_?secret|db_?password|"
    r"api_?secret|jwt_?secret|encryption_?key)",
    re.IGNORECASE,
)

# Common false positives
FALSE_POSITIVE_VALUES = {"", "None", "null", "undefined", "TODO", "CHANGEME", "your-key-here"}


class HardcodedSecretRule(BaseRule):
    rule_id = "ACS004"
    rule_name = "hardcoded-secret"
    severity = "critical"
    description = "Potential hardcoded secret/credential in source code"
    languages = ["python", "javascript", "typescript"]

    def check(self, tree, source: str, lang: str, filepath: str) -> list[SmellResult]:
        results = []
        if lang == "python":
            self._walk_python(tree.root_node, source, filepath, results)
        elif lang in ("javascript", "typescript"):
            self._walk_js(tree.root_node, source, filepath, results)
        return results

    def _walk_python(self, node, source, filepath, results):
        # assignment: identifier = string
        if node.type == "assignment":
            left = node.children[0] if node.children else None
            right = node.children[-1] if len(node.children) >= 3 else None
            if left and right:
                var_name = left.text.decode() if left.type == "identifier" else ""
                if SECRET_PATTERNS.search(var_name) and right.type == "string":
                    val = right.text.decode().strip("'\"")
                    if val not in FALSE_POSITIVE_VALUES and len(val) >= 4:
                        line = node.start_point[0] + 1
                        results.append(SmellResult(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=self.severity,
                            message=f"Hardcoded secret in variable '{var_name}'",
                            file=filepath,
                            line=line,
                            snippet=source.split("\n")[line - 1].strip(),
                        ))
        for child in node.children:
            self._walk_python(child, source, filepath, results)

    def _walk_js(self, node, source, filepath, results):
        # variable_declarator or assignment_expression
        if node.type in ("variable_declarator", "assignment_expression"):
            name_node = None
            value_node = None
            for child in node.children:
                if child.type in ("identifier", "property_identifier"):
                    name_node = child
                if child.type == "string":
                    value_node = child
            if name_node and value_node:
                var_name = name_node.text.decode()
                if SECRET_PATTERNS.search(var_name):
                    val = value_node.text.decode().strip("'\"`")
                    if val not in FALSE_POSITIVE_VALUES and len(val) >= 4:
                        line = node.start_point[0] + 1
                        results.append(SmellResult(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=self.severity,
                            message=f"Hardcoded secret in variable '{var_name}'",
                            file=filepath,
                            line=line,
                            snippet=source.split("\n")[line - 1].strip(),
                        ))
        for child in node.children:
            self._walk_js(child, source, filepath, results)

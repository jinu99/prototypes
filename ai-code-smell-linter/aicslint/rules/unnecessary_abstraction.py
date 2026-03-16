"""Rule: Unnecessary abstraction (single-implementation interface/abstract class).

AI models love creating abstract base classes or interfaces with only one
concrete implementation — premature abstraction that adds complexity without
value. No traditional linter catches this structural smell.
"""

from .base import BaseRule, SmellResult


class UnnecessaryAbstractionRule(BaseRule):
    rule_id = "ACS005"
    rule_name = "unnecessary-abstraction"
    severity = "info"
    description = "Abstract class/interface with likely single implementation in same file"
    languages = ["python", "javascript", "typescript"]

    def check(self, tree, source: str, lang: str, filepath: str) -> list[SmellResult]:
        results = []
        if lang == "python":
            self._check_python(tree.root_node, source, filepath, results)
        elif lang in ("javascript", "typescript"):
            self._check_ts(tree.root_node, source, filepath, results)
        return results

    def _check_python(self, root, source, filepath, results):
        """Find ABC subclasses with only one concrete subclass in the same file."""
        classes = []
        self._collect_classes_python(root, classes)

        # Find abstract classes (inherit from ABC or have abstractmethod)
        abstract_classes = {}
        concrete_classes = []

        for cls_node, name, bases in classes:
            is_abstract = False
            for base in bases:
                if base in ("ABC", "ABCMeta"):
                    is_abstract = True
            # Check for @abstractmethod decorators
            if not is_abstract:
                src_text = cls_node.text.decode()
                if "@abstractmethod" in src_text:
                    is_abstract = True
            if is_abstract:
                abstract_classes[name] = cls_node
            else:
                concrete_classes.append((name, bases))

        # Check if any abstract class has exactly one implementation
        for abs_name, abs_node in abstract_classes.items():
            implementations = [
                c_name for c_name, c_bases in concrete_classes
                if abs_name in c_bases
            ]
            if len(implementations) == 1:
                line = abs_node.start_point[0] + 1
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=f"Abstract class '{abs_name}' has only one implementation '{implementations[0]}' in this file",
                    file=filepath,
                    line=line,
                    snippet=source.split("\n")[line - 1].strip(),
                ))

    def _collect_classes_python(self, node, classes):
        if node.type == "class_definition":
            name = ""
            bases = []
            for child in node.children:
                if child.type == "identifier":
                    name = child.text.decode()
                if child.type == "argument_list":
                    for arg in child.children:
                        if arg.type == "identifier":
                            bases.append(arg.text.decode())
            classes.append((node, name, bases))
        for child in node.children:
            self._collect_classes_python(child, classes)

    def _check_ts(self, root, source, filepath, results):
        """Find interfaces/abstract classes with single implementation in same file."""
        interfaces = {}
        implementations = []
        self._collect_ts_types(root, interfaces, implementations)

        for iface_name, iface_node in interfaces.items():
            impls = [
                c_name for c_name, c_bases in implementations
                if iface_name in c_bases
            ]
            if len(impls) == 1:
                line = iface_node.start_point[0] + 1
                results.append(SmellResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=self.severity,
                    message=f"Interface '{iface_name}' has only one implementation '{impls[0]}' in this file",
                    file=filepath,
                    line=line,
                    snippet=source.split("\n")[line - 1].strip(),
                ))

    def _collect_ts_types(self, node, interfaces, implementations):
        if node.type == "interface_declaration":
            name = ""
            for child in node.children:
                if child.type == "type_identifier":
                    name = child.text.decode()
            if name:
                interfaces[name] = node

        if node.type == "class_declaration":
            name = ""
            bases = []
            for child in node.children:
                if child.type == "type_identifier":
                    name = child.text.decode()
                if child.type == "class_heritage":
                    for c in child.children:
                        if c.type == "type_identifier":
                            bases.append(c.text.decode())
                        # Dig into implements_clause
                        for cc in c.children:
                            if cc.type == "type_identifier":
                                bases.append(cc.text.decode())
            if name:
                implementations.append((name, bases))

        for child in node.children:
            self._collect_ts_types(child, interfaces, implementations)

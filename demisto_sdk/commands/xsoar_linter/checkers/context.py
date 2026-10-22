"""Per-file state shared by all checkers: the parsed tree, settings, suppressions and findings."""

import ast
from typing import Any, Dict, List, Optional, Sequence

from demisto_sdk.commands.xsoar_linter.checkers.models import Finding, LintSettings, Rule
from demisto_sdk.commands.xsoar_linter.checkers.pragmas import Suppressions

PARSE_ERROR_CODE = "E0001"
NAMED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


class FileContext:
    """Everything a checker needs to inspect one file and report findings."""

    def __init__(
        self,
        tree: ast.Module,
        settings: LintSettings,
        rules: Dict[str, Rule],
        suppressions: Suppressions,
    ):
        self.tree = tree
        self.settings = settings
        self.rules = rules
        self.suppressions = suppressions
        self.findings: List[Finding] = []
        self.parents: Dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                self.parents[child] = parent

    def parent(self, node: ast.AST) -> Optional[ast.AST]:
        return self.parents.get(node)

    def scope_name(self, node: ast.AST) -> str:
        """
        Dotted name of the function/class that contains the node, e.g. `Client.__init__`.
        A function or class node is named after itself. Top-level code gives ''.
        """
        names = []
        current: Optional[ast.AST] = node
        while current is not None:
            if isinstance(current, NAMED_SCOPES):
                names.append(current.name)
            elif isinstance(current, ast.Lambda):
                names.append("<lambda>")
            current = self.parents.get(current)
        return ".".join(reversed(names))

    def report(
        self, code: str, node: Optional[ast.AST] = None, args: Optional[Sequence[Any]] = None
    ) -> None:
        """
        Report a finding for an enabled rule, unless a disable comment turns it off.
        Findings without a node are reported for the whole module, at line 1 column 0.
        """
        rule = self.rules.get(code)
        if not rule:
            return
        if node is None:
            line, col, obj = 1, 0, ""
        else:
            line, col, obj = node.lineno, node.col_offset, self.scope_name(node)  # type: ignore[attr-defined]
        if self.suppressions.is_disabled(code, line):
            return
        message = rule.message % tuple(args) if args else rule.message
        self.findings.append(Finding(line, col, code, obj, message))


def parse_error_finding(error: SyntaxError, module_name: str) -> Finding:
    """The finding reported when a file cannot be parsed."""
    line = error.lineno or 1
    col = error.offset or 0
    return Finding(
        line=line,
        col=col,
        code=PARSE_ERROR_CODE,
        obj="",
        message=f"Parsing failed: '{error.msg} ({module_name}, line {line})'",
    )

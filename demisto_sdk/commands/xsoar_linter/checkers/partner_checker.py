"""Rules for partner support level and above."""

import ast
from typing import ClassVar, List

from demisto_sdk.commands.xsoar_linter.checkers.base_checker import call_name
from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.context import FileContext
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule

MAIN_FUNCTION = "main"
RETURN_ERROR = "return_error"
TRY_STATEMENTS = tuple(
    getattr(ast, name) for name in ("Try", "TryStar") if hasattr(ast, name)
)


def is_return_error_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and call_name(node) == RETURN_ERROR


class PartnerChecker(Checker):
    RULES: ClassVar[List[Rule]] = [
        Rule(
            "W9010",
            "try-except-main-doesnt-exists",
            "try and except statements were not found in main function. Please add them",
        ),
        Rule(
            "W9011",
            "too-many-return-error",
            "return_error used too many times, should be used only once in the code, in main function. "
            "Please remove other usages.",
        ),
        Rule(
            "W9012",
            "return-error-does-not-exist-in-main",
            "return_error should be used in main function. Please add it.",
        ),
    ]

    def __init__(self, context: FileContext):
        super().__init__(context)
        self.return_error_count = 0

    def visit_Call(self, node: ast.Call) -> None:
        if call_name(node) == RETURN_ERROR:
            self.return_error_count += 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Checks every function named main, including methods. `async def main` is not checked."""
        if node.name != MAIN_FUNCTION:
            return
        # Only statements directly in the body count, a try nested in an if does not.
        if not any(isinstance(statement, TRY_STATEMENTS) for statement in node.body):
            self.report("W9010", node)
        if not any(is_return_error_call(sub_node) for sub_node in ast.walk(node)):
            self.report("W9012", node)

    def leave_module(self) -> None:
        if self.return_error_count > 1:
            self.report("W9011")

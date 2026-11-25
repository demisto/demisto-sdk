"""Rules for certified partner support level and above."""

import ast
from typing import ClassVar, List, Set

from demisto_sdk.commands.xsoar_linter.checkers.base_checker import (
    call_name,
    is_attribute_call,
)
from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.context import FileContext
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule

MAIN_FUNCTION = "main"
FUNCTION_DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


class CertifiedPartnerChecker(Checker):
    RULES: ClassVar[List[Rule]] = [
        Rule(
            "E9001",
            "sys-exit-exists",
            "Sys.exit use is found, Please use return instead.",
        ),
        Rule(
            "W9005",
            "main-func-doesnt-exist",
            "Main function wasnt found in the file, Please add main()",
        ),
        Rule(
            "W9008",
            "demisto-results-exists",
            "Do not use demisto.results function. Please return CommandResults object instead.",
        ),
        Rule(
            "W9009",
            "return-outputs-exists",
            "Do not use return_outputs function. Please return CommandResults object instead.",
        ),
        Rule(
            "W9016",
            "init-params-outside-main",
            "Initialize of params was found outside of main function. Please use demisto.params() only inside main func",
        ),
        Rule(
            "W9017",
            "init-args-outside-main",
            "Initialize of args was found outside of main function. Please use demisto.args() only inside main func",
        ),
    ]

    def __init__(self, context: FileContext):
        super().__init__(context)
        self.function_names: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # `async def main` does not count as a main function.
        self.function_names.add(node.name)

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_sys_exit_with_error(node):
            self.report("E9001", node)
        if is_attribute_call(node, "demisto", "results"):
            self.report("W9008", node)
        if call_name(node) == "return_outputs":
            self.report("W9009", node)
        if is_attribute_call(node, "demisto", "params") and not self._inside_main(node):
            self.report("W9016", node)
        if is_attribute_call(node, "demisto", "args") and not self._inside_main(node):
            self.report("W9017", node)

    @staticmethod
    def _is_sys_exit_with_error(node: ast.Call) -> bool:
        """`sys.exit(x)` where x is a literal other than 0 (or False). A variable argument is not checked."""
        if not (is_attribute_call(node, "sys", "exit") and node.args):
            return False
        exit_code = node.args[0]
        return isinstance(exit_code, ast.Constant) and exit_code.value != 0

    def _inside_main(self, node: ast.AST) -> bool:
        """True when any enclosing function (sync or async, at any depth) is named main."""
        parent = self.context.parent(node)
        while parent is not None:
            if (
                isinstance(parent, FUNCTION_DEFINITIONS)
                and parent.name == MAIN_FUNCTION
            ):
                return True
            parent = self.context.parent(parent)
        return False

    def leave_module(self) -> None:
        if MAIN_FUNCTION not in self.function_names:
            self.report("W9005")

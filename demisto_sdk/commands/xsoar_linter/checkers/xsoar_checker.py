"""Rules for xsoar support level."""

import ast
from typing import ClassVar, Iterator, List, Optional

from demisto_sdk.commands.xsoar_linter.checkers.base_checker import (
    is_attribute_call,
)
from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule

MAIN_FUNCTION = "main"
NOT_IMPLEMENTED_ERROR = "NotImplementedError"
ANNOTATION_EXEMPT_FUNCTIONS = {"main", "__init__"}
ARGS_PARAMS_NAMES = {
    "args",
    "dargs",
    "arguments",
    "d_args",
    "data_args",
    "params",
    "PARAMS",
    "integration_parameters",
}


class UnclearRaise(Exception):
    """A raise statement whose exception is not a plain `Name(...)` call, e.g. a bare `raise`."""


def raises_not_implemented(statement: ast.AST) -> bool:
    """
    True for `raise NotImplementedError(...)`.
    Raises UnclearRaise for a raise that is not a plain function call (bare `raise`, `raise error`,
    `raise module.Error()`): the main-function check gives up and reports nothing in that case.
    """
    if not isinstance(statement, ast.Raise):
        return False
    exception = statement.exc
    if not (isinstance(exception, ast.Call) and isinstance(exception.func, ast.Name)):
        raise UnclearRaise()
    return exception.func.id == NOT_IMPLEMENTED_ERROR


def preorder(node: ast.AST) -> Iterator[ast.AST]:
    """All nodes under `node` (not including it), parents before children, in source order."""
    for child in ast.iter_child_nodes(node):
        yield child
        yield from preorder(child)


def main_raises_not_implemented(main: ast.FunctionDef) -> Optional[bool]:
    """
    Whether main raises NotImplementedError(...). An if statement's direct raises are checked
    when the if is reached. Returns None when an unclear raise is reached first.
    """
    try:
        for node in preorder(main):
            if raises_not_implemented(node):
                return True
            if isinstance(node, ast.If) and any(
                raises_not_implemented(statement)
                for statement in node.body + node.orelse
            ):
                return True
    except UnclearRaise:
        return None
    return False


class XsoarChecker(Checker):
    """Rules for xsoar support level."""

    RULES: ClassVar[List[Rule]] = [
        Rule(
            "W9014",
            "missing-arg-type-annoation",
            "Function arguments are missing type annotations. Please add type annotations",
        ),
        Rule(
            "W9018",
            "not-implemented-error-doesnt-exist",
            "It is best practice for Integrations to raise a NotImplementedError when receiving a command which is "
            "not recognized. exception",
        ),
        Rule(
            "W9019",
            "direct-access-args-params-dict-exist",
            "It is best practice to use .get when accessing the arg/params dict object rather then direct access.",
        ),
    ]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """`async def` functions are not checked."""
        if self._missing_annotations(node):
            self.report("W9014", node)
        if node.name == MAIN_FUNCTION and not self.settings.is_script:
            # Scripts do not have to raise NotImplementedError in main.
            if main_raises_not_implemented(node) is False:
                self.report("W9018", node)

    def _missing_annotations(self, node: ast.FunctionDef) -> bool:
        """
        A regular positional argument (not `self`) without a type annotation.
        Positional-only, keyword-only, *args and **kwargs are not checked. Skipped for Python 2.
        """
        if self.settings.py2 or node.name in ANNOTATION_EXEMPT_FUNCTIONS:
            return False
        return any(
            argument.annotation is None and argument.arg != "self"
            for argument in node.args.args
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        """`x = demisto.args()["key"]` or `x = args["key"]`: direct access on the value side of an assignment."""
        if isinstance(node.value, ast.Subscript) and self._is_args_params_dict(
            node.value.value
        ):
            self.report("W9019", node.value)

    @staticmethod
    def _is_args_params_dict(node: ast.expr) -> bool:
        if isinstance(node, ast.Call):
            return is_attribute_call(node, "demisto", "args") or is_attribute_call(
                node, "demisto", "params"
            )
        return isinstance(node, ast.Name) and node.id in ARGS_PARAMS_NAMES

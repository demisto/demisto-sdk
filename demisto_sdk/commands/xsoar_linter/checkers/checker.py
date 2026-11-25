"""Base class for the xsoar-linter tier checkers."""

import ast
from typing import Callable, ClassVar, Dict, List

from demisto_sdk.commands.xsoar_linter.checkers.context import FileContext
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule


class Checker:
    """
    A group of rules that run together (one support tier).

    Subclasses declare their rules in `RULES` and implement any of:
        visit_<NodeType>(self, node)  e.g. visit_Call, visit_FunctionDef, visit_If
        leave_module(self)            runs once after the whole file was visited
    Findings are reported with `self.report(code, node, args)`.
    """

    RULES: ClassVar[List[Rule]] = []

    def __init__(self, context: FileContext):
        self.context = context
        self.settings = context.settings

    def report(self, code: str, node: ast.AST = None, args=None) -> None:  # type: ignore[assignment]
        self.context.report(code, node, args)

    def leave_module(self) -> None:
        """Called once after every node in the file was visited."""

    def handlers(self) -> Dict[str, Callable[[ast.AST], None]]:
        return {
            name[len("visit_") :]: getattr(self, name)
            for name in dir(self)
            if name.startswith("visit_")
        }


def run_checkers(context: FileContext, checkers: List[Checker]) -> None:
    """Visit every node of the file once and dispatch it to the checkers that handle it."""
    dispatch: Dict[str, List[Callable[[ast.AST], None]]] = {}
    for checker in checkers:
        for node_type, handler in checker.handlers().items():
            dispatch.setdefault(node_type, []).append(handler)
    if dispatch:
        for node in ast.walk(context.tree):
            for handler in dispatch.get(type(node).__name__, ()):
                handler(node)
    for checker in checkers:
        checker.leave_module()

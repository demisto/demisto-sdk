"""Rules that run for every support level."""

import ast
from typing import Any, ClassVar, List, Optional, Set

from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.context import FileContext
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule
from demisto_sdk.commands.xsoar_linter.checkers.name_resolver import (
    NameResolver,
    UnsupportedValue,
)

TEST_MODULE = "test-module"
MAX_SLEEP_SECONDS = 10
DOCSTRING_OWNERS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def call_name(node: ast.Call) -> Optional[str]:
    """The name of a plain function call, e.g. `print` for `print(x)`. None for `obj.method(x)`."""
    return node.func.id if isinstance(node.func, ast.Name) else None


def is_attribute_call(node: ast.Call, owner: str, attribute: str) -> bool:
    """True for a call like `owner.attribute(...)`, e.g. `demisto.log(...)`."""
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == attribute
        and isinstance(func.value, ast.Name)
        and func.value.id == owner
    )


def docstring_nodes(tree: ast.Module) -> Set[ast.AST]:
    """The string constants that are module, class or function docstrings."""
    docstrings: Set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, DOCSTRING_OWNERS) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(first.value)
    return docstrings


class BaseChecker(Checker):
    RULES: ClassVar[List[Rule]] = [
        Rule("E9002", "print-exists", "Print is found, Please remove all prints from the code."),
        Rule("E9003", "sleep-exists", "Sleep is found, Please remove all sleep statements from the code."),
        Rule("E9004", "exit-exists", "exit is found, Please remove all exit() statements from the code."),
        Rule("E9005", "quit-exists", "quit is found, Please remove all quit() statements from the code."),
        Rule(
            "E9006",
            "invalid-import-common-server-python",
            "Invalid CommonServerPython import was found. Please change the import to: from CommonServerPython import *",
        ),
        Rule(
            "E9007",
            "commandresults-indicators-exists",
            "Invalid usage of indicators key in CommandResults was found, Please use indicator key instead.",
        ),
        Rule(
            "E9010",
            "unimplemented-commands-exist",
            "Some commands from yml file are not implemented in the python file, Please make sure that every command "
            "is implemented in your code. The commands that are not implemented are %s",
        ),
        Rule(
            "E9011",
            "unimplemented-test-module",
            "test-module command is not implemented in the python file, it is essential for every integration. "
            "Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ),
        Rule(
            "E9012",
            "demisto-log-exists",
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
        ),
        Rule(
            "W9013",
            "http-usage",
            "Hardcoded http URL was found in the code, using https (when possible) is recommended.",
        ),
    ]

    def __init__(self, context: FileContext):
        super().__init__(context)
        self.commands: List[Any] = list(self.settings.commands)
        self.test_module_implemented = self.settings.is_script
        self.resolver = NameResolver(context)
        self.docstrings = docstring_nodes(context.tree)

    # ---------------------------------------- calls ----------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node)
        if name == "print":
            self.report("E9002", node)
        elif name == "exit":
            self.report("E9004", node)
        elif name == "quit":
            self.report("E9005", node)
        elif name == "CommandResults" and any(keyword.arg == "indicators" for keyword in node.keywords):
            self.report("E9007", node)
        if self._is_long_sleep(node):
            self.report("E9003", node)
        if is_attribute_call(node, "demisto", "log"):
            self.report("E9012", node)

    def _is_long_sleep(self, node: ast.Call) -> bool:
        """
        `time.sleep(x)` or `sleep(x)` where x is a number above 10 or a variable.
        Long-running integrations are allowed to sleep.
        """
        if self.settings.long_running:
            return False
        if not (is_attribute_call(node, "time", "sleep") or call_name(node) == "sleep"):
            return False
        if not node.args:
            return False
        seconds = node.args[0]
        if isinstance(seconds, ast.Name):
            return True
        if not isinstance(seconds, ast.Constant):
            return False
        try:
            return int(seconds.value) > MAX_SLEEP_SECONDS
        except (TypeError, ValueError):
            return False

    # ---------------------------------------- strings ----------------------------------------

    def visit_Constant(self, node: ast.Constant) -> None:
        if not (isinstance(node.value, str) and node.value.startswith("http:")):
            return
        if node in self.docstrings:
            return
        parent = self.context.parent(node)
        # A string part of an f-string is reported at the position of the whole f-string.
        self.report("W9013", parent if isinstance(parent, ast.JoinedStr) else node)

    # ---------------------------------------- imports ----------------------------------------

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module == "CommonServerPython" and node.names[0].name != "*":
            self.report("E9006", node)
        if "ApiModule" in module:
            # The commands are implemented in the API module code.
            self.commands = []
            self.test_module_implemented = True

    # ---------------------------------------- commands ----------------------------------------

    def visit_Dict(self, node: ast.Dict) -> None:
        """Command names used as dict keys, e.g. {"my-command": my_command}."""
        try:
            for key in node.keys:
                if key is not None:
                    self._mark_implemented(self._possible_values(key))
        except UnsupportedValue:
            pass

    def visit_If(self, node: ast.If) -> None:
        """
        Command names compared in an if statement: `command == "x"`, `command in ["x", "y"]`,
        and `command == "x" or command == "y"`. Only the value on the right side is read.
        """
        try:
            if isinstance(node.test, ast.BoolOp):
                for value in node.test.values:
                    if not isinstance(value, ast.Compare):
                        return
                    self._check_compared_value(value.comparators[0])
            elif isinstance(node.test, ast.Compare):
                self._check_compared_value(node.test.comparators[0])
        except UnsupportedValue:
            pass

    def _check_compared_value(self, compared: ast.expr) -> None:
        self._mark_implemented(self._possible_values(compared))
        if isinstance(compared, (ast.List, ast.Set, ast.Tuple)):
            for element in compared.elts:
                self._mark_implemented(self._possible_values(element))

    def _possible_values(self, node: ast.expr) -> List[Any]:
        """The values a string, f-string or variable can have. Raises UnsupportedValue when unclear."""
        if isinstance(node, ast.Constant):
            return [node.value]
        if isinstance(node, ast.Name):
            return self.resolver.resolve(node) or []
        if isinstance(node, ast.JoinedStr):
            parts: List[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    resolved = self._formatted_value(value.value)
                    if resolved is None:
                        raise UnsupportedValue()
                    parts.extend(resolved)
            return ["".join(parts)]
        return []

    def _formatted_value(self, node: ast.expr) -> Optional[List[str]]:
        if not isinstance(node, ast.Name):
            return None
        values = self.resolver.resolve(node)
        if values is None or not all(isinstance(value, str) for value in values):
            return None
        return values

    def _mark_implemented(self, values: List[Any]) -> None:
        for value in values:
            if value in self.commands:
                self.commands.remove(value)
            if value == TEST_MODULE:
                self.test_module_implemented = True

    def leave_module(self) -> None:
        if self.commands:
            self.report("E9010", args=[str(self.commands)])
        if not self.test_module_implemented:
            self.report("E9011")

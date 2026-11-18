"""Resolve names (e.g. `FETCH_COMMAND`) to the constant values assigned to them in the same file."""

import ast
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from demisto_sdk.commands.xsoar_linter.checkers.context import FileContext

FUNCTION_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
SCOPES = FUNCTION_SCOPES + COMPREHENSIONS + (ast.ClassDef, ast.Module)
CONTAINER_LITERALS = (ast.Tuple, ast.List, ast.Set, ast.Dict, ast.Lambda)
MAX_DEPTH = 10

VALUE = "value"  # bound to an expression we can try to evaluate
UNKNOWN = "unknown"  # bound to something we cannot evaluate (argument, loop variable, import...)
UNSUPPORTED = (
    "unsupported"  # bound to something that is not a single value (function, class)
)


class UnsupportedValue(Exception):
    """The name points at something that is not a single value, such as a tuple, list, dict or function."""


class Binding(NamedTuple):
    end: Tuple[int, int]
    kind: str
    value: Optional[ast.expr] = None


class NameResolver:
    """
    Finds the value of a name the way a reader would: the last assignment before the use in the same
    function, or else the last assignment in an enclosing function or in the module.
    """

    def __init__(self, context: FileContext):
        self.context = context
        self._bindings: Dict[ast.AST, Dict[str, List[Binding]]] = {}

    def resolve(self, name: ast.Name, depth: int = 0) -> Optional[List[Any]]:
        """
        Returns the possible values of the name: [] when the name is never assigned in the file,
        None when it is assigned but the value cannot be evaluated.
        Raises UnsupportedValue when the name points at a tuple, list, dict, function or class.
        """
        use_position = (name.lineno, name.col_offset)
        for index, scope in enumerate(self._scope_chain(name)):
            if index and isinstance(scope, ast.ClassDef):
                continue  # class attributes are not visible inside methods
            bindings = self._scope_bindings(scope).get(name.id)
            if not bindings:
                continue
            if index == 0:
                bindings = [
                    binding for binding in bindings if binding.end <= use_position
                ]
                if not bindings:
                    return []
            return self._binding_values(bindings[-1], depth)
        return []

    def evaluate(self, node: ast.expr, depth: int = 0) -> Optional[List[Any]]:
        if depth > MAX_DEPTH:
            return None
        if isinstance(node, ast.Constant):
            return [node.value]
        if isinstance(node, CONTAINER_LITERALS):
            raise UnsupportedValue()
        if isinstance(node, ast.Name):
            return self.resolve(node, depth + 1)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self._concatenate(node, depth)
        return None

    def _concatenate(self, node: ast.BinOp, depth: int) -> Optional[List[Any]]:
        try:
            left = self.evaluate(node.left, depth + 1)
            right = self.evaluate(node.right, depth + 1)
        except UnsupportedValue:
            return None
        if left and right and len(left) == len(right) == 1:
            if isinstance(left[0], str) and isinstance(right[0], str):
                return [left[0] + right[0]]
        return None

    def _binding_values(self, binding: Binding, depth: int) -> Optional[List[Any]]:
        if binding.kind == UNSUPPORTED:
            raise UnsupportedValue()
        if binding.kind == UNKNOWN or binding.value is None:
            return None
        return self.evaluate(binding.value, depth)

    def _scope_chain(self, node: ast.AST) -> List[ast.AST]:
        chain: List[ast.AST] = []
        current = self.context.parent(node)
        while current is not None:
            if isinstance(current, SCOPES):
                chain.append(current)
            current = self.context.parent(current)
        return chain

    def _scope_bindings(self, scope: ast.AST) -> Dict[str, List[Binding]]:
        if scope not in self._bindings:
            self._bindings[scope] = collect_bindings(scope)
        return self._bindings[scope]


def collect_bindings(scope: ast.AST) -> Dict[str, List[Binding]]:
    """All names assigned directly in the scope (not in nested functions/classes), in source order."""
    bindings: Dict[str, List[Binding]] = {}

    def bind(
        name: str, node: ast.AST, kind: str, value: Optional[ast.expr] = None
    ) -> None:
        end = (
            getattr(node, "end_lineno", 0) or 0,
            getattr(node, "end_col_offset", 0) or 0,
        )
        bindings.setdefault(name, []).append(Binding(end, kind, value))

    def bind_target(target: ast.AST, statement: ast.AST) -> None:
        for sub_node in ast.walk(target):
            if isinstance(sub_node, ast.Name):
                bind(sub_node.id, statement, UNKNOWN)

    if isinstance(scope, FUNCTION_SCOPES):
        for argument in ast.walk(scope.args):
            if isinstance(argument, ast.arg):
                bind(argument.arg, scope.args, UNKNOWN)
    if isinstance(scope, COMPREHENSIONS):
        for generator in scope.generators:
            bind_target(generator.target, generator)
        return bindings

    body = scope.body if isinstance(scope.body, list) else [scope.body]  # type: ignore[attr-defined]
    stack: List[ast.AST] = list(reversed(body))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bind(node.name, node, UNSUPPORTED)
            continue
        if isinstance(node, (ast.Lambda,) + COMPREHENSIONS):
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bind(target.id, node, VALUE, node.value)
                else:
                    bind_target(target, node)
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and isinstance(node.target, ast.Name)
        ):
            bind(node.target.id, node, VALUE, node.value)
        elif isinstance(node, (ast.AugAssign, ast.For, ast.AsyncFor, ast.NamedExpr)):
            bind_target(node.target, node)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            bind_target(node.optional_vars, node.optional_vars)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bind(node.name, node, UNKNOWN)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bind((alias.asname or alias.name).split(".")[0], node, UNKNOWN)
        stack.extend(reversed(list(ast.iter_child_nodes(node))))
    return bindings

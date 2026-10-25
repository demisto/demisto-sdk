"""
Disable comments for xsoar-linter rules.

Two prefixes are accepted and behave the same:
    # xsoar-lint: disable=E9003
    # pylint: disable=E9003        (kept so existing content keeps working)

Supported keywords: disable, enable, disable-next, disable-msg, enable-msg, skip-file.
`disable=all` and `skip-file` ignore the whole file.
Rules can be named by code (E9003) or symbol (sleep-exists). Unknown names are ignored.

Where a comment applies:
    * `disable-next=X` applies to the next line only.
    * A comment at the end of a code line applies to that line only, unless the line
      opens a block (def, class, if, for, while, with, try, ...), in which case it
      applies to the whole block.
    * A comment on its own line applies from that line to the end of the block it is in
      (the end of the file at top level), or until a later comment changes it.
      When it comes before the first statement of a function or class, it also covers
      the def/class line.
"""

import ast
import io
import re
import tokenize
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

PRAGMA_PATTERN = re.compile(r"\b(?:xsoar-lint|pylint)\s*:\s*(?P<body>[^#\n]*)")
CLAUSE_PATTERN = re.compile(r"^\s*(?P<keyword>[a-z-]+)\s*(?:=\s*(?P<names>.*))?$")
DISABLE_KEYWORDS = {"disable", "disable-msg"}
ENABLE_KEYWORDS = {"enable", "enable-msg"}
NEXT_LINE_KEYWORDS = {"disable-next"}
SKIP_FILE_KEYWORDS = {"skip-file", "disable-all"}

# Block statements whose header line can carry a comment that covers the whole block.
DEFINITION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
STATEMENT_LIST_FIELDS = ("body", "orelse", "finalbody")


@dataclass(frozen=True)
class Pragma:
    line: int
    own_line: bool
    keyword: str
    codes: Tuple[str, ...]


@dataclass
class Suppressions:
    """Answers: is rule `code` turned off on line `line`?"""

    skip_file: bool = False
    # code -> list of (first line, last line, enabled), in the order they were applied.
    ranges: Dict[str, List[Tuple[int, int, bool]]] = field(default_factory=dict)

    def is_disabled(self, code: str, line: int) -> bool:
        if self.skip_file:
            return True
        for first, last, enabled in reversed(self.ranges.get(code, [])):
            if first <= line <= last:
                return not enabled
        return False

    def add_range(self, code: str, first: int, last: int, enabled: bool) -> None:
        self.ranges.setdefault(code, []).append((first, last, enabled))


def read_pragmas(source: str, known_names: Dict[str, str]) -> Tuple[List[Pragma], bool]:
    """
    Find all disable comments in the source.

    Args:
        source: the python source code.
        known_names: maps every rule code and symbol to its code.

    Returns:
        The pragmas in line order, and whether the whole file should be skipped.
    """
    pragmas: List[Pragma] = []
    skip_file = False
    lines = source.splitlines()
    for token in _comment_tokens(source):
        line_number, column = token.start
        own_line = not lines[line_number - 1][:column].strip()
        # A comment can hold several pragmas, e.g. `# pylint: disable=X  # xsoar-lint: disable=Y`.
        clauses = [
            clause
            for match in PRAGMA_PATTERN.finditer(token.string)
            for clause in match["body"].split(";")
        ]
        for clause in clauses:
            clause_match = CLAUSE_PATTERN.match(clause)
            if not clause_match:
                continue
            keyword = clause_match["keyword"]
            names = re.split(r"[,\s]+", clause_match["names"] or "")
            if keyword in SKIP_FILE_KEYWORDS or (
                keyword in DISABLE_KEYWORDS and "all" in names
            ):
                skip_file = True
                continue
            codes = tuple(known_names[name] for name in names if name in known_names)
            if codes:
                pragmas.append(Pragma(line_number, own_line, keyword, codes))
    return pragmas, skip_file


def build_suppressions(
    source: str, tree: Optional[ast.Module], known_names: Dict[str, str]
) -> Suppressions:
    pragmas, skip_file = read_pragmas(source, known_names)
    suppressions = Suppressions(skip_file=skip_file)
    if skip_file or not pragmas:
        return suppressions

    last_line = max(len(source.splitlines()), 1)
    blocks = BlockMap(tree, last_line) if tree else None
    for pragma in pragmas:
        first, last, enabled = _pragma_range(pragma, blocks, last_line)
        for code in pragma.codes:
            suppressions.add_range(code, first, last, enabled)
    return suppressions


def _pragma_range(
    pragma: Pragma, blocks: Optional["BlockMap"], last_line: int
) -> Tuple[int, int, bool]:
    if pragma.keyword in NEXT_LINE_KEYWORDS:
        return pragma.line + 1, pragma.line + 1, False
    enabled = pragma.keyword in ENABLE_KEYWORDS
    if not enabled and pragma.keyword not in DISABLE_KEYWORDS:
        return pragma.line, pragma.line, True  # unknown keyword: no effect
    if not blocks:
        return (
            (pragma.line, last_line, enabled)
            if pragma.own_line
            else (pragma.line, pragma.line, enabled)
        )
    if pragma.own_line:
        first, last = blocks.enclosing_block(pragma.line)
        return first, last, enabled
    return pragma.line, blocks.header_block_end(pragma.line), enabled


class BlockMap:
    """Line ranges of the blocks in a module, used to decide where a comment applies."""

    def __init__(self, tree: ast.Module, last_line: int):
        self.last_line = last_line
        # header line -> last line covered by a trailing comment on that header.
        self.header_ends: Dict[int, int] = {}
        # (first line, last line, definition line or 0) of every statement list.
        self.blocks: List[Tuple[int, int, int]] = []
        self._first_statement: Dict[int, int] = {}
        for node in ast.walk(tree):
            self._add_node(node)

    def _add_node(self, node: ast.AST) -> None:
        statement_lists = [
            getattr(node, name)
            for name in STATEMENT_LIST_FIELDS
            if isinstance(getattr(node, name, None), list) and getattr(node, name)
        ]
        statement_lists = [
            items for items in statement_lists if isinstance(items[0], ast.stmt)
        ]
        if not statement_lists or isinstance(node, ast.Module):
            return
        header_line = node.lineno
        body = statement_lists[0]
        if isinstance(node, DEFINITION_NODES):
            header_end = node.end_lineno or header_line
        else:
            header_end = body[-1].end_lineno or header_line
        self.header_ends[header_line] = max(
            self.header_ends.get(header_line, 0), header_end
        )

        definition_line = header_line if isinstance(node, DEFINITION_NODES) else 0
        self.blocks.append(
            (header_line + 1, body[-1].end_lineno or header_line, definition_line)
        )
        self._first_statement[header_line + 1] = body[0].lineno
        for items in statement_lists[1:]:
            self.blocks.append(
                (items[0].lineno - 1, items[-1].end_lineno or items[0].lineno, 0)
            )

    def header_block_end(self, line: int) -> int:
        return self.header_ends.get(line, line)

    def enclosing_block(self, line: int) -> Tuple[int, int]:
        """The range an own-line comment on `line` covers: from it to the end of its block."""
        best: Optional[Tuple[int, int, int]] = None
        for block in self.blocks:
            first, last, _ = block
            if first <= line <= last and (
                best is None or last - first < best[1] - best[0]
            ):
                best = block
        if best is None:
            return line, self.last_line
        first, last, definition_line = best
        if definition_line and line < self._first_statement.get(first, line + 1):
            return definition_line, last
        return line, last


def _comment_tokens(source: str) -> Iterable[tokenize.TokenInfo]:
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                yield token
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return

import ast
import textwrap
from pathlib import Path

import pytest

from demisto_sdk.commands.xsoar_linter.checkers.context import FileContext
from demisto_sdk.commands.xsoar_linter.checkers.models import LintSettings, Rule
from demisto_sdk.commands.xsoar_linter.checkers.pragmas import build_suppressions
from demisto_sdk.commands.xsoar_linter.checkers.runner import (
    format_finding,
    lint_source,
)

CHECKERS_DIR = Path(__file__).resolve().parent.parent / "checkers"
KNOWN_NAMES = {"E9003": "E9003", "sleep-exists": "E9003", "E9002": "E9002"}


def suppressions_for(source: str):
    source = textwrap.dedent(source)
    return build_suppressions(source, ast.parse(source), KNOWN_NAMES)


@pytest.mark.parametrize(
    "source, disabled_lines, enabled_lines",
    [
        pytest.param(
            """
            def helper():  # pylint: disable=E9003
                sleep(20)
                sleep(30)
            sleep(40)
            """,
            [2, 3, 4],
            [5],
            id="trailing comment on def covers the whole function",
        ),
        pytest.param(
            """
            def helper():
                sleep(20)
                # pylint: disable=E9003
                sleep(30)
                # pylint: enable=E9003
                sleep(40)
            sleep(50)
            """,
            [5],
            [3, 7, 8],
            id="own-line comment covers until enable",
        ),
        pytest.param(
            """
            def helper():
                sleep(20)
                # pylint: disable=E9003
                sleep(30)
            sleep(40)
            """,
            [5],
            [3, 6],
            id="own-line comment stops at the end of its block",
        ),
        pytest.param(
            """
            sleep(10)
            # pylint: disable-next=E9003
            sleep(20)
            sleep(30)
            """,
            [4],
            [2, 5],
            id="disable-next covers the next line only",
        ),
        pytest.param(
            """
            if True:  # pylint: disable=E9003
                sleep(20)
            sleep(30)
            """,
            [3],
            [4],
            id="trailing comment on if covers the if block",
        ),
        pytest.param(
            """
            values = [
                sleep(20),  # pylint: disable=E9003
                sleep(30),
            ]
            """,
            [3],
            [4],
            id="trailing comment inside a literal covers that line only",
        ),
        pytest.param(
            """
            sleep(10)
            # pylint: disable=E9003
            def helper():
                sleep(20)
            sleep(30)
            """,
            [5, 6],
            [2],
            id="top-level own-line comment covers the rest of the file",
        ),
        pytest.param(
            """
            sleep(10)  # xsoar-lint: disable=sleep-exists
            sleep(20)
            """,
            [2],
            [3],
            id="new xsoar-lint prefix and rule symbol",
        ),
        pytest.param(
            """
            sleep(10)  # some text # pylint: disable=E9003
            """,
            [2],
            [],
            id="comment after other comment text",
        ),
        pytest.param(
            """
            sleep(10)  # pylint: disable=e9003
            """,
            [],
            [2],
            id="codes are case sensitive",
        ),
    ],
)
def test_disable_comment_scope(source, disabled_lines, enabled_lines):
    """
    Given:
        - Python source with disable comments placed in different ways.
    When:
        - Building the suppressions for the file.
    Then:
        - Ensure E9003 is turned off exactly on the expected lines.
    """
    suppressions = suppressions_for(source)
    assert [
        line for line in disabled_lines if not suppressions.is_disabled("E9003", line)
    ] == []
    assert [
        line for line in enabled_lines if suppressions.is_disabled("E9003", line)
    ] == []


@pytest.mark.parametrize(
    "comment",
    ["# pylint: skip-file", "# pylint: disable=all", "# xsoar-lint: skip-file"],
)
def test_skip_file(comment):
    """
    Given:
        - A file with a skip-file or disable=all comment.
    When:
        - Building the suppressions for the file.
    Then:
        - Ensure every rule is turned off on every line.
    """
    suppressions = suppressions_for(f"{comment}\nsleep(20)\n")
    assert suppressions.is_disabled("E9003", 2)
    assert suppressions.is_disabled("E9002", 2)


def test_module_level_finding_needs_comment_on_line_1():
    """
    Given:
        - A disable comment on its own line after the module docstring.
    When:
        - Checking a module-level finding, which is reported at line 1.
    Then:
        - Ensure it is not suppressed, while a comment on line 1 does suppress it.
    """
    later = suppressions_for('"""doc"""\n# pylint: disable=E9003\nx = 1\n')
    first_line = suppressions_for('# pylint: disable=E9003\n"""doc"""\nx = 1\n')
    assert not later.is_disabled("E9003", 1)
    assert first_line.is_disabled("E9003", 1)


def test_scope_name_and_position():
    """
    Given:
        - Nodes at top level, inside a method, and a decorated function.
    When:
        - Reporting findings for them.
    Then:
        - Ensure positions and object names match the pylint output format.
    """
    source = textwrap.dedent(
        """
        class Client:
            def __init__(self):
                sleep(20)

        @decorator
        def helper():
            pass

        sleep(30)
        """
    )
    tree = ast.parse(source)
    rule = Rule("E9003", "sleep-exists", "Sleep is found")
    context = FileContext(
        tree,
        LintSettings(),
        {"E9003": rule},
        build_suppressions(source, tree, KNOWN_NAMES),
    )
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "sleep"
    ]
    helper = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "helper"
    )
    for node in calls + [helper]:
        context.report("E9003", node)
    context.report("E9003")

    found = sorted((f.line, f.col, f.obj) for f in context.findings)
    assert found == [
        (1, 0, ""),
        (4, 8, "Client.__init__"),
        (7, 0, "helper"),
        (10, 0, ""),
    ]


def test_parse_error_reports_e0001():
    """
    Given:
        - Python 2 only syntax.
    When:
        - Linting the source.
    Then:
        - Ensure a single failing E0001 finding is reported, like pylint.
    """
    result = lint_source(
        'def main():\n    print "x"\n', "sample", LintSettings(support="xsoar")
    )
    assert result.fails
    assert [(f.line, f.col, f.code) for f in result.findings] == [(2, 5, "E0001")]
    assert result.findings[0].message.startswith("Parsing failed: 'Missing parentheses")
    assert result.findings[0].message.endswith("(sample, line 2)'")


def test_unknown_support_level_fails_without_findings():
    """
    Given:
        - An unknown support level.
    When:
        - Linting a file.
    Then:
        - Ensure no rules run and the run fails, like the pylint engine.
    """
    result = lint_source("x = 1\n", "sample", LintSettings(support="unknown-level"))
    assert result.fails
    assert result.findings == []


def test_format_finding_matches_hook_pattern(tmp_path):
    """
    Given:
        - A finding.
    When:
        - Formatting it as an output line.
    Then:
        - Ensure the hook's error/warning regex can parse it.
    """
    from demisto_sdk.commands.xsoar_linter.checkers.models import Finding
    from demisto_sdk.commands.xsoar_linter.xsoar_linter import (
        ERROR_AND_WARNING_CODE_PATTERN,
    )

    line = format_finding(
        tmp_path / "a.py", Finding(3, 4, "E9003", "helper", "Sleep is found")
    )
    match = ERROR_AND_WARNING_CODE_PATTERN.match(line)
    assert match
    assert (match["line"], match["col"], match["error_code"]) == ("3", "4", "E9003")


def test_checkers_do_not_import_pylint_or_astroid():
    """
    Given:
        - The ast-based checkers package.
    When:
        - Scanning every module for imports.
    Then:
        - Ensure nothing imports pylint, astroid or the pylint plugins, so the package
          keeps working unchanged once pylint is removed.
    """
    forbidden = (
        "pylint",
        "astroid",
        "demisto_sdk.commands.pre_commit.resources.pylint_plugins",
    )
    offenders = []
    for module_path in CHECKERS_DIR.glob("*.py"):
        for node in ast.walk(ast.parse(module_path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            offenders += [
                f"{module_path.name}: {name}"
                for name in names
                if any(
                    name == prefix or name.startswith(f"{prefix}.")
                    for prefix in forbidden
                )
            ]
    assert offenders == []

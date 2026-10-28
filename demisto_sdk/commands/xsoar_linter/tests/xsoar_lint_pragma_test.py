"""
End-to-end tests for the `# xsoar-lint:` disable comment, which only the ast engine reads.

pylint ignores this prefix, so these cases cannot be recorded into golden.json.
The expected findings are written by hand.
"""

import textwrap
from typing import List, Tuple

import pytest

from demisto_sdk.commands.xsoar_linter.checkers.models import LintSettings
from demisto_sdk.commands.xsoar_linter.checkers.runner import lint_source

SCRIPT_SETTINGS = LintSettings(support="base", is_script=True)


def findings_for(source: str) -> List[Tuple[int, str]]:
    result = lint_source(textwrap.dedent(source), "sample", SCRIPT_SETTINGS)
    return [(finding.line, finding.code) for finding in result.findings]


@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param(
            """
            print("a")  # xsoar-lint: disable=E9002
            print("b")
            """,
            [(3, "E9002")],
            id="trailing comment covers its line only",
        ),
        pytest.param(
            """
            print("a")  # xsoar-lint: disable=print-exists
            print("b")
            """,
            [(3, "E9002")],
            id="rule symbol instead of code",
        ),
        pytest.param(
            """
            def helper():
                print("a")
                # xsoar-lint: disable=E9002
                print("b")
                print("c")
            print("d")
            """,
            [(3, "E9002"), (7, "E9002")],
            id="own-line comment in a function covers the rest of the function",
        ),
        pytest.param(
            """
            print("a")
            # xsoar-lint: disable=E9002
            def helper():
                print("b")
            print("c")
            """,
            [(2, "E9002")],
            id="own-line comment at top level covers the rest of the file",
        ),
        pytest.param(
            """
            # xsoar-lint: disable=E9002
            print("a")
            # xsoar-lint: enable=E9002
            print("b")
            """,
            [(5, "E9002")],
            id="enable after disable",
        ),
        pytest.param(
            """
            # xsoar-lint: disable-next=E9002
            print("a")
            print("b")
            """,
            [(4, "E9002")],
            id="disable-next covers the next line only",
        ),
        pytest.param(
            """
            print("a")  # xsoar-lint: disable=E9002,E9003
            sleep(20)  # xsoar-lint: disable=E9002
            """,
            [(3, "E9003")],
            id="only the listed rules are turned off",
        ),
        pytest.param(
            """
            print("a")  # pylint: disable=E9002
            sleep(20)  # xsoar-lint: disable=E9003
            print("b")
            sleep(30)
            """,
            [(4, "E9002"), (5, "E9003")],
            id="pylint and xsoar-lint prefixes in the same file",
        ),
        pytest.param(
            """
            print("a")  # pylint: disable=W0703  # xsoar-lint: disable=E9002
            """,
            [],
            id="xsoar-lint after a pylint comment on the same line",
        ),
    ],
)
def test_xsoar_lint_disable_comment(source: str, expected: List[Tuple[int, str]]):
    """
    Given:
        - A script with `# xsoar-lint:` disable comments placed in different ways.
    When:
        - Linting it with the ast engine.
    Then:
        - Ensure only the findings outside the comments' scope are reported.
    """
    assert findings_for(source) == expected


def test_xsoar_lint_skip_file():
    """
    Given:
        - A script with `# xsoar-lint: skip-file` and code that breaks error rules.
    When:
        - Linting it with the ast engine.
    Then:
        - Ensure nothing is reported and the run does not fail.
    """
    source = '# xsoar-lint: skip-file\nprint("a")\nsleep(20)\n'
    result = lint_source(source, "sample", SCRIPT_SETTINGS)
    assert result.findings == []
    assert not result.fails


def test_suppressed_error_does_not_fail_the_run():
    """
    Given:
        - A script whose only error finding is turned off with `# xsoar-lint:`.
    When:
        - Linting it with the ast engine.
    Then:
        - Ensure the run does not fail, while the same code without the comment fails.
    """
    suppressed = lint_source(
        'print("a")  # xsoar-lint: disable=E9002\n', "sample", SCRIPT_SETTINGS
    )
    not_suppressed = lint_source('print("a")\n', "sample", SCRIPT_SETTINGS)
    assert not suppressed.fails
    assert not_suppressed.fails

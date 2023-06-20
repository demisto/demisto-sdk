from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.pre_commit.linter_parser import (
    LinterViolation,
    ViolationType,
)

path = Path("dummy/foo.py")


DUMMY_VIOLATIONS = (
    LinterViolation(
        error_code="TEST001",
        path=path,
        row_start=0,
        message="dummy message",
        violation_type=ViolationType.ERROR,
        is_autofixable=False,
    ),
    LinterViolation(
        error_code="TEST002",
        path=path,
        row_start=1,
        message="dummy message",
        violation_type=ViolationType.ERROR,
        is_autofixable=True,
        fix_suggestion="dummy fix suggestion",
    ),
)


@pytest.mark.parametrize(
    "modified_lines,expected",
    [
        pytest.param((0,), (DUMMY_VIOLATIONS[0],), id="only one line changed"),
        pytest.param(
            (0, 1),
            (
                DUMMY_VIOLATIONS[0],
                DUMMY_VIOLATIONS[1],
            ),
            id="two lines, two violations",
        ),
        pytest.param((), (), id="no lines changed"),
        pytest.param((3,), (), id="lines without violations changed"),
    ],
)
def test_filter_violations(
    modified_lines: Tuple[int, ...], expected: List[LinterViolation]
):
    from demisto_sdk.commands.pre_commit.ruff_wrapper import filter_violations

    assert (
        filter_violations(
            violations=DUMMY_VIOLATIONS,
            git_modified_lines={path: modified_lines},
            fail_autofixable=False,  # TODO autofixable
        )
        == expected
    )

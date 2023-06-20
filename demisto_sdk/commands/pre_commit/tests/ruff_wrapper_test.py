from pathlib import Path
from typing import Tuple

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

@pytest.mark.parametrize("modified_lines,expected", [((0,), (DUMMY_VIOLATIONS[0],))])
def test_filter_violations(modified_lines:Tuple[int,...], expected: list[LinterViolation]):
    from demisto_sdk.commands.pre_commit.ruff_wrapper import filter_violations

    git_modified_files = {path: modified_lines}
    assert filter_violations(
        violations=DUMMY_VIOLATIONS,
        git_modified_lines=git_modified_files,
        fail_autofixable=True,
    ) == expected  # TODO autofixable 
from pathlib import Path

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.pre_commit.linter_parser import LinterViolation

json = JSON_Handler()


def test_ruff_parse():
    from demisto_sdk.commands.pre_commit.linter_parser import RuffParser

    with open(Path(__file__).parent / "ruff_output.json") as f:
        raw_data = json.load(f)
    assert len(raw_data) == 2

    violations = tuple(RuffParser.parse_single(_) for _ in raw_data)
    # assert violations == (LinterViolation(error_code='F401', path=PosixPath(''), row_start=2, message='`demisto_sdk.commands.pre_commit.linter_parser.LinterParser` imported but unused', violation_type=None, is_autofixable=True, fix_suggestion='Remove unused import: `demisto_sdk.commands.pre_commit.linter_parser.LinterParser`', row_end=2, col_start=63, col_end=75), LinterViolation(error_code='W293', path=PosixPath('demisto-sdk/demisto_sdk/commands/pre_commit/tests/linter_parser_test.py'), row_start=3, message='Blank line contains whitespace', violation_type=None, is_autofixable=True, fix_suggestion='Remove whitespace from blank line', row_end=3, col_start=1, col_end=5))
    assert violations == (
        LinterViolation(
            "F401",
        )
    )

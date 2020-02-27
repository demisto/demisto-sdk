import pytest
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.git_tools import git_path

VALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-valid.md'
INVALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid.md'
INVALID_MD_NODE = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid.md'

README_INPUTS = [
    (VALID_MD, True, None),
    (INVALID_MD, False, None),
]


@pytest.mark.parametrize("current, answer, NoNode", README_INPUTS)
def test_is_file_valid(current, answer, NoNode):
    readme_validator = ReadMeValidator(current)
    assert readme_validator.is_file_valid() is answer or readme_validator.is_file_valid() is NoNode

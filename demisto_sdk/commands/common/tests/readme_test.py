import pytest
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.git_tools import git_path

VALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-valid.md'
INVALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid.md'

README_INPUTS = [
    (VALID_MD, True),
    (INVALID_MD, False),
]


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid(current, answer):
    readme_validator = ReadMeValidator(current)
    ready = readme_validator.are_modules_installed_for_verify()
    if ready:
        assert readme_validator.is_valid_file() is answer

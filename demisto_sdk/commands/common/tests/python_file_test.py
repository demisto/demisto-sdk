import pytest

from demisto_sdk.commands.common.hook_validations.python_file import PythonFileValidator


@pytest.mark.parametrize(
    "file_input",
    [
        "# Copyright\n import pytest",
        "# BSD\n def test():\n pass",
        "# MIT\n import test",
        "# proprietary\n\ninput",
    ],
)
def test_copyright_sections(integration, file_input):
    """
    Given
        - Valid sections in different forms from SECTIONS
    When
        - Run validate on a python file
    Then
        - Ensure no empty sections from the SECTIONS list
    """

    integration.code.write(file_input)
    code_path = integration.code.path
    python_validator = PythonFileValidator(code_path)
    result = python_validator.is_valid_copyright()

    assert not result

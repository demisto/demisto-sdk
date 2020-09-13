from pathlib import Path

import pytest
from demisto_sdk.commands.lint import linter
from demisto_sdk.tests.constants_test import (GIT_ROOT,
                                              XSOAR_LINTER_PY2_INVALID,
                                              XSOAR_LINTER_PY2_VALID,
                                              XSOAR_LINTER_PY3_INVALID,
                                              XSOAR_LINTER_PY3_VALID)

files = [(Path(f"{XSOAR_LINTER_PY2_INVALID}"), 2.7, 1, ['Sys.exit use is found, Please use return instead.',
                                                        'Print is found, Please remove all prints from the code.']),
         (Path(f"{XSOAR_LINTER_PY2_VALID}"), 2.7, 0, []),
         (Path(f"{XSOAR_LINTER_PY3_VALID}"), 3.8, 0, []),
         (Path(f"{XSOAR_LINTER_PY3_INVALID}"), 3.8, 1, ['Sys.exit use is found, Please use return instead.',
                                                        'Print is found, Please remove all prints from the code.'])]


@pytest.mark.parametrize('file, python_version,exit_code,error_msgs', files)
def test_xsoar_linter(mocker, file, python_version, exit_code, error_msgs):
    """
    Given
    - file to run the linter on.
    - Python version of the file.
    - expected exit code of the xsoar linter function.
    - expected error messages of the xosar linter.

    When
    - Running xsoar linter using demisto lint.

    Then
    - Ensure valid files pass with the correct exit code.
    - Ensure valid files pass with no error messages.
    - Ensure invalid files fail with the correct exit code.
    - Ensure invalid files fail with the correct error messages.
    """

    mocker.patch.object(linter.Linter, '_docker_login')
    mocker.patch.object(linter.Linter, '_update_support_level')
    linter.Linter._docker_login.return_value = False
    test_path = Path(f"{GIT_ROOT}/demisto_sdk/tests/test_files")

    runner = linter.Linter(content_repo=test_path,
                           pack_dir=test_path,
                           req_2=[],
                           req_3=[],
                           docker_engine=True)
    exit_code_actual, output = runner._run_xsoar_linter(python_version, [file])
    assert exit_code == exit_code_actual
    for msg in error_msgs:
        assert msg in output

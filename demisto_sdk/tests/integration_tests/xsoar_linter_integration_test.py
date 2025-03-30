# ------------------------------------------------------ UT file list--------------------------------------------------
"""
Please use the existing test files and add the invalid usage to them.
For Error messages use: XSOAR_LINTER_PY3_INVALID
For Waring messages use: XSOAR_LINTER_PY3_INVALID_WARNINGS
For Waring messages which are relevant from partner and bigger use: XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER
For Valid file use: XSOAR_LINTER_PY3_VALID

For a new checker, add the invalid statement in the relevant file and add it to the relevant test.
"""

import pytest
from wcmatch.pathlib import Path


from demisto_sdk.tests.constants_test import (
    GIT_ROOT,
    XSOAR_LINTER_PY3_INVALID,
    XSOAR_LINTER_PY3_INVALID_WARNINGS,
    XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER,
    XSOAR_LINTER_PY3_NO_DEMISTO_RESULTS_WARNINGS,
    XSOAR_LINTER_PY3_VALID,
)

files = [
    # ---------------------------------------- For Valid file -------------------------------------------------
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_VALID}"),
        "3.8",
        "base",
        False,
        0,
        [],
        [],
        id="valid empty",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_VALID}"),
        "3.8",
        "base",
        True,
        0,
        [],
        [
            "test-module",
            "kace-machines-list",
            "kace-assets-list",
            "kace-queues-list",
            "kace-tickets-list",
        ],
        id="valid",
    ),
    # -------------------------------------------- For Invalid file -------------------------------------------------
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "base",
        True,
        1,
        [
            "Print is found, Please remove all prints from the code.",
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [],
        id="invalid,support=base,longrunning=True",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "base",
        False,
        1,
        [
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "Sleep is found, Please remove all sleep statements from the code.",
            "Invalid CommonServerPython import was found. Please change the import to: from CommonServerPython import *",
            "Invalid usage of indicators key in CommandResults was found, Please use indicator key instead.",
            "Some commands from yml file are not implemented in the python file, Please make sure that every command is"
            " implemented in your code. The commands that are not implemented are ['error']",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [
            "kace-machines-list",
            "kace-assets-list",
            "kace-queues-list",
            "kace-tickets-list",
            "error",
        ],
        id="invalid,support=base,longrunning=False",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "certified partner",
        False,
        1,
        [
            "Sys.exit use is found, Please use return instead.",
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "Sleep is found, Please remove all sleep statements from the code.",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [],
        id="invalid,support=certified partner,longrunning=False",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "certified partner",
        True,
        1,
        [
            "Sys.exit use is found, Please use return instead.",
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [],
        id="invalid,support=certified partner,longrunning=True",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "community",
        False,
        1,
        [
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [],
        id="invalid,support=community,longrunning=False",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "",
        False,
        1,
        [
            "exit is found, Please remove all exit()",
            "quit is found, Please remove all quit()",
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [],
        id="invalid,support=partner,longrunning=False",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID}"),
        "3.8",
        "xsoar",
        False,
        1,
        [
            "exit is found, Please remove all exit()",
            "quit is found, Please remove all quit()",
            "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
            "test-module command is not implemented in the python file, it is essential for every"
            " integration. Please add it to your code. For more information see: "
            "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        ],
        [],
        id="invalid,support=xsoar,longrunning=False",
    ),
    # -------------------------------- For Warning file which is relevant from partner level and bigger---------------
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER}"),
        "3.8",
        "partner",
        False,
        4,
        [
            "try and except statements were not found in main function.",
            "return_error should be used in main function. Please add it.",
            "return_error used too many times, should be used only once in the code, in main function.",
        ],
        [],
        id="warning,support=partner",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER}"),
        "3.8",
        "community",
        False,
        0,
        [],
        [],
        id="warning,support=community",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER}"),
        "3.8",
        "xsoar",
        False,
        4,
        [
            "return_error should be used in main function. Please add it.",
            "return_error used too many times, should be used only once in the code, in main function.",
        ],
        [],
        id="warning,support=xsoar",
    ),
    # --------------------------------------- For Warning file -------------------------------------------------------
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS}"),
        "3.8",
        "certified partner",
        False,
        4,
        [
            "Main function wasnt found in the file, Please add main()",
            "Do not use return_outputs function. Please return CommandResults object instead.",
            "Do not use demisto.results function.",
            "Initialize of params was found outside of main function. Please use demisto.params() only inside main",
            "Initialize of args was found outside of main function. Please use demisto.args() only inside main func",
            "Hardcoded http URL was found in the code, using https (when possible) is recommended.",
        ],
        [],
        id="warning,support=certified partner",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_NO_DEMISTO_RESULTS_WARNINGS}"),
        "3.8",
        "certified partner",
        False,
        4,
        [
            "Do not use return_outputs function. Please return CommandResults object instead."
        ],
        [],
        id="warning,support=xsoar, certified partner, indicator format",
    ),
    pytest.param(
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS}"),
        "3.8",
        "xsoar",
        False,
        4,
        [
            "Function arguments are missing type annotations. Please add type annotations",
            "It is best practice to use .get when accessing the arg/params dict object rather then direct access.",
            "Hardcoded http URL was found in the code, using https (when possible) is recommended.",
        ],
        [],
        id="warning,support=xsoar",
    ),
]


@pytest.mark.parametrize(
    "file, python_version,support_level,long_running,expected_exit_code,error_msgs,commands",
    files,
)
def test_xsoar_linter_errors(
    mocker,
    file,
    python_version,
    support_level,
    long_running,
    expected_exit_code,
    error_msgs,
    commands,
):
    """
    Given
    - file to run the linter on.
    - Python version of the file.
    - expected exit code of the xsoar linter function.
    - expected error messages of the xsoar linter.

    When
    - Running xsoar linter using demisto lint.

    Then
    - Ensure valid files pass with the correct exit code.
    - Ensure valid files pass with no error messages.
    - Ensure invalid files fail with the correct exit code.
    - Ensure invalid files fail with the correct error messages.
    """

    mocker.patch("demisto_sdk.commands.common.docker_helper.docker_login", return_value=False)
    mocker.patch.object(linter.Linter, "_update_support_level")
    test_path = Path(f"{GIT_ROOT}/demisto_sdk/tests/test_files")
    runner = linter.Linter(
        content_repo=test_path,
        pack_dir=test_path,
        docker_engine=True,
        docker_timeout=60,
    )
    runner._facts["support_level"] = support_level
    runner._facts["is_long_running"] = long_running
    runner._facts["commands"] = commands
    exit_code, output = runner._run_xsoar_linter(python_version, [file])
    assert exit_code == expected_exit_code
    for msg in error_msgs:
        assert msg in output

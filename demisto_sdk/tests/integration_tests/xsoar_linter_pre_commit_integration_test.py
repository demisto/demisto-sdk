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

from demisto_sdk.commands.xsoar_linter.xsoar_linter import (
    xsoar_linter_manager,
)
from demisto_sdk.tests.constants_test import (
    XSOAR_LINTER_PY3_INVALID,
    XSOAR_LINTER_PY3_INVALID_WARNINGS,
    XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER,
    XSOAR_LINTER_PY3_NO_DEMISTO_RESULTS_WARNINGS,
    XSOAR_LINTER_PY3_VALID,
)
from TestSuite.test_tools import ChangeCWD

files = [
    # ---------------------------------------- For Valid file -------------------------------------------------
    (Path(f"{XSOAR_LINTER_PY3_VALID}"), "3.8", "base", False, 0, [], []),
    (
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
    ),
    # -------------------------------------------- For Invalid file -------------------------------------------------
    # -------------------- For Invalid file with support level base and long running True -----------------------
    (
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
    ),
    # -------------------- For Invalid file with support level base and long running False -----------------------
    (
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
    ),
    # ------------- For Invalid file with support level certified partner and long running False ------------------
    (
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
    ),
    # ------------- For Invalid file with support level certified partner and long running True ---------------------
    (
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
    ),
    # ------------- For Invalid file with support level community and long running False ------------------
    # (
    #     Path(f"{XSOAR_LINTER_PY3_INVALID}"),
    #     "3.8",
    #     "community",
    #     False,
    #     1,
    #     [
    #         "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
    #         "test-module command is not implemented in the python file, it is essential for every"
    #         " integration. Please add it to your code. For more information see: "
    #         "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
    #     ],
    #     [],
    # ),
    # ------------- For Invalid file with default support level and long running False ------------------
    (
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
    ),
    # ------------- For Invalid file with xsoar support level and long running False ------------------
    (
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
    ),
    # -------------------------------- For Warning file which is relevant from partner level and bigger---------------
    # -------------------------------- For Warning file with support level partner------------------------------------
    (
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER}"),
        "3.8",
        "partner",
        False,
        0,
        [
            "try and except statements were not found in main function.",
            "return_error should be used in main function. Please add it.",
            "return_error used too many times, should be used only once in the code, in main function.",
        ],
        [],
    ),
    # -------------------------------- For Warning file with support level community-----------------------------------
    (
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER}"),
        "3.8",
        "community",
        False,
        0,
        [],
        [],
    ),
    # -------------------------------- For Warning file with support level xsoar-----------------------------------
    (
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER}"),
        "3.8",
        "xsoar",
        False,
        0,
        [
            "return_error should be used in main function. Please add it.",
            "return_error used too many times, should be used only once in the code, in main function.",
        ],
        [],
    ),
    # --------------------------------------- For Warning file -------------------------------------------------------
    # --------------------- For Warning file with support level certified partner -----------------------------------
    (
        Path(f"{XSOAR_LINTER_PY3_INVALID_WARNINGS}"),
        "3.8",
        "certified partner",
        False,
        0,
        [
            "Main function wasnt found in the file, Please add main()",
            "Do not use return_outputs function. Please return CommandResults object instead.",
            "Do not use demisto.results function.",
            "Initialize of params was found outside of main function. Please use demisto.params() only inside main",
            "Initialize of args was found outside of main function. Please use demisto.args() only inside main func",
            "Hardcoded http URL was found in the code, using https (when possible) is recommended.",
        ],
        [],
    ),
    # ------------- For Warning file with support level certified partner with indicator format file -------------------
    (
        Path(f"{XSOAR_LINTER_PY3_NO_DEMISTO_RESULTS_WARNINGS}"),
        "3.8",
        "certified partner",
        False,
        0,
        [
            "Do not use return_outputs function. Please return CommandResults object instead."
        ],
        [],
    ),
]


@pytest.mark.parametrize(
    "file, python_version,support_level,long_running,exit_code,error_msgs,commands",
    files,
)
def test_xsoar_linter_errors(
    mocker,
    git_repo,
    file,
    python_version,
    support_level,
    long_running,
    exit_code,
    error_msgs,
    commands,
    caplog,
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
    pack = git_repo.create_pack()
    pack.pack_metadata.update({"support": support_level})

    with open(file, "r") as f:
        test_content = f.read()
    integration_obj = pack.create_integration()
    integration_obj.set_commands(commands)

    with open(integration_obj.code.path, "w") as f:
        f.write(test_content)

    with ChangeCWD(pack.repo_path):
        res = xsoar_linter_manager([Path(integration_obj.path)])
        assert res == exit_code
        if exit_code:
            for error_msg in error_msgs:
                assert error_msg in caplog.text
        else:
            for warning in error_msgs:
                assert warning in caplog.text

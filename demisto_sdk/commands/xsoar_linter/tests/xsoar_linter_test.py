import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_integration_object
from demisto_sdk.commands.xsoar_linter.xsoar_linter import (
    ProcessResults,
    build_xsoar_linter_command,
    build_xsoar_linter_env_var,
    process_file,
)


@dataclass
class MockProcessError:
    returncode = 2
    stdout = (
        b"/Packs/TestName/Integrations/TestName/TestName.py:327:8: E9002 deserialize_protection_groups: Print is found, Please remove all prints from the code.\n"
        b"/Packs/TestName/Integrations/TestName/TestName.py:327:10: W9009 return-outputs-exists: Do not use return_outputs function. Please return CommandResults object instead."
    )
    stderr = b""


@dataclass
class MockProcessValid:
    returncode = 0
    stdout = b"/Packs/TestName/Integrations/TestName/TestName.py:327:10: W9009 return-outputs-exists: Do not use return_outputs function. Please return CommandResults object instead."
    stderr = b""


def test_build_xsoar_linter_command():
    """
    Given:
        None.

    When:
        Calling build_xsoar_linter_command function.

    Then:
        Assert that the command was built correctly.

    """
    expected = [
        f"{Path(sys.executable).parent}/pylint",
        "-E",
        "--disable=all",
        "--fail-under=-100",
        "--fail-on=E",
        "--msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'",
        "--enable=E9002,E9003,E9004,E9005,E9006,E9007,E9010,E9011,E9012,W9013,",
        "--load-plugins=base_checker,",
    ]

    output = build_xsoar_linter_command("base")
    assert len(output) == len(expected)
    assert all([a == b for a, b in zip(output, expected)])


@pytest.mark.parametrize(
    "integration_script, expected_env",
    [
        (
            create_integration_object(paths=["script.longRunning"], values=[True]),
            {
                "LONGRUNNING": "True",
                "PY2": "True",
                "is_script": "False",
                "commands": "test-command",
            },
        ),
        (
            create_integration_object(paths=["script.longRunning"], values=[False]),
            {
                "LONGRUNNING": "False",
                "PY2": "True",
                "is_script": "False",
                "commands": "test-command",
            },
        ),
        (
            create_integration_object(
                paths=["script.longRunning", "script.Commands"],
                values=[True, ["command1", "command2"]],
            ),
            {
                "LONGRUNNING": "True",
                "is_script": "False",
                "commands": ["command1", "command2"],
            },
        ),
    ],
)
def test_build_xsoar_linter_env_var(integration_script, expected_env):
    """
    Given:
        An integration object.

    When:
        Calling build_xsoar_linter_env_var function.

    Then:
        Assert that the environment variable dict was updated with the relevant values.

    """
    res = build_xsoar_linter_env_var(integration_script)
    assert all(item in res.items() for item in res.items())


@pytest.mark.parametrize(
    "mock_object, expected_res",
    [
        (
            MockProcessError(),
            ProcessResults(
                2,
                [
                    "/Packs/TestName/Integrations/TestName/TestName.py:327:8: E9002 deserialize_protection_groups: Print is found, Please remove all prints from the code."
                ],
                "/Packs/TestName/Integrations/TestName/TestName.py:327:8: E9002 deserialize_protection_groups: Print is found, Please remove all prints from the code.\n"
                "/Packs/TestName/Integrations/TestName/TestName.py:327:10: W9009 return-outputs-exists: Do not use return_outputs function. Please return CommandResults object instead.",
            ),
        ),
        (
            MockProcessValid(),
            ProcessResults(
                0,
                [],
                "/Packs/TestName/Integrations/TestName/TestName.py:327:10: W9009 return-outputs-exists: Do not use return_outputs function. Please return CommandResults object instead.",
            ),
        ),
    ],
)
def test_process_file(mocker, graph_repo, mock_object, expected_res):
    """
    Given:
        An integration path.

    When:
        Calling process_file function.

    Then:
        Assert that errors and warnings were successfully caught.

    """
    pack = graph_repo.create_pack("pack")
    integration = pack.create_integration("integration")
    mocker.patch.object(subprocess, "run", return_value=mock_object)
    res = process_file(Path(integration.path))
    assert res == expected_res

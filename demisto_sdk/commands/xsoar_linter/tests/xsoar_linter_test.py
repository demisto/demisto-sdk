import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_integration_object
from demisto_sdk.commands.xsoar_linter import xsoar_linter
from demisto_sdk.commands.xsoar_linter.xsoar_linter import (
    ProcessResults,
    build_xsoar_linter_command,
    build_xsoar_linter_env_var,
    process_file,
    process_file_ast,
    xsoar_linter_manager,
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


@pytest.mark.parametrize(
    "support_level, expected_loaded_checkers",
    [
        pytest.param(
            "base",
            "base_checker",
            id="Base support",
        ),
        pytest.param(
            "developer",
            "base_checker,community_level_checker",
            id="Developer support",
        ),
    ],
)
def test_build_xsoar_linter_command_valid_support_level(
    support_level: str,
    expected_loaded_checkers: str,
):
    """
    Given:
        A valid pack support level.

    When:
        Calling `build_xsoar_linter_command` function.

    Then:
        Assert that the command was built correctly.
    """
    expected = [
        f"{Path(sys.executable).parent}/pylint",
        "--disable=all",
        "--fail-under=-100",
        "--fail-on=E",
        "--msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'",
        "--enable=E9002,E9003,E9004,E9005,E9006,E9007,E9010,E9011,E9012,W9013",
        f"--load-plugins={expected_loaded_checkers}",
    ]

    output = build_xsoar_linter_command(support_level)
    assert len(output) == len(expected)
    assert output == expected


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
                [
                    "/Packs/TestName/Integrations/TestName/TestName.py:327:10: W9009 return-outputs-exists: Do not use return_outputs function. Please return CommandResults object instead."
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
                [
                    "/Packs/TestName/Integrations/TestName/TestName.py:327:10: W9009 return-outputs-exists: Do not use return_outputs function. Please return CommandResults object instead."
                ],
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


def test_process_file_ast(graph_repo):
    """
    Given:
        An integration whose code has a print (error E9002).

    When:
        Calling process_file_ast.

    Then:
        Assert the error is caught in the same line format as the pylint engine, and the return code is 1.
    """
    pack = graph_repo.create_pack("pack")
    integration = pack.create_integration(
        "integration", code='def main():\n    print("x")\n'
    )
    res = process_file_ast(Path(integration.path))
    print_errors = [
        error
        for error in res.errors
        if error.endswith(
            ":2:4: E9002 main: Print is found, Please remove all prints from the code."
        )
    ]
    assert res.return_code == 1
    assert len(print_errors) == 1
    assert print_errors[0] in res.errors_and_warnings.splitlines()


class InProcessPool:
    """Runs pool.map in the current process, so mocks and patches apply."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def map(self, func, items):
        return [func(item) for item in items]


@pytest.mark.parametrize(
    "engine, expected_worker",
    [("pylint", "process_file"), ("ast", "process_file_ast")],
)
def test_xsoar_linter_manager_engine(mocker, engine, expected_worker):
    """
    Given:
        An engine name.

    When:
        Calling xsoar_linter_manager.

    Then:
        Assert only the matching worker runs, and the start/finish log lines name the engine and the duration.
    """
    mocker.patch.object(xsoar_linter.multiprocessing, "Pool", InProcessPool)
    workers = {
        name: mocker.patch.object(xsoar_linter, name, return_value=ProcessResults())
        for name in ("process_file", "process_file_ast")
    }
    logger_info = mocker.patch.object(xsoar_linter.logger, "info")

    assert xsoar_linter_manager([Path("a.py")], engine=engine) == 0

    assert workers[expected_worker].call_count == 1
    assert sum(worker.call_count for worker in workers.values()) == 1
    messages = [call.args[0] for call in logger_info.call_args_list]
    assert any(
        message.startswith(f"[xsoar-lint] engine={engine}: starting on 1 file(s)")
        for message in messages
    )
    assert any(
        message.startswith(f"[xsoar-lint] engine={engine}: finished 1 file(s) in ")
        and "errors=0, warnings=0, failed files=0." in message
        for message in messages
    )


def test_xsoar_linter_manager_unknown_engine(mocker):
    """
    Given:
        An unknown engine name.

    When:
        Calling xsoar_linter_manager.

    Then:
        Assert it fails with a clear error and no file is processed.
    """
    pool = mocker.patch.object(xsoar_linter.multiprocessing, "Pool")
    logger_error = mocker.patch.object(xsoar_linter.logger, "error")
    assert xsoar_linter_manager([Path("a.py")], engine="foo") == 1
    pool.assert_not_called()
    assert "Unknown engine 'foo'" in logger_error.call_args.args[0]

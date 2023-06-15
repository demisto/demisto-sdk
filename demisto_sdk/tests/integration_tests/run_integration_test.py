import logging

import pytest
from click.testing import CliRunner
from demisto_client.demisto_api import DefaultApi

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.run_cmd.runner import Runner
from TestSuite.test_tools import str_in_call_args_list

DEBUG_FILE_PATH = (
    f"{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.txt"
)
YAML_OUTPUT = """arguments: []
name: kl-get-records
outputs:
- contextPath: Keylight.ID
  description: ''
  type: Number
- contextPath: Keylight.Name
  description: ''
  type: String
- contextPath: Keylight.ShortName
  description: ''
  type: String
- contextPath: Keylight.SystemName
  description: ''
  type: String"""


@pytest.fixture
def set_environment_variables(monkeypatch):
    # Set environment variables required by runner
    monkeypatch.setenv("DEMISTO_BASE_URL", "http://demisto.instance.com:8080/")
    monkeypatch.setenv("DEMISTO_API_KEY", "API_KEY")
    monkeypatch.delenv("DEMISTO_USERNAME", raising=False)
    monkeypatch.delenv("DEMISTO_PASSWORD", raising=False)


def test_integration_run_non_existing_command(
    mocker, monkeypatch, set_environment_variables
):
    """
    Given
    - Non-existing command to run.
    - Debug and Verbose option to increase coverage

    When
    - Running `run` command.

    Then
    - Ensure output is the appropriate error.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")
    mocker.patch.object(DefaultApi, "investigation_add_entries_sync", return_value=None)
    mocker.patch.object(Runner, "_get_playground_id", return_value="pg_id")
    result = CliRunner(mix_stderr=False,).invoke(
        main,
        [
            "run",
            "-q",
            "!non-existing-command",
            "-D",
        ],
    )
    assert 0 == result.exit_code
    assert not result.exception
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "Command did not run, make sure it was written correctly.",
    )


def test_json_to_outputs_flag(mocker, monkeypatch, set_environment_variables):
    """
    Given
    - kl-get-components command

    When
    - Running `run` command on it with json-to-outputs flag.

    Then
    - Ensure the json_to_outputs command is running correctly
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    monkeypatch.setenv("COLUMNS", "1000")

    # mocks to allow the command to run locally
    mocker.patch.object(Runner, "_get_playground_id", return_value="pg_id")
    mocker.patch.object(Runner, "_run_query", return_value=["123"])
    # mock to get test log file
    mocker.patch.object(DefaultApi, "download_file", return_value=DEBUG_FILE_PATH)
    # mock to set prefix instead of getting it from input

    command = "!kl-get-records"
    run_result = CliRunner(
        mix_stderr=False,
    ).invoke(main, ["run", "-q", command, "--json-to-outputs", "-p", "Keylight", "-r"])

    assert run_result.exit_code == 0
    assert not run_result.stderr
    assert not run_result.exception

    assert str_in_call_args_list(logger_info.call_args_list, YAML_OUTPUT)
    assert logger_warning.call_count == 0
    assert logger_error.call_count == 0


def test_json_to_outputs_flag_fail_no_prefix(
    mocker, monkeypatch, set_environment_variables
):
    """
    Given
    - kl-get-components command

    When
    - Running `run` command on it with json-to-outputs flag and no prefix argument

    Then
    - Ensure the json_to_outputs command is failing due to no prefix argument provided.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")
    # mocks to allow the command to run locally
    mocker.patch.object(Runner, "_get_playground_id", return_value="pg_id")
    mocker.patch.object(Runner, "_run_query", return_value=["123"])
    # mock to get test log file
    mocker.patch.object(DefaultApi, "download_file", return_value=DEBUG_FILE_PATH)
    # mock to set prefix instead of getting it from input

    command = "!kl-get-records"
    run_result = CliRunner(
        mix_stderr=False,
    ).invoke(main, ["run", "-q", command, "--json-to-outputs"])
    assert 1 == run_result.exit_code
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "A prefix for the outputs is needed for this command. Please provide one",
    )


def test_incident_id_passed_to_run(mocker, monkeypatch, set_environment_variables):
    """
    Given
    - kl-get-components command and --incident-id argument.

    When
    - Running `run` command on it.

    Then
    - Ensure the investigation-id is set from the incident-id.
    """
    logger_debug = mocker.patch.object(logging.getLogger("demisto-sdk"), "debug")
    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    monkeypatch.setenv("COLUMNS", "1000")

    # mocks to allow the command to run locally
    mocker.patch.object(Runner, "_run_query", return_value=["123"])
    # mock to get test log file
    mocker.patch.object(DefaultApi, "download_file", return_value=DEBUG_FILE_PATH)
    # mock to set prefix instead of getting it from input

    command = "!kl-get-records"
    run_result = CliRunner(
        mix_stderr=False,
    ).invoke(main, ["run", "-q", command, "--incident-id", "pg_id"])

    assert run_result.exit_code == 0
    assert str_in_call_args_list(
        logger_debug.call_args_list, "running command in investigation_id='pg_id'"
    )
    assert logger_warning.call_count == 0
    assert logger_error.call_count == 0

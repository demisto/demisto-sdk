import pytest
from click.testing import CliRunner
from demisto_client.demisto_api import DefaultApi
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.run_cmd.runner import Runner

DEBUG_FILE_PATH = f'{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.txt'
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
    monkeypatch.setenv('DEMISTO_BASE_URL', 'http://demisto.instance.com:8080/')
    monkeypatch.setenv('DEMISTO_API_KEY', 'API_KEY')
    monkeypatch.delenv('DEMISTO_USERNAME', raising=False)
    monkeypatch.delenv('DEMISTO_PASSWORD', raising=False)


def test_integration_run_non_existing_command(mocker, set_environment_variables):
    """
    Given
    - Non-existing command to run.
    - Debug and Verbose option to increase coverage

    When
    - Running `run` command.

    Then
    - Ensure output is the appropriate error.
    """
    mocker.patch.object(DefaultApi, 'investigation_add_entries_sync', return_value=None)
    mocker.patch.object(Runner, '_get_playground_id', return_value='pg_id')
    result = CliRunner(mix_stderr=False, ).invoke(main, ['run', '-q', '!non-existing-command', '-D', '-v'])
    assert 0 == result.exit_code
    assert not result.exception
    assert 'Command did not run, make sure it was written correctly.' in result.output
    assert not result.stderr


def test_json_to_outputs_flag(mocker, set_environment_variables):
    """
        Given
        - kl-get-components command

        When
        - Running `run` command on it with json-to-outputs flag.

        Then
        - Ensure the json_to_outputs command is running correctly
    """
    # mocks to allow the command to run locally
    mocker.patch.object(Runner, '_get_playground_id', return_value='pg_id')
    mocker.patch.object(Runner, '_run_query', return_value=['123'])
    # mock to get test log file
    mocker.patch.object(DefaultApi, 'download_file', return_value=DEBUG_FILE_PATH)
    # mock to set prefix instead of getting it from input

    command = '!kl-get-records'
    run_result = CliRunner(mix_stderr=False, ).invoke(main, ['run', '-q', command, '--json-to-outputs', '-p', 'Keylight', '-r'])
    assert 0 == run_result.exit_code
    assert not run_result.exception
    assert YAML_OUTPUT in run_result.stdout
    assert not run_result.stderr


def test_json_to_outputs_flag_fail_no_prefix(mocker, set_environment_variables):
    """
        Given
        - kl-get-components command

        When
        - Running `run` command on it with json-to-outputs flag and no prefix argument

        Then
        - Ensure the json_to_outputs command is failing due to no prefix argument provided.
    """
    # mocks to allow the command to run locally
    mocker.patch.object(Runner, '_get_playground_id', return_value='pg_id')
    mocker.patch.object(Runner, '_run_query', return_value=['123'])
    # mock to get test log file
    mocker.patch.object(DefaultApi, 'download_file', return_value=DEBUG_FILE_PATH)
    # mock to set prefix instead of getting it from input

    command = '!kl-get-records'
    run_result = CliRunner(mix_stderr=False, ).invoke(main, ['run', '-q', command, '--json-to-outputs'])
    assert 1 == run_result.exit_code
    assert 'A prefix for the outputs is needed for this command. Please provide one' in run_result.stdout
    assert not run_result.stderr

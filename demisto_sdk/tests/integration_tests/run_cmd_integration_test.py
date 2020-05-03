import pytest
from click.testing import CliRunner
from demisto_client.demisto_api import DefaultApi
from demisto_sdk.__main__ import main
from demisto_sdk.commands.run_cmd.runner import Runner


@pytest.fixture
def set_environment_variables(monkeypatch):
    # Set environment variables required by runner
    monkeypatch.setenv('DEMISTO_BASE_URL', 'http://demisto.instance.com:8080/')
    monkeypatch.setenv('DEMISTO_API_KEY', 'API_KEY')


def test_runner_with_wrong_query(mocker, set_environment_variables):
    """
    Given
    - Non-existing query.

    When
    - Running `run` command.

    Then
    - Ensure output is the appropriate error.
    """
    mocker.patch.object(DefaultApi, 'investigation_add_entries_sync', return_value=None)
    mocker.patch.object(Runner, '_get_playground_id', return_value='pg_id')
    result = CliRunner(mix_stderr=False).invoke(main, ['run', '-q', '!non-existing-command'])
    assert 'Command did not run, make sure it was written correctly.' in result.output

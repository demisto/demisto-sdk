import filecmp
import tempfile
import pytest

from demisto_client.demisto_api import DefaultApi

from demisto_sdk.commands.run_cmd.runner import Runner

EXPECTED_OUTPUT = [{'ID': 10082, 'Name': 'Projects', 'ShortName': 'Projects', 'SystemName': 'Projects'},
                   {'ID': 10077, 'Name': 'Universe', 'ShortName': 'Universe', 'SystemName': 'Universe'}]


@pytest.fixture
def set_environment_variables(monkeypatch):
    # Set environment variables required by runner
    monkeypatch.setenv('DEMISTO_BASE_URL', 'http://demisto.instance.com:8080/')
    monkeypatch.setenv('DEMISTO_API_KEY', 'API_KEY')


def test_return_raw_outputs_from_log(mocker, set_environment_variables):
    """
    Validates that the raw outputs of a log file is extracted correctly.

    """
    mocker.patch.object(DefaultApi, 'download_file',
                        return_value='demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.log')
    runner = Runner('Query', json_to_outputs=True)
    temp = runner._return_raw_outputs_from_log(['123'])
    assert temp == EXPECTED_OUTPUT


def test_return_raw_outputs_from_log_also_write_log(mocker, set_environment_variables):
    """
    Validates that the raw outputs of a log file is extracted correctly and that the log file is saved correctly in
    the expected output path.

    """
    mocker.patch.object(DefaultApi, 'download_file',
                        return_value='demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.log')
    temp_file = tempfile.NamedTemporaryFile()
    runner = Runner('Query', debug_path=temp_file.name, json_to_outputs=True)
    temp = runner._return_raw_outputs_from_log(['123'])
    assert temp == EXPECTED_OUTPUT
    assert filecmp.cmp('demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.log', temp_file.name)
    temp_file.close()

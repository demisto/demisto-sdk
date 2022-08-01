import filecmp
import tempfile

import pytest
from demisto_client.demisto_api import DefaultApi

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.run_cmd.runner import Runner

INPUT_OUTPUTS = [
    # Debug output with Context Output part
    (f'{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.txt',
     {'Keylight.Component': [{'ID': 10082, 'Name': 'Projects', 'ShortName': 'Projects', 'SystemName': 'Projects'},
                             {'ID': 10077, 'Name': 'Universe', 'ShortName': 'Universe', 'SystemName': 'Universe'}]}),
    # Debug output without Context Output part
    (f'{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component_no_context.txt',
     [{'ID': 10082, 'Name': 'Projects', 'ShortName': 'Projects', 'SystemName': 'Projects'},
      {'ID': 10077, 'Name': 'Universe', 'ShortName': 'Universe', 'SystemName': 'Universe'}])
]


@pytest.fixture
def set_environment_variables(monkeypatch):
    # Set environment variables required by runner
    monkeypatch.setenv('DEMISTO_BASE_URL', 'http://demisto.instance.com:8080/')
    monkeypatch.setenv('DEMISTO_API_KEY', 'API_KEY')
    monkeypatch.delenv('DEMISTO_USERNAME', raising=False)
    monkeypatch.delenv('DEMISTO_PASSWORD', raising=False)


@pytest.mark.parametrize('file_path, expected_output', INPUT_OUTPUTS)
def test_return_raw_outputs_from_log(mocker, set_environment_variables, file_path, expected_output):
    """
    Validates that the context of a log file is extracted correctly.

    """
    mocker.patch.object(DefaultApi, 'download_file',
                        return_value=file_path)
    runner = Runner('Query', json_to_outputs=True)
    temp = runner._return_context_dict_from_log(['123'])
    assert temp == expected_output


@pytest.mark.parametrize('file_path, expected_output', INPUT_OUTPUTS)
def test_return_raw_outputs_from_log_also_write_log(mocker, set_environment_variables, file_path, expected_output):
    """
    Validates that the context of a log file is extracted correctly and that the log file is saved correctly in
    the expected output path.

    """
    mocker.patch.object(DefaultApi, 'download_file',
                        return_value=file_path)
    temp_file = tempfile.NamedTemporaryFile()
    runner = Runner('Query', debug_path=temp_file.name, json_to_outputs=True)
    temp = runner._return_context_dict_from_log(['123'])
    assert temp == expected_output
    assert filecmp.cmp(file_path, temp_file.name)
    temp_file.close()


def test_return_raw_outputs_from_log_with_raw_response_flag(mocker, set_environment_variables, ):
    """
    Validates that the raw outputs of a log file is extracted correctly while using the raw_output parameter,
     even if the file has a context part

    """
    file_path = f'{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.txt'
    expected_output = [{'ID': 10082, 'Name': 'Projects', 'ShortName': 'Projects', 'SystemName': 'Projects'},
                       {'ID': 10077, 'Name': 'Universe', 'ShortName': 'Universe', 'SystemName': 'Universe'}]
    mocker.patch.object(DefaultApi, 'download_file',
                        return_value=file_path)
    runner = Runner('Query', json_to_outputs=True, raw_response=True)
    temp = runner._return_context_dict_from_log(['123'])
    assert temp == expected_output

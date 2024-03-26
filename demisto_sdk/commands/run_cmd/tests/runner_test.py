import filecmp
import tempfile

import pytest
from demisto_client.demisto_api import DefaultApi

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.run_cmd.runner import Runner

INPUT_OUTPUTS = [
    # Debug output with Context Output part
    (
        f"{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.txt",
        {
            "Keylight.Component": [
                {
                    "ID": 10082,
                    "Name": "Projects",
                    "ShortName": "Projects",
                    "SystemName": "Projects",
                },
                {
                    "ID": 10077,
                    "Name": "Universe",
                    "ShortName": "Universe",
                    "SystemName": "Universe",
                },
            ]
        },
    ),
    # Debug output without Context Output part
    (
        f"{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component_no_context.txt",
        [
            {
                "ID": 10082,
                "Name": "Projects",
                "ShortName": "Projects",
                "SystemName": "Projects",
            },
            {
                "ID": 10077,
                "Name": "Universe",
                "ShortName": "Universe",
                "SystemName": "Universe",
            },
        ],
    ),
]


@pytest.fixture
def set_environment_variables(monkeypatch):
    # Set environment variables required by runner
    monkeypatch.setenv("DEMISTO_BASE_URL", "http://demisto.instance.com:8080/")
    monkeypatch.setenv("DEMISTO_API_KEY", "API_KEY")
    monkeypatch.delenv("DEMISTO_USERNAME", raising=False)
    monkeypatch.delenv("DEMISTO_PASSWORD", raising=False)


@pytest.mark.parametrize("file_path, expected_output", INPUT_OUTPUTS)
def test_return_raw_outputs_from_log(
    mocker, set_environment_variables, file_path, expected_output
):
    """
    Validates that the context of a log file is extracted correctly.

    """
    mocker.patch.object(DefaultApi, "download_file", return_value=file_path)
    runner = Runner("Query", json_to_outputs=True)
    temp = runner._return_context_dict_from_log(["123"])
    assert temp == expected_output


@pytest.mark.parametrize("file_path, expected_output", INPUT_OUTPUTS)
def test_return_raw_outputs_from_log_also_write_log(
    mocker, set_environment_variables, file_path, expected_output
):
    """
    Validates that the context of a log file is extracted correctly and that the log file is saved correctly in
    the expected output path.

    """
    mocker.patch.object(DefaultApi, "download_file", return_value=file_path)
    temp_file = tempfile.NamedTemporaryFile()
    runner = Runner("Query", debug_path=temp_file.name, json_to_outputs=True)
    temp = runner._return_context_dict_from_log(["123"])
    assert temp == expected_output
    assert filecmp.cmp(file_path, temp_file.name)
    temp_file.close()


def test_return_raw_outputs_from_log_with_raw_response_flag(
    mocker,
    set_environment_variables,
):
    """
    Validates that the raw outputs of a log file is extracted correctly while using the raw_output parameter,
     even if the file has a context part

    """
    file_path = f"{git_path()}/demisto_sdk/commands/run_cmd/tests/test_data/kl-get-component.txt"
    expected_output = [
        {
            "ID": 10082,
            "Name": "Projects",
            "ShortName": "Projects",
            "SystemName": "Projects",
        },
        {
            "ID": 10077,
            "Name": "Universe",
            "ShortName": "Universe",
            "SystemName": "Universe",
        },
    ]
    mocker.patch.object(DefaultApi, "download_file", return_value=file_path)
    runner = Runner("Query", json_to_outputs=True, raw_response=True)
    temp = runner._return_context_dict_from_log(["123"])
    assert temp == expected_output


class GetPlaygroundResMock:
    def __init__(self, total, data):
        self.total = total
        self.data = data


class PlaygroundObjMock:
    def __init__(self, _id):
        self.id = _id
        self.creating_user_id = str(_id)


def test_playground_not_exist(mocker, set_environment_variables):
    """
    Validates that the context of a log file is extracted correctly.

    """
    mocker.patch.object(
        DefaultApi, "search_investigations", return_value=GetPlaygroundResMock(0, [])
    )
    runner = Runner("Query", json_to_outputs=True)
    with pytest.raises(RuntimeError):
        runner._get_playground_id()


def test_single_playground_exist(mocker, set_environment_variables):
    """
    Validates that the context of a log file is extracted correctly.

    """

    mocker.patch.object(
        DefaultApi,
        "search_investigations",
        return_value=GetPlaygroundResMock(1, [PlaygroundObjMock(1)]),
    )
    generic_request_mock = mocker.patch.object(DefaultApi, "generic_request")
    runner = Runner("Query", json_to_outputs=True)
    assert runner._get_playground_id() == 1
    assert generic_request_mock.call_count == 0


data_test_multiple_existing_playgrounds = ["15", "10", "5", "3"]


@pytest.mark.parametrize("username", data_test_multiple_existing_playgrounds)
def test_multiple_existing_playgrounds(mocker, set_environment_variables, username):
    """
    Validates that the context of a log file is extracted correctly.

    """
    responses = [PlaygroundObjMock(i) for i in range(1, 16)]

    def helper(*_args, **_kwargs):
        return GetPlaygroundResMock(15, [responses.pop(0) for _ in range(5)])

    mocker.patch.object(DefaultApi, "search_investigations", new=helper)
    generic_request_mock = mocker.patch.object(
        DefaultApi, "generic_request", return_value=({"username": username}, 200, None)
    )
    runner = Runner("Query", json_to_outputs=True)
    assert runner._get_playground_id() == int(username)
    assert generic_request_mock.call_count == 1
    assert len(responses) == 0

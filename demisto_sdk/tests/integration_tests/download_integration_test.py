from os.path import join
from pathlib import Path

import pytest
from typer.testing import CliRunner
from urllib3.response import HTTPResponse

from demisto_sdk.__main__ import app
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.download.tests.downloader_test import Environment

DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
TEST_FILE_DIR = Path(__file__).parent.parent / "test_files" / "download_command"


def match_request_text(client, url, method, *args, **kwargs):
    if url == "/content/bundle":
        bundle_path = TEST_FILE_DIR / "content_bundle.tar.gz"
        api_response = bundle_path.read_bytes()
        result = HTTPResponse(body=api_response, status=200)

        return result, 200, None

    elif url.startswith("/playbook") and url.endswith("/yaml"):
        filename = url.replace("/playbook/", "").replace("/yaml", "")

        file_path = TEST_FILE_DIR / f"playbook-{filename}.yml"
        api_response = file_path.read_text()

        return api_response, 200, None


@pytest.fixture
def demisto_client(mocker):
    mocker.patch(
        "demisto_sdk.commands.download.downloader.demisto_client",
        return_value="object",
    )

    mocker.patch(
        "demisto_sdk.commands.download.downloader.demisto_client.generic_request_func",
        side_effect=match_request_text,
    )


def test_integration_download_no_force(demisto_client, tmp_path):
    """
    Given
    - playbook & script exist in the output pack path.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure no download has been made.
    - Ensure skipped msg is printed.
    """

    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["download", "-o", pack_path, "-i", "TestScript", "-i", "DummyPlaybook"],
    )
    assert "Filtering process completed, 2/13 items remain." in result.output
    assert "Skipped downloads: 2" in result.output
    assert result.exit_code == 0


def test_integration_download_with_force(demisto_client, tmp_path, mocker):
    """
    Given
    - playbook & script exist in the output pack path.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure download has been made successfully.
    """

    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [
            "download",
            "-o",
            pack_path,
            "-i",
            "TestScript",
            "-i",
            "DummyPlaybook",
            "-f",
        ],
    )
    assert "Filtering process completed, 2/13 items remain." in result.output
    assert "Successful downloads: 2" in result.output
    assert result.exit_code == 0


def test_integration_download_list_files(demisto_client, mocker, capsys):
    """
    Given
    - lf flag to list all available content items.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure list files has been made successfully.
    """

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["download", "-lf"])

    expected_table_str = """Content Name                          Content Type
------------------------------------  ---------------
CommonServerUserPowerShell            script
CommonServerUserPython                script
FormattingPerformance                 script
TestScript                            script
Microsoft Graph Device Management     integration
Symantec Data Loss Prevention (Beta)  betaintegration
Test Integration                      integration
DummyPlaybook                         playbook
FormattingPerformance - Test          playbook
Handle Hello World Alert Test         playbook
MSGraph_DeviceManagement_Test         playbook
Protectwise-Test                      playbook
guy                                   playbook"""

    assert expected_table_str in result.output
    assert result.exit_code == 0


def test_integration_download_fail(demisto_client, tmp_path):
    """
    Given
    - Script to download, that exists on the machine.
    - Playbook to download, that doesn't exist on the machine.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure that the exit code is 1, since the playbook was not downloaded.
    """
    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [
            "download",
            "-o",
            pack_path,
            "-i",
            "TestScript",
            "-i",
            "DummyPlaybook1",
            "-f",
        ],
    )
    for string in (
        "Filtering process completed, 1/13 items remain.",
        "Custom content item 'DummyPlaybook1' provided as an input could not be found / parsed.",
        "Successful downloads: 1",
    ):
        assert string in result.output
    assert result.exit_code == 1
